from core.base_event import BaseEvent
import pygame
import random
import math

class EspectroLuminicoEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="17. EL ESPECTRO LUMÍNICO (APAGONES)")
        self.mensaje = "CALIBRANDO TELEMETRÍA DE LA RED ELÉCTRICA MUNDIAL..."
        self.width = 800
        self.height = 430

        # Red eléctrica global (Píxel X, Píxel Y, Radio de Dispersión en px, Cantidad de luces)
        # Coordenadas recalibradas milimétricamente según la captura image_c2b9fd.jpg
        self.nodos_urbanos = [
            # NORTEAMÉRICA
            (205, 115, 9, 350),   # NY / Boston
            (195, 125, 7, 200),   # Washington DC
            (120, 125, 8, 250),   # Los Ángeles
            (115, 115, 6, 150),   # San Francisco
            (180, 115, 9, 200),   # Chicago
            (160, 140, 8, 150),   # Texas / Houston
            (195, 150, 6, 120),   # Miami / Florida
            (150, 160, 8, 180),   # Centro de México
            
            # SUDAMÉRICA
            (270, 255, 8, 250),   # Sao Paulo
            (275, 250, 6, 150),   # Río de Janeiro
            (250, 290, 8, 150),   # Buenos Aires
            (240, 290, 6, 100),   # Santiago (Chile)
            (220, 230, 6, 80),    # Lima
            (215, 205, 6, 100),   # Bogotá
            
            # EUROPA
            (365, 90,  6, 250),   # Londres / UK Sur
            (360, 80,  5, 150),   # UK Norte
            (375, 100, 8, 300),   # París / Francia
            (395, 95,  9, 350),   # Alemania Central
            (405, 115, 7, 200),   # Italia
            (365, 120, 6, 180),   # Madrid / España Centro
            (375, 115, 5, 120),   # Barcelona / Costa Blanca
            (450, 80,  10, 200),  # Moscú
            
            # ÁFRICA
            (425, 145, 6, 150),   # El Cairo / Delta del Nilo
            (390, 205, 7, 150),   # Lagos / Golfo de Guinea
            (425, 285, 7, 120),   # Sudáfrica (Johannesburgo)
            
            # ASIA
            (675, 120, 7, 350),   # Tokio
            (665, 125, 5, 200),   # Osaka
            (635, 140, 9, 400),   # Shanghái
            (610, 165, 7, 250),   # Hong Kong / Shenzhen
            (615, 115, 9, 300),   # Beijing
            (525, 165, 9, 350),   # Nueva Delhi
            (515, 185, 7, 200),   # Mumbai
            (590, 185, 7, 180),   # Bangkok
            (595, 215, 5, 120),   # Singapur
            (485, 160, 5, 100),   # Dubái / Golfo Pérsico
            
            # OCEANÍA
            (695, 295, 7, 150),   # Sídney
            (680, 310, 5, 100),   # Melbourne
            (740, 315, 5, 80),    # Nueva Zelanda
        ]

        self.red_puntos = []
        self.generar_red()
        self.apagones_activos = []
        self.ultimo_apagon = 0

    def generar_red(self):
        for cx, cy, dispersion, cantidad in self.nodos_urbanos:
            for _ in range(cantidad):
                px = random.gauss(cx, dispersion)
                py = random.gauss(cy, dispersion)
                if 0 <= px <= self.width and 0 <= py <= self.height:
                    self.red_puntos.append([px, py, random.random() * math.pi * 2])

    def update(self, tiempo_actual):
        if tiempo_actual - self.ultimo_apagon > random.randint(5000, 12000):
            self.ultimo_apagon = tiempo_actual

            nodo = random.choice(self.nodos_urbanos)
            cx, cy, disp, _ = nodo
            
            px_falla = cx + random.gauss(0, disp / 2)
            py_falla = cy + random.gauss(0, disp / 2)

            radio = random.randint(20, 50)
            duracion = random.randint(10000, 30000)

            self.apagones_activos.append({
                "x": px_falla,
                "y": py_falla,
                "radio": radio,
                "fin": tiempo_actual + duracion,
                "nombre_zona": f"X:{int(px_falla)} Y:{int(py_falla)}"
            })

            self.mensaje = f"ANOMALÍA EN RED ELÉCTRICA: CASCADA DE FALLOS DETECTADA EN SECTOR {int(px_falla)}/{int(py_falla)}"

        apagones_restantes = []
        for ap in self.apagones_activos:
            if ap["fin"] > tiempo_actual:
                apagones_restantes.append(ap)
        self.apagones_activos = apagones_restantes

        if not self.apagones_activos:
            self.mensaje = "INFRAESTRUCTURA ELÉCTRICA ESTABLE. RED GLOBAL NOMINAL."

    def draw(self, surface, color_linea, color_fondo):
        tiempo_sec = pygame.time.get_ticks() / 1000.0

        for punto in self.red_puntos:
            px, py, offset = punto
            en_apagon = False
            
            for apagon in self.apagones_activos:
                dist_cuadrada = (px - apagon["x"])**2 + (py - apagon["y"])**2
                if dist_cuadrada < apagon["radio"]**2:
                    en_apagon = True
                    break

            if not en_apagon:
                frecuencia = math.sin(tiempo_sec * 6.0 + offset)
                if frecuencia > -0.3:
                    pygame.draw.rect(surface, color_linea, (int(px), int(py), 1, 1))
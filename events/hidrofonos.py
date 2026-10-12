from core.base_event import BaseEvent
import pygame
import random

class CantoAcusticoEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="19. EL CANTO ACÚSTICO (HIDRÓFONOS)")
        self.mensaje = "CALIBRANDO RED DE HIDRÓFONOS DE PROFUNDIDAD..."
        
        # Coordenadas ancladas en las fallas oceánicas y zonas de migración
        self.nodos_oceanicos = [
            {"nombre": "CUENCA DEL PACÍFICO NORTE", "x": 90, "y": 180},
            {"nombre": "FOSA DE LAS MARIANAS", "x": 720, "y": 220},
            {"nombre": "DORSAL MESOATLÁNTICA", "x": 330, "y": 250},
            {"nombre": "OCÉANO ÍNDICO SUR", "x": 540, "y": 300},
            {"nombre": "OCÉANO ANTÁRTICO", "x": 400, "y": 380}
        ]
        
        self.ondas_activas = []
        self.ultimo_evento = 0
        
    def update(self, tiempo_actual):
        # Generar una nueva intercepción acústica cada 5 a 12 segundos
        if tiempo_actual - self.ultimo_evento > random.randint(5000, 12000):
            self.ultimo_evento = tiempo_actual
            
            nodo = random.choice(self.nodos_oceanicos)
            # 70% de probabilidad de ser canto de cetáceo, 30% de sismo submarino
            es_biologico = random.random() > 0.3 
            
            if es_biologico:
                frecuencia = random.randint(15, 40)
                msg = f"INTERCEPCIÓN ACÚSTICA: CANTO DE BALLENA AZUL ({frecuencia}Hz) — {nodo['nombre']}"
                velocidad = 0.4
                anillos = 4
            else:
                frecuencia = round(random.uniform(2.0, 10.0), 1)
                msg = f"ANOMALÍA GRAVIMÉTRICA: ACTIVIDAD TECTÓNICA SUBMARINA ({frecuencia}Hz) — {nodo['nombre']}"
                velocidad = 1.5
                anillos = 1
            
            self.ondas_activas.append({
                "x": nodo["x"],
                "y": nodo["y"],
                "radio": 1.0,
                # Las ondas viajan hasta 300 píxeles, cubriendo continentes enteros
                "max_radio": random.randint(200, 350),
                "velocidad": velocidad,
                "anillos": anillos
            })
            
            self.mensaje = msg

        # Calcular la propagación matemática del sonido
        ondas_vivas = []
        for onda in self.ondas_activas:
            onda["radio"] += onda["velocidad"]
            if onda["radio"] < onda["max_radio"]:
                ondas_vivas.append(onda)
        self.ondas_activas = ondas_vivas

    def draw(self, surface, color_linea, color_fondo):
        for onda in self.ondas_activas:
            r_base = onda["radio"]
            x, y = onda["x"], onda["y"]
            
            # Dibujar anillos concéntricos
            for i in range(onda["anillos"]):
                # Separación matemática entre cada eco del canto
                r_actual = r_base - (i * 25)
                
                if r_actual > 0:
                    # Dibujamos líneas vectoriales estables de 1 píxel de grosor
                    pygame.draw.circle(surface, color_linea, (int(x), int(y)), int(r_actual), width=1)
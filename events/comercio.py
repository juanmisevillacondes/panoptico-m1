from core.base_event import BaseEvent
import pygame
import random
import math

class FlujoLogisticoEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="22. LA SANGRE DEL COMERCIO (AIS MARÍTIMO)")
        self.mensaje = "INTERCEPTANDO RED AIS: CALCULANDO VECTORES DE TRÁFICO MERCANTE..."
        
        # Rutas esculpidas con evasión de masa terrestre corregida
        self.rutas = {
            # Asia -> Suez -> Gibraltar -> Mancha
            "ASIA-EUROPA (VÍA SUEZ)": [(670, 170), (630, 210), (605, 245), (530, 240), (490, 210), (460, 195), (435, 155), (410, 145), (380, 135), (365, 125), (375, 110)],
            
            # Asia -> Cabo -> Atlántico Sur -> *Curva abierta para esquivar África* -> Europa
            "ASIA-EUROPA (VÍA CABO)": [(670, 170), (630, 210), (605, 245), (530, 240), (490, 260), (470, 300), (425, 335), (390, 300), (340, 250), (330, 200), (340, 160), (365, 125), (375, 110)],
            
            # Europa -> Atlántico -> Paso del Caribe -> *Panamá (Reubicado al Sur)*
            "EUROPA-PANAMÁ (TRANSATLÁNTICO)": [(375, 110), (365, 125), (320, 150), (270, 185), (240, 215), (215, 235)],
            
            # Nueva York -> Mar Caribe abierto -> *Panamá (Reubicado al Sur)*
            "EEUU (ESTE)-PANAMÁ": [(230, 130), (220, 160), (225, 180), (235, 205), (215, 235)],
            
            # Asia -> Salida Pacífico
            "ASIA-PACÍFICO": [(670, 170), (700, 160), (790, 180)],
            
            # Pacífico -> *Panamá (Reubicado al Sur)*
            "PACÍFICO-PANAMÁ": [(10, 190), (80, 200), (150, 225), (215, 235)]
        }
        
        # Chokepoints recalibrados con la nueva latitud de Panamá
        self.chokepoints = [
            {"nombre": "CANAL DE SUEZ", "x": 435, "y": 155, "bloqueado": False},
            {"nombre": "ESTRECHO DE MALACA", "x": 605, "y": 245, "bloqueado": False},
            {"nombre": "CANAL DE PANAMÁ", "x": 215, "y": 235, "bloqueado": False},
            {"nombre": "ESTRECHO DE GIBRALTAR", "x": 380, "y": 135, "bloqueado": False}
        ]
        
        self.buques = []
        self.ultimo_cambio_estado = 0
        
        for _ in range(1500):
            self._crear_buque()

    def _crear_buque(self):
        nombre_ruta = random.choice(list(self.rutas.keys()))
        self.buques.append({
            "ruta": nombre_ruta,
            "progreso": random.uniform(0.0, 1.0), # Se distribuyen por toda la ruta
            # Velocidad letárgica: tardan minutos reales en cruzar el mapa
            "velocidad_base": random.uniform(0.0001, 0.0005) 
        })

    def _interpolar_ruta(self, ruta_nodos, progreso):
        # Calcula la posición exacta (x,y) a lo largo de una lista de puntos
        total_segmentos = len(ruta_nodos) - 1
        indice_flotante = progreso * total_segmentos
        idx = int(indice_flotante)
        
        if idx >= total_segmentos:
            return ruta_nodos[-1]
            
        t = indice_flotante - idx
        p1 = ruta_nodos[idx]
        p2 = ruta_nodos[idx + 1]
        
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        return (x, y)

    def update(self, tiempo_actual):
        # Dinámica de los atascos (Cada 20-40 segundos hay posibilidad de bloqueo)
        if tiempo_actual - self.ultimo_cambio_estado > random.randint(20000, 40000):
            self.ultimo_cambio_estado = tiempo_actual
            
            # Resetear bloqueos
            for cp in self.chokepoints:
                cp["bloqueado"] = False
                
            # 30% de probabilidad de que el capitalismo global se atasque
            if random.random() < 0.30:
                cp_afectado = random.choice(self.chokepoints)
                cp_afectado["bloqueado"] = True
                self.mensaje = f"ANOMALÍA LOGÍSTICA: ACUMULACIÓN DE TRÁFICO DETECTADA EN {cp_afectado['nombre']}."
            else:
                self.mensaje = f"FLUJO COMERCIAL NOMINAL: {len(self.buques)} ULTRA-GRANDES BUQUES EN TRÁNSITO."

        # Mover los buques y reinyectarlos al terminar
        buques_vivos = []
        for buque in self.buques:
            pos = self._interpolar_ruta(self.rutas[buque["ruta"]], buque["progreso"])
            
            velocidad_actual = buque["velocidad_base"]
            
            # Si hay un chokepoint bloqueado cerca, la velocidad cae casi a cero, creando la mancha
            for cp in self.chokepoints:
                if cp["bloqueado"]:
                    distancia = math.hypot(pos[0] - cp["x"], pos[1] - cp["y"])
                    if distancia < 30: # Radio de influencia del atasco
                        velocidad_actual *= 0.05 
            
            buque["progreso"] += velocidad_actual
            
            if buque["progreso"] < 1.0:
                buques_vivos.append(buque)
            else:
                # El buque llegó a puerto, se recicla creando uno nuevo en el origen
                self._crear_buque()
                
        self.buques = buques_vivos

    def draw(self, surface, color_linea, color_fondo):
        # Dibujamos las arterias invisibles del comercio usando píxeles de 1x1
        for buque in self.buques:
            x, y = self._interpolar_ruta(self.rutas[buque["ruta"]], buque["progreso"])
            # Un píxel puro, sin artificios
            surface.set_at((int(x), int(y)), color_linea)
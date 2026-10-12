from core.base_event import BaseEvent
import pygame
import random
import math
import time
import threading

class TejidoSubmarinoEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="14. EL TEJIDO SUBMARINO (CABLES ÓPTICOS)")
        self.mensaje = "MONITORIZANDO ENRUTAMIENTO BGP Y ESTADO FÍSICO DE FIBRA ÓPTICA..."
        self.width = 800
        self.height = 430
        
        # Red de arterias principales de Internet (Nombre, Lat/Lon Origen, Lat/Lon Destino)
        self.red_cables = [
            {"nombre": "TAT-14 / MAREA", "p1": (40.7, -74.0), "p2": (51.5, -0.1), "estado": "OK"}, # NY - Londres
            {"nombre": "SEABRAS-1", "p1": (40.7, -74.0), "p2": (-23.5, -46.6), "estado": "OK"}, # NY - Sao Paulo
            {"nombre": "FASTER", "p1": (34.0, -118.2), "p2": (35.6, 139.6), "estado": "OK"}, # LA - Tokio
            {"nombre": "SEA-ME-WE 5", "p1": (43.2, 5.3), "p2": (1.3, 103.8), "estado": "OK"}, # Marsella - Singapur
            {"nombre": "SOUTHERN CROSS", "p1": (34.0, -118.2), "p2": (-33.8, 151.2), "estado": "OK"}, # LA - Sídney
            {"nombre": "ELLALINK", "p1": (38.7, -9.1), "p2": (-3.7, -38.5), "estado": "OK"}, # Lisboa - Fortaleza
            {"nombre": "APG", "p1": (35.6, 139.6), "p2": (1.3, 103.8), "estado": "OK"}, # Tokio - Singapur
            {"nombre": "SACS", "p1": (-3.7, -38.5), "p2": (-8.8, 13.2), "estado": "OK"}, # Fortaleza - Luanda
            {"nombre": "AAE-1", "p1": (1.3, 103.8), "p2": (25.2, 55.2), "estado": "OK"}, # Singapur - Dubai
            {"nombre": "ARCTIC CONNECT", "p1": (51.5, -0.1), "p2": (35.6, 139.6), "estado": "OK"}, # Londres - Tokio
        ]
        
        self.cable_roto = None
        self.tiempo_rotura = 0
        
        self.ejecutando_hilo = True
        self.hilo_fallos = threading.Thread(target=self.simulador_anomalias_bgp)
        self.hilo_fallos.daemon = True
        self.hilo_fallos.start()

    def simulador_anomalias_bgp(self):
        while self.ejecutando_hilo:
            time.sleep(random.uniform(8.0, 20.0)) # Un evento crítico cada 8-20 segundos
            
            if not self.cable_roto:
                # Provocar un corte
                cable = random.choice(self.red_cables)
                cable["estado"] = "FAULT"
                self.cable_roto = cable
                self.tiempo_rotura = pygame.time.get_ticks()
                self.mensaje = f"CRÍTICO: PÉRDIDA DE TRÁFICO BGP DETECTADA EN RUTA {cable['nombre']}."
            else:
                # Reparar el corte anterior
                self.cable_roto["estado"] = "OK"
                self.cable_roto = None
                self.mensaje = "MONITORIZANDO ENRUTAMIENTO BGP Y ESTADO FÍSICO DE FIBRA ÓPTICA..."

    def proyectar_coordenadas(self, lat, lon):
        ESCALA_X = 1.0   
        ESCALA_Y = 1.20  
        centro_y = self.height / 2
        
        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        desviacion_y = (lat * (self.height / 180)) * ESCALA_Y
        base_y = centro_y - desviacion_y
        
        OFFSET_X = -25 
        OFFSET_Y = 10 
        
        return base_x + OFFSET_X, base_y + OFFSET_Y

    def calcular_curva_bezier(self, p0, p2, offset=0.2):
        # Ecuación cuadrática de Bézier para emular la curvatura oceánica y tensión del cable
        puntos = []
        pasos = 25
        
        # El punto de control (P1) tira de la línea hacia un lado u otro para curvarla
        mid_x = (p0[0] + p2[0]) / 2
        mid_y = (p0[1] + p2[1]) / 2
        
        dx = p2[0] - p0[0]
        dy = p2[1] - p0[1]
        
        # Vector perpendicular para la panza de la curva
        p1 = (mid_x - dy * offset, mid_y + dx * offset)
        
        for t_int in range(pasos + 1):
            t = t_int / pasos
            x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
            y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
            puntos.append((x, y))
            
        return puntos

    def update(self, tiempo_actual):
        pass # La lógica de tiempo la maneja el hilo asíncrono para no bloquear los frames

    def draw(self, surface, color_linea, color_fondo):
        tiempo_actual = pygame.time.get_ticks()
        
        for cable in self.red_cables:
            # Proyectar nodos físicos al mapa
            coord_1 = self.proyectar_coordenadas(cable["p1"][0], cable["p1"][1])
            coord_2 = self.proyectar_coordenadas(cable["p2"][0], cable["p2"][1])
            
            # Obtener el trazado curvo (el offset crea el arco en el mapa plano)
            puntos_curva = self.calcular_curva_bezier(coord_1, coord_2, offset=0.15)
            
            # 1. Nodos terrestres de conexión (Cajas rígidas / Landing Stations)
            pygame.draw.rect(surface, color_linea, (coord_1[0]-2, coord_1[1]-2, 5, 5))
            pygame.draw.rect(surface, color_linea, (coord_2[0]-2, coord_2[1]-2, 5, 5))
            
            if cable["estado"] == "OK":
                # Cable sano: línea continua, delgada y tensa
                pygame.draw.lines(surface, color_linea, False, puntos_curva, 1)
            else:
                # Cable seccionado: Destello de error y rotura visual
                if (tiempo_actual // 250) % 2 == 0:
                    # Dibujar el cable a trazos (fracturado)
                    for i in range(0, len(puntos_curva) - 1, 2):
                        pygame.draw.line(surface, color_linea, puntos_curva[i], puntos_curva[i+1], 2)
                    
                    # Dibujar un radar de advertencia en el punto medio de la rotura
                    mitad_curva = puntos_curva[len(puntos_curva)//2]
                    radio_alerta = (tiempo_actual % 1000) / 1000 * 30
                    pygame.draw.circle(surface, color_linea, (int(mitad_curva[0]), int(mitad_curva[1])), int(radio_alerta), 1)
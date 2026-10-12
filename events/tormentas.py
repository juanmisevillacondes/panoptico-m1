
from core.base_event import BaseEvent
import pygame
import threading
import requests
import time
import random

class TormentasEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="09. COSECHADOR DE TORMENTAS")
        self.tormentas_activas = []
        self.rayos_visuales = []
        self.mensaje = "INICIALIZANDO RASTREO METEOROLÓGICO GLOBAL..."
        self.ultimo_rayo = 0
        
        # Red de 15 nodos estratégicos en zonas de alta convección y densidad poblacional
        self.nodos = [
            {"nombre": "FLORIDA", "lat": 25.7, "lon": -80.1},
            {"nombre": "AMAZONAS", "lat": -3.4, "lon": -62.1},
            {"nombre": "CONGO", "lat": -0.7, "lon": 23.6},
            {"nombre": "JAVA", "lat": -6.2, "lon": 106.8},
            {"nombre": "N. AUSTRALIA", "lat": -12.4, "lon": 130.8},
            {"nombre": "INDIA OCC.", "lat": 19.0, "lon": 72.8},
            {"nombre": "JAPÓN", "lat": 35.6, "lon": 139.6},
            {"nombre": "R. UNIDO", "lat": 51.5, "lon": -0.1},
            {"nombre": "PEN. IBÉRICA", "lat": 40.4, "lon": -3.7},
            {"nombre": "RÍO DE LA PLATA", "lat": -34.6, "lon": -58.3},
            {"nombre": "MEDIO OESTE EEUU", "lat": 39.0, "lon": -94.5},
            {"nombre": "MALACA", "lat": 1.3, "lon": 103.8},
            {"nombre": "FILIPINAS", "lat": 14.5, "lon": 120.9},
            {"nombre": "ANDES", "lat": 4.7, "lon": -74.0},
            {"nombre": "CENTROAMÉRICA", "lat": 12.1, "lon": -86.2}
        ]

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_meteo)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_meteo(self):
        while self.ejecutando_hilo:
            nodos_activos = []
            nombres_activos = []
            
            self.mensaje = "CONSULTANDO CÓDIGOS WMO DE SATÉLITE..."
            
            for nodo in self.nodos:
                if not self.ejecutando_hilo:
                    break
                try:
                    url = f"https://api.open-meteo.com/v1/forecast?latitude={nodo['lat']}&longitude={nodo['lon']}&current=weather_code"
                    respuesta = requests.get(url, timeout=5)
                    
                    if respuesta.status_code == 200:
                        codigo = respuesta.json().get("current", {}).get("weather_code", 0)
                        # Códigos WMO: 61 a 65 (Lluvia), 80 a 82 (Chubascos), 95 a 99 (Tormentas)
                        if codigo >= 61: 
                            nodos_activos.append(nodo)
                            nombres_activos.append(nodo["nombre"])
                except Exception:
                    pass
                
                time.sleep(0.5)
            
            if nombres_activos:
                self.tormentas_activas = nodos_activos
                texto_nodos = ", ".join(nombres_activos[:3])
                if len(nombres_activos) > 3:
                    texto_nodos += f" (+{len(nombres_activos)-3})"
                self.mensaje = f"ACTIVIDAD ATMOSFÉRICA DETECTADA: {texto_nodos}"
            else:
                # MODO FALLBACK: Si no hay tormentas reales, activamos simulación para no apagar la pantalla
                self.mensaje = "CIELO DESPEJADO. MODO AUTÓNOMO: SIMULANDO FRENTES."
                self.tormentas_activas = random.sample(self.nodos, 3)
            
            time.sleep(300)

    def update(self, tiempo_actual):
        if tiempo_actual - self.ultimo_rayo > random.randint(50, 400):
            self.ultimo_rayo = tiempo_actual
            
            if self.tormentas_activas:
                nodo = random.choice(self.tormentas_activas)
                
                # Proyección con calibración exacta para el mapamundi
                OFFSET_X = 20
                OFFSET_Y = -5
                base_x = (nodo['lon'] + 180) * (800 / 360) + OFFSET_X
                base_y = (90 - nodo['lat']) * (430 / 180) + OFFSET_Y
                
                offset_x = random.randint(-20, 20)
                offset_y = random.randint(-20, 20)
                
                self.rayos_visuales.append([base_x + offset_x, base_y + offset_y, random.randint(3, 10)])

    def draw(self, surface, color_linea, color_fondo):
        for rayo in self.rayos_visuales[:]:
            pygame.draw.rect(surface, color_linea, (rayo[0], rayo[1], 4, 4))
            pygame.draw.rect(surface, color_linea, (rayo[0]-2, rayo[1]-2, 8, 8), 1)
            
            rayo[2] -= 1
            if rayo[2] <= 0:
                self.rayos_visuales.remove(rayo)
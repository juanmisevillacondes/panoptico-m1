from core.base_event import BaseEvent
import pygame
import threading
import requests
import time

class SismografoEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="SISMOGRAFO PLANETARIO")
        self.sismos = [] 
        self.mensaje = "CONECTANDO CON RED SÍSMICA GLOBAL (USGS)..."
        
        # Hilo secundario para no bloquear los 60 FPS
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_usgs)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_usgs(self):
        # API de terremotos de magnitud > 2.5 en el último día
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        
        while self.ejecutando_hilo:
            try:
                respuesta = requests.get(url, timeout=5)
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    nuevos_sismos = []
                    
                    # Extraemos el sismo más reciente y fuerte para el teletipo
                    if datos["features"]:
                        reciente = datos["features"][0]
                        mag = reciente["properties"]["mag"]
                        lugar = reciente["properties"]["place"]
                        self.mensaje = f"ÚLTIMO SISMO DETECTADO: MAG {mag} - {lugar.upper()}"
                    
                    for feature in datos["features"]:
                        lon = feature["geometry"]["coordinates"][0]
                        lat = feature["geometry"]["coordinates"][1]
                        mag = feature["properties"]["mag"]
                        
                        # Matemáticas de proyección (las mismas que usamos para la ISS)
                        x = (lon + 180) * (800 / 360)
                        y = (90 - lat) * (430 / 180)
                        
                        # Guardamos: x, y, magnitud, radio_actual_onda, radio_maximo_onda
                        radio_maximo = max(10, mag * 12) # Magnitud mayor = onda expansiva más grande
                        nuevos_sismos.append([x, y, mag, 1, radio_maximo])
                        
                    self.sismos = nuevos_sismos
                else:
                    self.mensaje = "ERROR DE LECTURA EN LA RED SÍSMICA GLOBAL."
            except Exception as e:
                self.mensaje = "PÉRDIDA DE CONEXIÓN CON USGS. REINTENTANDO ENLACE..."
            
            # El USGS recomienda consultar cada 60 segundos para no saturar su servidor
            time.sleep(60)

    def update(self, tiempo_actual):
        # Animamos las ondas expansivas de los terremotos
        for sismo in self.sismos:
            sismo[3] += 0.3 # Velocidad de expansión de la onda
            if sismo[3] > sismo[4]: # Si la onda alcanza su límite (según magnitud)
                sismo[3] = 1 # Se reinicia para crear un efecto de latido continuo

    def draw(self, surface, color_linea, color_fondo):
        for sismo in self.sismos:
            x, y, mag, radio_actual, radio_maximo = sismo
            
            # Dibujamos el epicentro (un punto estático)
            pygame.draw.circle(surface, color_linea, (int(x), int(y)), 2)
            
            # Dibujamos la onda sísmica expansiva
            pygame.draw.circle(surface, color_linea, (int(x), int(y)), int(radio_actual), 1)
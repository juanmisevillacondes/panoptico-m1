from core.base_event import BaseEvent
import pygame
import threading
import requests
import time
import math
import random

class OleajeEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="10. EL RESPIRO DEL OCÉANO (OLEAJE EXTREMO)")
        self.mensaje = "SINTONIZANDO RED DE BOYAS PROFUNDAS NDBC (NOAA) — BUSCANDO OLEAJE EXTREMO..."
        
        self.boyas_pasivas = []
        self.olas_extremas = []
        self.fase_animacion = 0.0
        
        self.width = 800
        self.height = 430
        
        # Coordenadas históricas de oleaje brutal (Cabo de Hornos, Mar del Norte, Bering)
        # Actúan como simulación de seguridad si la boya real no reporta tormentas hoy o no hay internet.
        self.historico_seguridad = [
            {"lat": -56.0, "lon": -67.0, "altura": 14.2, "ubicacion": "CABO DE HORNOS"},
            {"lat": 59.5, "lon": 2.0, "altura": 11.5, "ubicacion": "MAR DEL NORTE"},
            {"lat": 55.0, "lon": 170.0, "altura": 12.8, "ubicacion": "MAR DE BERING"},
            {"lat": 45.0, "lon": -40.0, "altura": 10.1, "ubicacion": "ATLÁNTICO NORTE (ZONA DE BORRASCAS)"},
            {"lat": -60.0, "lon": -120.0, "altura": 15.5, "ubicacion": "OCÉANO ANTÁRTICO"}
        ]
        
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_ndbc)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_ndbc(self):
        while self.ejecutando_hilo:
            try:
                # Archivo de texto plano crudo con la última lectura de todas las boyas mundiales
                url = "https://www.ndbc.noaa.gov/data/latest_obs/latest_obs.txt"
                respuesta = requests.get(url, timeout=15)
                
                if respuesta.status_code == 200:
                    lineas = respuesta.text.split('\n')
                    boyas_temp_pasivas = []
                    olas_temp_extremas = []
                    
                    # La primera línea contiene las cabeceras (LAT, LON, WVHT...)
                    cabeceras = lineas[0].split()
                    idx_lat = cabeceras.index('LAT')
                    idx_lon = cabeceras.index('LON')
                    idx_wvht = cabeceras.index('WVHT') # Altura de la ola en metros
                    
                    for linea in lineas[2:]: # Saltamos cabeceras y unidades
                        datos = linea.split()
                        if len(datos) > idx_wvht:
                            lat_str = datos[idx_lat]
                            lon_str = datos[idx_lon]
                            wvht_str = datos[idx_wvht]
                            
                            # 'MM' significa dato no disponible en esa boya
                            if wvht_str != 'MM' and lat_str != 'MM' and lon_str != 'MM':
                                lat = float(lat_str)
                                lon = float(lon_str)
                                altura = float(wvht_str)
                                
                                # Si la ola supera los 7.5 metros (marejada muy gruesa/arbolada)
                                if altura > 7.5:
                                    olas_temp_extremas.append({"lat": lat, "lon": lon, "altura": altura, "ubicacion": "BOYA NDBC"})
                                else:
                                    # Guardamos una de cada 10 boyas normales para no saturar la pantalla de puntos
                                    if random.random() < 0.1:
                                        boyas_temp_pasivas.append({"lat": lat, "lon": lon})
                    
                    self.boyas_pasivas = boyas_temp_pasivas
                    
                    if olas_temp_extremas:
                        self.olas_extremas = olas_temp_extremas
                        max_ola = max(olas_temp_extremas, key=lambda x: x['altura'])
                        self.mensaje = f"NDBC ALERTA: MAREJADA MASIVA DETECTADA. ALTURA MÁXIMA: {max_ola['altura']} METROS."
                    else:
                        # Si el mar global está en calma, activamos la simulación para mantener el arte vivo
                        self.activar_simulacion_seguridad()
                else:
                    self.activar_simulacion_seguridad()
            except Exception:
                self.activar_simulacion_seguridad()
            
            time.sleep(3600) # Consultar 1 vez por hora

    def activar_simulacion_seguridad(self):
        self.boyas_pasivas = []
        # Seleccionamos una tormenta masiva histórica al azar
        tormenta = random.choice(self.historico_seguridad)
        self.olas_extremas = [tormenta]
        self.mensaje = f"MODO AUTÓNOMO: SIMULANDO TORMENTA EXTREMA EN {tormenta['ubicacion']} — ALTURA: {tormenta['altura']} METROS."

    def proyectar_coordenadas(self, lat, lon):
        # --- MATEMÁTICAS CON CALIBRACIÓN DE PROYECCIÓN (HEREDADAS) ---
        ESCALA_X = 1.0   
        ESCALA_Y = 1.20  
        centro_y = self.height / 2
        
        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        desviacion_y = (lat * (self.height / 180)) * ESCALA_Y
        base_y = centro_y - desviacion_y
        
        OFFSET_X = -25 
        OFFSET_Y = 10 
        
        return int(base_x + OFFSET_X), int(base_y + OFFSET_Y)

    def update(self, tiempo_actual):
        # El tiempo avanza para animar el oleaje concéntrico
        self.fase_animacion += 0.05

    def draw(self, surface, color_linea, color_fondo):
        # 1. Dibujar la cuadrícula pasiva de boyas (Mar en calma)
        # Un punto de 1 píxel, muy sutil, que demuestra la red de vigilancia
        for boya in self.boyas_pasivas:
            ex, ey = self.proyectar_coordenadas(boya['lat'], boya['lon'])
            pygame.draw.rect(surface, color_linea, (ex, ey, 1, 1))

        # 2. Dibujar las anomalías masivas (Olas Extremas)
        for ola in self.olas_extremas:
            ex, ey = self.proyectar_coordenadas(ola['lat'], ola['lon'])
            altura_ola = ola['altura']
            
            # El epicentro clínico
            pygame.draw.circle(surface, color_linea, (ex, ey), 2)
            
            # Generación de la topografía del oleaje extremo
            # A mayor altura de la ola, más anillos se dibujan
            cantidad_anillos = int(altura_ola)
            
            for i in range(1, cantidad_anillos + 1):
                # El algoritmo de "respiro": usamos una onda senoidal que expande y contrae
                # los anillos basándose en el tiempo y el desfase de cada anillo.
                radio_base = i * 6
                # Ondulación (respiración) matemática
                pulsacion = math.sin(self.fase_animacion - (i * 0.5)) * (altura_ola * 0.3)
                radio_dinamico = max(1, radio_base + pulsacion)
                
                # Atenuación visual: Los anillos exteriores se dibujan discontinuos (simulando disipación)
                if i > cantidad_anillos - 3:
                    # Dibujamos 4 arcos en lugar de un círculo completo para crear líneas cortadas
                    rect = pygame.Rect(ex - radio_dinamico, ey - radio_dinamico, radio_dinamico * 2, radio_dinamico * 2)
                    pygame.draw.arc(surface, color_linea, rect, 0, math.pi/2 - 0.2, 1)
                    pygame.draw.arc(surface, color_linea, rect, math.pi, 3*math.pi/2 - 0.2, 1)
                else:
                    # Anillos interiores de tensión constante
                    pygame.draw.circle(surface, color_linea, (ex, ey), int(radio_dinamico), 1)
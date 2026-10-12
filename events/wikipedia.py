from core.base_event import BaseEvent
import pygame
import threading
import requests
import json
import time
import random
import math

class WikipediaPulseEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="11. EL PULSO DEL CONOCIMIENTO (WIKIPEDIA)")
        self.mensaje = "SINTONIZANDO EVENTSTREAM DE WIKIMEDIA — ESPERANDO EDICIONES..."
        
        self.pixeles_activos = []
        self.width = 800
        self.height = 430
        
        # Mapeo de códigos de Wikipedia a cajas delimitadoras geográficas (Lat Min, Lat Max, Lon Min, Lon Max)
        self.regiones_idioma = {
            'enwiki': [ (30, 50, -120, -70), (50, 55, -5, 2) ],       # Norteamérica, UK
            'eswiki': [ (36, 43, -9, 3), (-30, 30, -80, -50) ],       # España, LatAm
            'dewiki': [ (47, 54, 6, 14) ],                            # Alemania, Suiza, Austria
            'frwiki': [ (42, 51, -4, 8) ],                            # Francia
            'jawiki': [ (30, 45, 130, 145) ],                         # Japón
            'zhwiki': [ (20, 40, 100, 120) ],                         # China, Taiwán
            'ruwiki': [ (50, 65, 30, 100) ],                          # Rusia
            'ptwiki': [ (-30, 0, -60, -35), (37, 42, -9, -6) ],       # Brasil, Portugal
            'itwiki': [ (37, 46, 7, 18) ],                            # Italia
            'arwiki': [ (15, 35, -10, 50) ]                           # Norte de África, Medio Oriente
        }
        
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_wiki)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_coordenadas_por_wiki(self, wiki_code):
        # Si el idioma está mapeado, elegimos una región al azar de ese idioma
        if wiki_code in self.regiones_idioma:
            region = random.choice(self.regiones_idioma[wiki_code])
        else:
            # Si es un idioma menor, lo mandamos a una ubicación aleatoria del globo
            region = (-50, 60, -120, 120)
            
        lat = random.uniform(region[0], region[1])
        lon = random.uniform(region[2], region[3])
        return lat, lon

    def obtener_datos_wiki(self):
        url = "https://stream.wikimedia.org/v2/stream/recentchange"
        
        while self.ejecutando_hilo:
            try:
                # Conexión persistente al flujo de eventos
                respuesta = requests.get(url, stream=True, timeout=10)
                if respuesta.status_code == 200:
                    for linea in respuesta.iter_lines():
                        if not self.ejecutando_hilo:
                            break
                        
                        if linea:
                            linea_decodificada = linea.decode('utf-8')
                            if linea_decodificada.startswith('data: '):
                                try:
                                    datos = json.loads(linea_decodificada[6:])
                                    # Solo nos interesan ediciones de artículos reales (namespace 0)
                                    if datos.get('namespace') == 0:
                                        wiki = datos.get('wiki')
                                        titulo = datos.get('title')
                                        
                                        lat, lon = self.obtener_coordenadas_por_wiki(wiki)
                                        
                                        # Añadir a la lista de píxeles: [lat, lon, vida_util_maxima]
                                        # Limitamos la cantidad para no saturar la Raspberry Pi
                                        if len(self.pixeles_activos) < 150:
                                            self.pixeles_activos.append([lat, lon, 255.0])
                                            self.mensaje = f"PULSO DETECTADO: [{wiki}] {titulo}"
                                except json.JSONDecodeError:
                                    continue
                else:
                    self.generar_ruido_autonomo()
            except Exception:
                self.generar_ruido_autonomo()
                
            time.sleep(5)

    def generar_ruido_autonomo(self):
        # Modo de seguridad por si no hay red: simula ediciones globales
        self.mensaje = "MODO AUTÓNOMO: SIMULANDO FLUJO DE EDICIÓN GLOBAL..."
        while self.ejecutando_hilo:
            lat = random.uniform(-50, 60)
            lon = random.uniform(-120, 120)
            if len(self.pixeles_activos) < 100:
                self.pixeles_activos.append([lat, lon, 255.0])
            time.sleep(random.uniform(0.1, 0.5))

    def proyectar_coordenadas(self, lat, lon):
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
        # Desvanecer los píxeles (se apagan como chispas)
        for pixel in self.pixeles_activos[:]:
            pixel[2] -= 4.0 # Velocidad de apagado
            if pixel[2] <= 0:
                self.pixeles_activos.remove(pixel)

    def draw(self, surface, color_linea, color_fondo):
        # Capa temporal para gestionar la transparencia (desvanecimiento)
        superficie_temporal = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        for pixel in self.pixeles_activos:
            lat, lon, alpha = pixel[0], pixel[1], pixel[2]
            ex, ey = self.proyectar_coordenadas(lat, lon)
            
            # Limitar el alfa entre 0 y 255
            alpha_int = max(0, min(255, int(alpha)))
            color_trazo = (*color_linea[:3], alpha_int)
            
            # Dibujar un pequeño "destello" o chispa (Crucecita 3x3)
            pygame.draw.line(superficie_temporal, color_trazo, (ex - 1, ey), (ex + 1, ey), 1)
            pygame.draw.line(superficie_temporal, color_trazo, (ex, ey - 1), (ex, ey + 1), 1)

        surface.blit(superficie_temporal, (0, 0))
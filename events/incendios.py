from core.base_event import BaseEvent
import pygame
import threading
import requests
import io
import time
import random

class IncendiosForestalesEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="06. EL TERMÓMETRO DE LA BIOSFERA")
        self.mapa_incendios = None
        self.mensaje = "INICIALIZANDO RASTREO TÉRMICO DE LA BIOSFERA..."
        self.ultimo_rayo = 0
        self.rayos_visuales = [] 
        
        # NASA GIBS WMS en proyección Equirectangular (EPSG:4326)
        self.wms_url = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
        self.wms_layer = "MODIS_Terra_Thermal_Anomalies_All" 
        # Bounding box recortado para coincidir con la proporción visual del mapamundi.jpg
        self.bbo = "-180,-60,180,85" 
        self.width = 800
        self.height = 430
        
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_firms)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_firms(self):
        while self.ejecutando_hilo:
            self.mensaje = "CONSULTANDO ANOMALÍAS TÉRMICAS SATELITALES (NASA GIBS)..."
            
            try:
                # Petición al servidor GIBS usando proyección Equirectangular (EPSG:4326)
                wms_request = f"{self.wms_url}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS={self.wms_layer}&BBOX={self.bbo}&WIDTH={self.width}&HEIGHT={self.height}&SRS=EPSG:4326&FORMAT=image/png&TRANSPARENT=TRUE"
                respuesta = requests.get(wms_request, timeout=10)
                
                if respuesta.status_code == 200:
                    image_stream = io.BytesIO(respuesta.content)
                    mapa_temp = pygame.image.load(image_stream).convert_alpha()
                    self.mapa_incendios = self.procesar_imagen_fuego(mapa_temp)
                    self.mensaje = "PANÓPTICO TÉRMICO ACTUALIZADO. LA BIOSFERA ARDE."
                else:
                    self.generar_mapa_simulado()
            except Exception:
                self.generar_mapa_simulado()
            
            time.sleep(1800)

    def procesar_imagen_fuego(self, img):
        # --- TORNILLOS DE ESCALADO GEOMÉTRICO ---
        # Si África se sale por la derecha, significa que la imagen de la NASA es muy ancha.
        # Reducimos el ancho (ej. de 800 a 760) para "apretar" los continentes.
        NUEVO_ANCHO = 760 
        NUEVO_ALTO = 430
        
        # Escala la imagen mágicamente antes de procesar los píxeles
        img_escalada = pygame.transform.scale(img, (NUEVO_ANCHO, NUEVO_ALTO))
        processed_img = img_escalada.copy()
        
        for x in range(processed_img.get_width()):
            for y in range(processed_img.get_height()):
                r, g, b, a = processed_img.get_at((x, y))
                # Capturamos solo los colores cálidos de las anomalías térmicas
                if r > 150 and g < 150 and b < 100 and a > 0: 
                    processed_img.set_at((x, y), (255, 0, 0, 200)) # Fuego rojo intenso
                else:
                    processed_img.set_at((x, y), (0, 0, 0, 0)) # Transparente
                    
        return processed_img    

    def generar_mapa_simulado(self):
        """Plan B: Fuego procedimental con coordenadas Equirectangulares."""
        superficie_simulada = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        zonas_riesgo = [
            (250, 230, 40, 40),   # Amazonas
            (420, 210, 40, 40),   # África Central
            (670, 270, 40, 30),   # Australia
            (120, 120, 20, 30),   # California
            (600, 70, 60, 40)     # Siberia
        ]
        
        for zona in zonas_riesgo:
            cantidad_fuegos = random.randint(30, 100)
            for _ in range(cantidad_fuegos):
                px = zona[0] + random.randint(0, zona[2])
                py = zona[1] + random.randint(0, zona[3])
                px += random.randint(-15, 15)
                py += random.randint(-15, 15)
                
                if 0 <= px < self.width and 0 <= py < self.height:
                    superficie_simulada.set_at((px, py), (255, 0, 0, 150))
                    
        self.mapa_incendios = superficie_simulada
        self.mensaje = "MODO AUTÓNOMO ACTIVO: PATRONES TÉRMICOS PROCEDIMENTALES."

    def update(self, tiempo_actual):
        if self.mapa_incendios and (tiempo_actual - self.ultimo_rayo > random.randint(10, 40)):
            self.ultimo_rayo = tiempo_actual
            
            for _ in range(30):
                px = random.randint(0, self.width-1)
                py = random.randint(0, self.height-1)
                
                try:
                    r, g, b, a = self.mapa_incendios.get_at((px, py))
                    if r == 255 and a > 0: 
                        self.rayos_visuales.append([px, py, random.randint(5, 20)])
                        break
                except IndexError:
                    pass

    def draw(self, surface, color_linea, color_fondo):
        # --- TORNILLOS DE CALIBRACIÓN MANUAL ---
        # Ajustado a -75 para que encaje sobre la tierra de tu mapamundi específico.
        OFFSET_X = -25 
        OFFSET_Y = -15

        if self.mapa_incendios:
            surface.blit(self.mapa_incendios, (OFFSET_X, OFFSET_Y))
            
        for rayo in self.rayos_visuales[:]:
            rx = rayo[0] + OFFSET_X
            ry = rayo[1] + OFFSET_Y
            
            if 0 <= rx < self.width and 0 <= ry < self.height:
                pygame.draw.rect(surface, (255, 150, 0), (rx, ry, 3, 3))
                pygame.draw.rect(surface, (255, 50, 0), (rx-2, ry-2, 7, 7), 1)
            
            rayo[2] -= 1
            if rayo[2] <= 0:
                self.rayos_visuales.remove(rayo)
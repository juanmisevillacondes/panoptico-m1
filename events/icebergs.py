from core.base_event import BaseEvent
import pygame
import threading
import time
import math
import random

class SilencioPolarEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="12. EL SILENCIO POLAR (DESPRENDIMIENTOS)")
        self.mensaje = "SINCRONIZANDO CON NATIONAL ICE CENTER (USNIC) — TELEMETRÍA ANTÁRTICA..."
        
        self.icebergs_activos = []
        self.width = 800
        self.height = 430
        
        # Color de advertencia industrial (Rojo puro)
        self.color_alerta = (255, 40, 40)
        
        self.colosos_historicos = [
            {"nombre": "A-76", "area": 4320, "lat": -73.0, "lon": -43.0, "origen": "BARRERA DE RONNE"},
            {"nombre": "A-68", "area": 5800, "lat": -67.5, "lon": -60.0, "origen": "BARRERA DE LARSEN C"},
            {"nombre": "B-15", "area": 11000, "lat": -78.0, "lon": 162.0, "origen": "BARRERA DE ROSS"},
            {"nombre": "D-28", "area": 1636, "lat": -69.0, "lon": 71.0, "origen": "BARRERA DE AMERY"},
            {"nombre": "A-74", "area": 1270, "lat": -75.0, "lon": -25.0, "origen": "BARRERA DE BRUNT"}
        ]
        
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_usnic)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_usnic(self):
        while self.ejecutando_hilo:
            if len(self.icebergs_activos) < 1:
                iceberg = random.choice(self.colosos_historicos)
                escala = math.sqrt(iceberg["area"]) / 12 
                
                forma_base = [
                    (random.uniform(-escala, -escala/2), random.uniform(-escala, -escala/2)),
                    (random.uniform(escala/2, escala), random.uniform(-escala, -escala/2)),
                    (random.uniform(escala/2, escala), random.uniform(escala/2, escala)),
                    (random.uniform(-escala/2, 0), random.uniform(escala, escala*1.2)),
                    (random.uniform(-escala, -escala/2), random.uniform(escala/2, escala))
                ]
                
                self.icebergs_activos.append({
                    "datos": iceberg,
                    "lat_actual": iceberg["lat"],
                    "lon_actual": iceberg["lon"],
                    "deriva_lat": random.uniform(0.0001, 0.0003),
                    "deriva_lon": random.uniform(-0.0002, 0.0002),
                    "forma": forma_base
                })
                
                self.mensaje = f"USNIC ALERTA: DESPRENDIMIENTO MASIVO EN {iceberg['origen']}. ICEBERG {iceberg['nombre']} A LA DERIVA."
            
            time.sleep(86400)

    def proyectar_coordenadas(self, lat, lon):
        ESCALA_X = 1.0   
        ESCALA_Y = 1.20  
        centro_y = self.height / 2
        
        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        desviacion_y = (lat * (self.height / 180)) * ESCALA_Y
        base_y = centro_y - desviacion_y
        
        OFFSET_X = -25 
        # He subido ligeramente el OFFSET_Y negativo para separar el iceberg del teletipo inferior
        OFFSET_Y = -15 
        
        return base_x + OFFSET_X, base_y + OFFSET_Y

    def update(self, tiempo_actual):
        for ice in self.icebergs_activos[:]:
            ice["lat_actual"] += ice["deriva_lat"]
            ice["lon_actual"] += ice["deriva_lon"]
            
            if ice["lat_actual"] > -50:
                self.icebergs_activos.remove(ice)

    def draw(self, surface, color_linea, color_fondo):
        tiempo_actual = pygame.time.get_ticks()
        
        # Capa temporal para gestionar la transparencia del pulso rojo
        superficie_alertas = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        for ice in self.icebergs_activos:
            px, py = self.proyectar_coordenadas(ice["lat_actual"], ice["lon_actual"])
            
            # 1. Animación del pulso rojo cuadrado
            # Crea un ciclo de 0.0 a 1.0 cada 2 segundos (2000 ms)
            ciclo_animacion = (tiempo_actual % 2000) / 2000.0
            
            # El cuadrado crece de 10 a 60 píxeles de lado
            tamano_cuadrado = 10 + (ciclo_animacion * 50)
            # La opacidad se desvanece de 255 a 0 a medida que crece
            opacidad = int(255 * (1.0 - ciclo_animacion))
            
            color_pulso = (*self.color_alerta, opacidad)
            rect_pulso = pygame.Rect(
                px - (tamano_cuadrado / 2), 
                py - (tamano_cuadrado / 2), 
                tamano_cuadrado, 
                tamano_cuadrado
            )
            
            # Dibujamos el cuadrado de alerta (grosor 2)
            pygame.draw.rect(superficie_alertas, color_pulso, rect_pulso, 2)
            
            # 2. Dibujar el bloque de hielo (Relleno sólido)
            puntos_reales = [(px + vx, py + vy) for vx, vy in ice["forma"]]
            pygame.draw.polygon(surface, color_linea, puntos_reales, 0)
            pygame.draw.polygon(surface, color_fondo, puntos_reales, 1) # Borde para separarlo del mapa
            
            # 3. Tipografía clínica
            fuente = pygame.font.SysFont("arial", 9, bold=True)
            etiqueta = f"{ice['datos']['nombre']} | {ice['datos']['area']} KM²"
            texto = fuente.render(etiqueta, True, color_fondo)
            
            fondo_rect = texto.get_rect(topleft=(int(px) + 12, int(py) - 12)).inflate(4, 4)
            pygame.draw.rect(surface, color_linea, fondo_rect)
            surface.blit(texto, (int(px) + 14, int(py) - 10))
            
        # Volcamos la capa de alertas rojas sobre la pantalla principal
        surface.blit(superficie_alertas, (0, 0))
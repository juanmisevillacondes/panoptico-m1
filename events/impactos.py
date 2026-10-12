from core.base_event import BaseEvent
import pygame
import threading
import requests
import time
import math
import random

class ImpactosEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="09. EL IMPACTO CELESTE (BÓLIDOS)")
        self.mensaje = "CALIBRANDO TELEMETRÍA JPL (NASA) — VIGILANCIA ORBITAL ACTIVA..."
        
        self.datos_bolidos = []
        self.evento_actual = None
        self.fase_animacion = 0
        self.tiempo_ultimo_impacto = 0
        
        self.width = 800
        self.height = 430
        
        # Base histórica de seguridad por si la API de la NASA falla o no hay red
        self.historico_seguridad = [
            {"lat": 55.15, "lon": 61.41, "energia": "440", "alt": "23.3"},  # Cheliábinsk
            {"lat": 53.00, "lon": 173.00, "energia": "173", "alt": "25.6"}, # Mar de Bering
            {"lat": -35.00, "lon": 50.00, "energia": "14", "alt": "32.0"},  # Océano Índico
            {"lat": 6.00, "lon": -40.00, "energia": "3.8", "alt": "38.5"},  # Atlántico Central
            {"lat": 60.00, "lon": -120.00, "energia": "2.5", "alt": "45.0"} # Canadá
        ]
        
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_jpl)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_jpl(self):
        while self.ejecutando_hilo:
            try:
                # API pública de bólidos atmosféricos (Fireballs) del JPL de la NASA
                url = "https://ssd-api.jpl.nasa.gov/fireball.api?limit=20"
                respuesta = requests.get(url, timeout=10)
                
                if respuesta.status_code == 200:
                    datos_nasa = respuesta.json()
                    campos = datos_nasa.get('fields', [])
                    datos_crudos = datos_nasa.get('data', [])
                    
                    bolidos_procesados = []
                    for fila in datos_crudos:
                        # Extraemos los índices basados en la respuesta de la NASA
                        try:
                            lat = float(fila[campos.index('lat')])
                            if fila[campos.index('lat-dir')] == 'S': lat = -lat
                            
                            lon = float(fila[campos.index('lon')])
                            if fila[campos.index('lon-dir')] == 'W': lon = -lon
                            
                            energia = fila[campos.index('impact-e')]
                            alt = fila[campos.index('alt')]
                            
                            if energia and alt: # Solo eventos con telemetría completa
                                bolidos_procesados.append({"lat": lat, "lon": lon, "energia": energia, "alt": alt})
                        except (ValueError, TypeError, ValueError):
                            continue
                    
                    if bolidos_procesados:
                        self.datos_bolidos = bolidos_procesados
                else:
                    self.datos_bolidos = self.historico_seguridad
            except Exception:
                self.datos_bolidos = self.historico_seguridad
            
            time.sleep(3600) # Consultar 1 vez por hora (son eventos muy raros)

    def update(self, tiempo_actual):
        # Disparamos visualmente un impacto cada 15-30 segundos (configurable)
        # para que el dispositivo mantenga su valor contemplativo.
        if tiempo_actual - self.tiempo_ultimo_impacto > random.randint(15000, 30000):
            self.tiempo_ultimo_impacto = tiempo_actual
            
            lista_origen = self.datos_bolidos if self.datos_bolidos else self.historico_seguridad
            impacto = random.choice(lista_origen)
            
            # --- MATEMÁTICAS CON CALIBRACIÓN DE PROYECCIÓN (HEREDADAS) ---
            ESCALA_X = 1.0   
            ESCALA_Y = 1.20  
            centro_y = self.height / 2
            
            base_x = ((impacto['lon'] + 180) * (self.width / 360)) * ESCALA_X
            desviacion_y = (impacto['lat'] * (self.height / 180)) * ESCALA_Y
            base_y = centro_y - desviacion_y
            
            OFFSET_X = -25 
            OFFSET_Y = 10 
            
            final_x = base_x + OFFSET_X
            final_y = base_y + OFFSET_Y
            
            # Parámetros del vector visual (Trayectoria de entrada)
            angulo_entrada = random.uniform(0, 2 * math.pi)
            longitud_vector = random.randint(300, 800) # Corta toda la pantalla
            
            self.evento_actual = {
                "x": final_x, 
                "y": final_y, 
                "angulo": angulo_entrada, 
                "longitud": longitud_vector
            }
            
            self.fase_animacion = 255 # Opacidad máxima inicial (Destello)
            self.mensaje = f"IMPACTO DETECTADO — ENERGÍA: {impacto['energia']} KILOTONES / ALTITUD DETONACIÓN: {impacto['alt']} KM"

        # Decadencia de la cicatriz visual (Se borra muy lentamente)
        if self.evento_actual:
            self.fase_animacion -= 1.0 
            if self.fase_animacion <= 0:
                self.evento_actual = None
                self.mensaje = "VIGILANCIA ORBITAL ACTIVA. ESPERANDO DATOS JPL (NASA)..."

    def draw(self, surface, color_linea, color_fondo):
        if self.evento_actual and self.fase_animacion > 0:
            ex = self.evento_actual["x"]
            ey = self.evento_actual["y"]
            angulo = self.evento_actual["angulo"]
            long = self.evento_actual["longitud"]
            
            # Para el efecto de "fading" (desvanecimiento), usamos una superficie transparente
            alpha = max(0, min(255, int(self.fase_animacion)))
            superficie_temporal = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            color_trazo = (*color_linea[:3], alpha)
            
            # 1. La trayectoria vectorial (Línea cortante)
            p1 = (ex - math.cos(angulo) * long, ey - math.sin(angulo) * long)
            p2 = (ex + math.cos(angulo) * long, ey + math.sin(angulo) * long)
            pygame.draw.aalines(superficie_temporal, color_trazo, False, [p1, p2])
            
            # 2. La marca de detonación clínica (Cruz Bauhaus)
            ancho_cruz = 8
            pygame.draw.line(superficie_temporal, color_trazo, (ex - ancho_cruz, ey), (ex + ancho_cruz, ey), 1)
            pygame.draw.line(superficie_temporal, color_trazo, (ex, ey - ancho_cruz), (ex, ey + ancho_cruz), 1)
            
            # Anillo de impacto estático
            pygame.draw.circle(superficie_temporal, color_trazo, (int(ex), int(ey)), 4, 1)
            
            # Volcar la superficie transparente sobre la pantalla principal
            surface.blit(superficie_temporal, (0, 0))
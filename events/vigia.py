from core.base_event import BaseEvent
import pygame
import threading
import requests
import time

class VigiaEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="VIGIA ORBITAL")
        self.iss_x = -10
        self.iss_y = -10
        self.latitud = 0.0
        self.longitud = 0.0
        self.mensaje = "CONECTANDO CON SATÉLITES DE TELEMETRÍA..."
        self.fuente_radar = pygame.font.SysFont("consolas", 12)
        
        # Bandera para controlar el hilo secundario
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_iss)
        self.hilo_datos.daemon = True # El hilo muere automáticamente si cierras el programa
        self.hilo_datos.start()

    def obtener_datos_iss(self):
        """Este bucle se ejecuta en la sombra, sin bloquear los 60 FPS de Pygame."""
        while self.ejecutando_hilo:
            try:
                respuesta = requests.get("http://api.open-notify.org/iss-now.json", timeout=5)
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    self.latitud = float(datos["iss_position"]["latitude"])
                    self.longitud = float(datos["iss_position"]["longitude"])
                    
                    # --- MATEMÁTICAS DE PROYECCIÓN (Coordenadas a Píxeles) ---
                    # La longitud va de -180 (Oeste) a 180 (Este). Ancho pantalla: 800px
                    self.iss_x = (self.longitud + 180) * (800 / 360)
                    
                    # La latitud va de 90 (Norte) a -90 (Sur). Alto pantalla disponible: 430px
                    self.iss_y = (90 - self.latitud) * (430 / 180)

                    # Actualizamos el teletipo con los datos puros
                    self.mensaje = f"TELEMETRÍA ISS: LAT {self.latitud:.4f} / LON {self.longitud:.4f} — A 422 KM DE ALTITUD"
                else:
                    self.mensaje = "ERROR DE ENLACE CON LA ESTACIÓN ESPACIAL."
            except Exception as e:
                self.mensaje = "PÉRDIDA DE SEÑAL. REINTENTANDO CONEXIÓN..."
            
            # La ISS se mueve rápido, pero consultar cada 3 segundos es un buen equilibrio
            time.sleep(3)

    def update(self, tiempo_actual):
        # La lógica de cálculo ahora vive en el hilo secundario. 
        # Aquí solo mantendríamos animaciones locales si fueran necesarias.
        pass

    def draw(self, surface, color_linea, color_fondo):
        # Si aún no tenemos coordenadas válidas, no dibujamos el satélite
        if self.iss_x < 0:
            return

        # Dibujamos una cruz de rastreo estilo radar (arquitectura Bauhaus)
        pygame.draw.line(surface, color_linea, (self.iss_x - 10, self.iss_y), (self.iss_x + 10, self.iss_y), 1)
        pygame.draw.line(surface, color_linea, (self.iss_x, self.iss_y - 10), (self.iss_x, self.iss_y + 10), 1)
        
        # El bloque sólido de la estación
        pygame.draw.rect(surface, color_linea, (int(self.iss_x)-3, int(self.iss_y)-3, 6, 6))
        
        # Etiqueta de identificación
        etiqueta = self.fuente_radar.render("ISS", True, color_fondo)
        fondo_etiqueta = etiqueta.get_rect(topleft=(int(self.iss_x) + 8, int(self.iss_y) - 8)).inflate(4, 2)
        
        pygame.draw.rect(surface, color_linea, fondo_etiqueta)
        surface.blit(etiqueta, (int(self.iss_x) + 10, int(self.iss_y) - 7))
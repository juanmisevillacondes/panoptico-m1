from core.base_event import BaseEvent
import pygame
import threading
import requests
import time
import math

class HeliosEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="07. EL RELOJ HELIOS (CLIMA ESPACIAL)")
        self.kp_index = 0.0
        self.mensaje = "SINTONIZANDO SENSORES DE VIENTO SOLAR (NOAA SWPC)..."
        self.fase_fluido = 0.0
        
        self.width = 800
        self.height = 430
        
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_espaciales)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_espaciales(self):
        while self.ejecutando_hilo:
            try:
                # API pública y gratuita de la NOAA para el Índice Kp (Planetary K-index)
                # El índice Kp va de 0 (Calma absoluta) a 9 (Tormenta Geomagnética Extrema)
                url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
                respuesta = requests.get(url, timeout=10)
                
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    # El JSON devuelve una lista de listas. La última posición tiene el dato más reciente.
                    # Ejemplo: ["2023-10-25 18:00:00", "3.33"]
                    ultimo_dato = datos[-1]
                    self.kp_index = float(ultimo_dato[1])
                    
                    if self.kp_index >= 5.0:
                        self.mensaje = f"ALERTA: TORMENTA GEOMAGNÉTICA EN CURSO. ÍNDICE Kp: {self.kp_index} - RIESGO AURORAS."
                    elif self.kp_index >= 4.0:
                        self.mensaje = f"CLIMA ESPACIAL ACTIVO. ÍNDICE Kp: {self.kp_index} - PERTURBACIONES MAGNÉTICAS."
                    else:
                        self.mensaje = f"ESCUDO MAGNETOSFÉRICO ESTABLE. ÍNDICE Kp: {self.kp_index}"
                else:
                    self.activar_simulacion()
            except Exception:
                self.activar_simulacion()
            
            # El clima espacial cambia lentamente. Consultamos cada 15 minutos.
            time.sleep(900)

    def activar_simulacion(self):
        self.mensaje = "MODO AUTÓNOMO ACTIVO: SIMULANDO TORMENTA SOLAR (Kp: 6.0)."
        self.kp_index = 6.0

    def update(self, tiempo_actual):
        # La velocidad a la que "fluyen" las ondas depende directamente del impacto solar (Kp)
        velocidad_base = 0.005
        aceleracion_solar = self.kp_index * 0.003
        self.fase_fluido += (velocidad_base + aceleracion_solar)

    def draw(self, surface, color_linea, color_fondo):
        # El alcance (hacia el ecuador) y la altura de las ondas crecen con el índice Kp
        amplitud = 5 + (self.kp_index * 8)
        alcance_latitud = 20 + (self.kp_index * 15)
        
        # Cantidad de "hilos" o líneas magnéticas
        num_capas = 6 
        
        # Si hay una tormenta solar (Kp >= 5), inyectamos un tono rojizo a las ondas
        color_onda = (200, 200, 200) if color_fondo == (0, 0, 0) else (100, 100, 100)
        if self.kp_index >= 5:
            color_onda = (255, 80, 80) # Rojo advertencia minimalista

        for i in range(num_capas):
            puntos_norte = []
            puntos_sur = []
            
            # Desfases para que las líneas no se pisen y parezcan un fluido continuo
            offset_capa = i * 0.5
            freq_espacial = 0.01 + (i * 0.002)
            
            for x in range(0, self.width + 10, 15):
                # ALGORITMO DE FLUIDO: Combinamos dos ondas sinusoidales a diferentes velocidades y escalas
                # para crear un patrón de interferencia que se asemeja al viento magnético.
                onda_1 = math.sin(x * freq_espacial + self.fase_fluido + offset_capa)
                onda_2 = math.cos(x * 0.005 - (self.fase_fluido * 1.5) + offset_capa)
                
                # Turbulencia extra si hay tormenta solar fuerte
                turbulencia = 0
                if self.kp_index >= 5:
                    turbulencia = math.sin(x * 0.05 + self.fase_fluido * 5) * (self.kp_index * 1.5)

                ruido_magnetico = (onda_1 + onda_2) * amplitud + turbulencia
                
                # Distancia desde los polos hacia el centro (Ecuador)
                separacion_polos = alcance_latitud - (i * 12)
                
                # Polo Norte (Crecen hacia abajo)
                y_norte = separacion_polos + ruido_magnetico
                # Polo Sur (Crecen hacia arriba)
                y_sur = (self.height - separacion_polos) - ruido_magnetico
                
                # Suavizado en los bordes horizontales de la pantalla para que las líneas nazcan limpias
                atenuacion_bordes = math.sin(math.pi * (x / self.width))
                y_norte = (y_norte * atenuacion_bordes)
                y_sur = self.height - ((self.height - y_sur) * atenuacion_bordes)

                # Evitamos que crucen el ecuador y rompan el dibujo
                y_norte = max(0, min(self.height / 2, y_norte))
                y_sur = min(self.height, max(self.height / 2, y_sur))
                
                puntos_norte.append((x, int(y_norte)))
                puntos_sur.append((x, int(y_sur)))
            
            # Dibujamos las ondas magnéticas con líneas suavizadas (Anti-Aliasing)
            if len(puntos_norte) > 2:
                pygame.draw.aalines(surface, color_onda, False, puntos_norte)
            if len(puntos_sur) > 2:
                pygame.draw.aalines(surface, color_onda, False, puntos_sur)
                
        # EFECTO LLAMARADA SOLAR: Si el Kp es muy alto, dibujamos halos concéntricos en los polos
        if self.kp_index >= 6:
            radio_halo = int((math.sin(self.fase_fluido * 3) + 1) * 30) + 10
            # Halo Polo Norte
            pygame.draw.circle(surface, color_onda, (self.width // 2, 0), radio_halo, 1)
            pygame.draw.circle(surface, color_onda, (self.width // 2, 0), radio_halo + 20, 1)
            # Halo Polo Sur
            pygame.draw.circle(surface, color_onda, (self.width // 2, self.height), radio_halo, 1)
            pygame.draw.circle(surface, color_onda, (self.width // 2, self.height), radio_halo + 20, 1)
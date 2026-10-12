from core.base_event import BaseEvent
import pygame
from datetime import datetime
import math

class RelojPlanetarioEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="13. LA SOMBRA DEL TERMINADOR")
        self.mensaje = "CALCULANDO MECÁNICA ORBITAL..."
        
        self.width = 800
        self.height = 430
        
        # 1. Pre-generar la superficie del patrón Halftone
        # Creamos una textura de puntos densa para representar la noche
        self.halftone = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dot_spacing = 3
        
        for y in range(0, self.height, dot_spacing):
            for x in range(0, self.width, dot_spacing):
                # Desplazamiento alterno para generar un patrón de trama de impresión clásica
                if (x // dot_spacing + y // dot_spacing) % 2 == 0:
                    # Usamos negro puro con opacidad 190. Esto ensombrece el mapa blanco
                    # y oscurece las líneas del mapa en el modo oscuro.
                    pygame.draw.circle(self.halftone, (0, 0, 0, 190), (x, y), 1)

    def inversa_proyectar_x(self, x):
        # Transforma el píxel de la pantalla X en una Longitud geográfica (-180 a 180)
        # para que la sombra del sol encaje perfectamente con la imagen de fondo.
        ESCALA_X = 1.0
        OFFSET_X = -25 
        lon = ((x - OFFSET_X) / ESCALA_X) * 360.0 / self.width - 180.0
        return lon

    def proyectar_coordenadas(self, lat, lon):
        # Proyección estándar heredada para mantener la geometría de tu mapa
        ESCALA_X = 1.0   
        ESCALA_Y = 1.20  
        centro_y = self.height / 2
        
        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        desviacion_y = (lat * (self.height / 180)) * ESCALA_Y
        base_y = centro_y - desviacion_y
        
        OFFSET_X = -25 
        OFFSET_Y = 10 
        
        return base_x + OFFSET_X, base_y + OFFSET_Y

    def update(self, tiempo_actual):
        ahora = datetime.utcnow()
        hora_str = ahora.strftime("%H:%M:%S UTC")
        
        # Cálculo del día del año (1 a 365) para averiguar la estación
        dia_del_ano = ahora.timetuple().tm_yday
        # Ecuación de declinación solar aproximada (varía entre -23.44° y +23.44°)
        declinacion = -23.44 * math.cos(math.radians((360.0 / 365.25) * (dia_del_ano + 10)))
        
        self.mensaje = f"RELOJ PLANETARIO — LÍNEA DEL TERMINADOR EN DIRECTO — {hora_str} | DECL. SOLAR: {declinacion:.1f}°"

    def draw(self, surface, color_linea, color_fondo):
        ahora = datetime.utcnow()
        dia_del_ano = ahora.timetuple().tm_yday
        
        declinacion = -23.44 * math.cos(math.radians((360.0 / 365.25) * (dia_del_ano + 10)))
        # Prevenir un error matemático en los equinoccios exactos (división por cero)
        if abs(declinacion) < 0.01:
            declinacion = 0.01

        # Calcular en qué meridiano está pegando el sol directamente ahora mismo
        hora_decimal = ahora.hour + ahora.minute / 60.0 + ahora.second / 3600.0
        lon_subsolar = (12.0 - hora_decimal) * 15.0
        if lon_subsolar < -180: lon_subsolar += 360
        if lon_subsolar > 180: lon_subsolar -= 360

        puntos_terminador = []
        
        # Recorremos la pantalla de izquierda a derecha para generar la curva de la sombra
        for x in range(-10, self.width + 10, 5):
            lon = self.inversa_proyectar_x(x)
            
            # Matemática del Terminador: calculamos la latitud donde atardece/amanece
            # para esta longitud exacta.
            cot_decl = 1.0 / math.tan(math.radians(declinacion))
            cos_diff = math.cos(math.radians(lon - lon_subsolar))
            tan_lat = -cot_decl * cos_diff
            lat = math.degrees(math.atan(tan_lat))
            
            _, py = self.proyectar_coordenadas(lat, lon)
            puntos_terminador.append((x, py))

        # 2. Construir el polígono que representa la noche
        poligono_noche = puntos_terminador.copy()
        
        # Si estamos en verano boreal (decl > 0), la noche domina el polo sur.
        # Si estamos en invierno boreal (decl < 0), la noche domina el polo norte.
        y_lim = self.height + 200 if declinacion > 0 else -200
        
        poligono_noche.append((puntos_terminador[-1][0], y_lim))
        poligono_noche.append((puntos_terminador[0][0], y_lim))

        # 3. La Magia Visual: Máscara y Halftone
        # Creamos una capa en blanco temporal
        shadow_layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Dibujamos el polígono de la noche en blanco puro en esa capa
        pygame.draw.polygon(shadow_layer, (255, 255, 255, 255), poligono_noche)
        
        # Fundimos la trama de halftone utilizando BLEND_RGBA_MULT.
        # Esto hace que la trama de puntos exista *únicamente* dentro del polígono.
        shadow_layer.blit(self.halftone, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        # Volcamos la sombra terminada a la pantalla principal
        surface.blit(shadow_layer, (0, 0))

        # Finalmente, dibujamos un trazado fino puro marcando la división exacta de luz
        if len(puntos_terminador) > 1:
            pygame.draw.lines(surface, color_linea, False, puntos_terminador, 1)
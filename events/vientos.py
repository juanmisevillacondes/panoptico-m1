from core.base_event import BaseEvent
import pygame
import random
import math

class MapaVientosEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="16. EL MAPA DE VIENTOS (FLUIDOS)")
        self.mensaje = "SINTETIZANDO DINÁMICA DE FLUIDOS ATMOSFÉRICA..."
        
        self.width = 800
        self.height = 430
        
        # 1200 partículas es el punto dulce para mantener 60 FPS fluidos en una Pi 4
        self.num_particulas = 1200 
        self.particulas = []
        
        # Semilla de tiempo para animar los sistemas de presión
        self.tiempo_fluido = 0.0
        
        # Pre-poblar el mapa
        for _ in range(self.num_particulas):
            self.respawn_particula()

    def respawn_particula(self, p=None):
        x = random.uniform(0, self.width)
        y = random.uniform(0, self.height)
        edad = 0
        vida_maxima = random.randint(30, 150)
        velocidad = random.uniform(0.8, 2.5)
        
        if p is not None:
            p[0] = x
            p[1] = y
            p[2] = edad
            p[3] = vida_maxima
            p[4] = velocidad
        else:
            # Estructura: [x, y, edad, vida_max, velocidad]
            self.particulas.append([x, y, edad, vida_maxima, velocidad])

    def calcular_vector(self, x, y):
        # Convertimos las coordenadas a un espacio matemático mapeado al globo
        nx = (x / self.width) * math.pi * 2.0
        ny = (y / self.height) * math.pi
        
        # 1. Bandas Climáticas Globales
        # math.cos(ny * 3.0) crea las 3 franjas de circulación (Alisios y Westerlies)
        banda_x = -math.cos(ny * 3.0) 
        banda_y = 0.0
        
        # 2. Sistemas de Presión (Ciclones y Anticiclones generados proceduralmente)
        # Cruzamos senos y cosenos desplazados por el tiempo para crear vórtices cambiantes
        turbulencia_x = math.sin(nx * 3.0 + self.tiempo_fluido) * math.cos(ny * 4.0)
        turbulencia_y = math.cos(nx * 4.0) * math.sin(ny * 3.0 + self.tiempo_fluido)
        
        # Sumamos las corrientes globales con la turbulencia local
        vx = banda_x + (turbulencia_x * 1.2)
        vy = banda_y + (turbulencia_y * 1.2)
        
        # Normalizamos el vector resultante para mantener una velocidad constante
        magnitud = math.hypot(vx, vy)
        if magnitud == 0: magnitud = 1
        return vx / magnitud, vy / magnitud

    def update(self, tiempo_actual):
        # Avanzamos el reloj climático muy lentamente para que las tormentas se muevan
        self.tiempo_fluido += 0.005 
        
        for p in self.particulas:
            p[2] += 1 # Envejecer partícula
            
            # Si muere por edad o se sale del mapa, reaparece en un punto aleatorio
            if p[2] > p[3] or p[0] < 0 or p[0] > self.width or p[1] < 0 or p[1] > self.height:
                self.respawn_particula(p)
            else:
                # Mover partícula siguiendo el campo vectorial
                vx, vy = self.calcular_vector(p[0], p[1])
                p[0] += vx * p[4]
                p[1] += vy * p[4]

    def draw(self, surface, color_linea, color_fondo):
        # En lugar de dibujar un solo píxel por partícula, dibujamos un trazo que une 
        # la posición actual con un cálculo de dónde estaba hace unos milisegundos.
        # Esto engaña al ojo creando un "motion blur" masivo y sedoso sin coste de RAM.
        
        for p in self.particulas:
            vx, vy = self.calcular_vector(p[0], p[1])
            
            # Longitud del trazo basada en su velocidad individual
            cola_x = p[0] - (vx * p[4] * 2.5)
            cola_y = p[1] - (vy * p[4] * 2.5)
            
            # Difuminado óptico: Si la partícula está naciendo o muriendo, la dibujamos más fina
            if p[2] < 10 or (p[3] - p[2]) < 10:
                pygame.draw.rect(surface, color_linea, (int(p[0]), int(p[1]), 1, 1))
            else:
                pygame.draw.line(surface, color_linea, (int(cola_x), int(cola_y)), (int(p[0]), int(p[1])), 1)
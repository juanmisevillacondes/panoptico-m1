from core.base_event import BaseEvent
import pygame
import math
import threading
import requests
import time

class FuriaSolarEvent(BaseEvent):
    # Orden de severidad de las fulguraciones solares en rayos X (escala real de la NOAA)
    ORDEN_CLASE = {"A": 0, "B": 1, "C": 2, "M": 3, "X": 4}
    RIESGO_HF = {
        "A": "NINGUNO", "B": "NINGUNO",
        "C": "MENOR",
        "M": "MODERADO — POSIBLE AFECTACIÓN DE RADIO HF EN CARA DIURNA",
        "X": "SEVERO — APAGÓN DE RADIO HF PROBABLE EN CARA DIURNA",
    }

    def __init__(self):
        super().__init__(name="27. LA FURIA SOLAR (FULGURACIONES EN RAYOS X)")
        self.mensaje = "SINTONIZANDO SATÉLITES GOES (NOAA SWPC) — MONITORIZANDO RAYOS X SOLARES..."

        self.width = 800
        self.height = 430

        self.letra = "A"
        self.numero = 0.0
        self.max_class = "A0.0"
        self.max_time = ""

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_swpc)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_swpc(self):
        # API pública y gratuita de la NOAA SWPC (satélites GOES), sin necesidad de clave.
        url = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json"

        while self.ejecutando_hilo:
            try:
                respuesta = requests.get(url, timeout=15)
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    if datos:
                        evento = datos[0]
                        self.max_class = evento.get("max_class", "A0.0")
                        self.max_time = evento.get("max_time", "")
                        self.letra, self.numero = self._descomponer_clase(self.max_class)

                        riesgo = self.RIESGO_HF.get(self.letra, "DESCONOCIDO")
                        self.mensaje = (
                            f"NOAA SWPC: FULGURACIÓN CLASE {self.max_class} A LAS {self.max_time} UTC — "
                            f"RIESGO DE RADIO HF: {riesgo}"
                        )
                    else:
                        raise Exception("Respuesta sin datos de fulguraciones.")
                else:
                    raise Exception(f"HTTP {respuesta.status_code}")
            except Exception:
                self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON NOAA SWPC. SIN DATOS DE FULGURACIONES."

            # Las fulguraciones se reportan cada pocos minutos: 5 min es un sondeo respetuoso
            time.sleep(300)

    def _descomponer_clase(self, clase):
        try:
            letra = clase[0].upper()
            numero = float(clase[1:])
            if letra not in self.ORDEN_CLASE:
                letra = "A"
            return letra, numero
        except Exception:
            return "A", 0.0

    def _severidad_normalizada(self):
        # 0.0 (calma total) a 1.0 (X9.9, la mayor fulguración registrable)
        base = self.ORDEN_CLASE.get(self.letra, 0) / 4.0
        extra = min(self.numero, 9.9) / 9.9 / 4.0
        return min(1.0, base + extra)

    def update(self, tiempo_actual):
        pass  # La intensidad se deriva directamente de la última clase conocida, sin estado propio

    def draw(self, surface, color_linea, color_fondo):
        tiempo_actual = pygame.time.get_ticks()
        severidad = self._severidad_normalizada()

        # Posición simbólica fija (no hay "posición geográfica real" para el propio Sol
        # en un mapamundi): un sol esquemático asomando por el borde superior.
        cx, cy = self.width // 2, 12

        num_rayos = 8 + int(severidad * 16)
        radio_base = 14 + severidad * 26
        pulso = 1.0 + 0.15 * math.sin(tiempo_actual * 0.003 * (1 + severidad * 3))

        for i in range(num_rayos):
            angulo = (i / num_rayos) * 2 * math.pi
            # Los rayos solo se proyectan hacia abajo/los lados (el sol "asoma" desde arriba)
            if math.sin(angulo) < -0.3:
                continue
            radio = radio_base * pulso
            x_fin = cx + math.cos(angulo) * radio
            y_fin = cy + math.sin(angulo) * radio
            pygame.draw.line(surface, color_linea, (cx, cy), (x_fin, y_fin), 1)

        pygame.draw.circle(surface, color_linea, (cx, cy), int(8 + severidad * 6), 0)
        pygame.draw.circle(surface, color_fondo, (cx, cy), int(8 + severidad * 6), 1)

        fuente = pygame.font.SysFont("consolas", 11, bold=True)
        etiqueta = f"CLASE {self.max_class}"
        texto = fuente.render(etiqueta, True, color_fondo)
        fondo_rect = texto.get_rect(midtop=(cx, cy + int(radio_base) + 6)).inflate(6, 4)
        pygame.draw.rect(surface, color_linea, fondo_rect)
        surface.blit(texto, texto.get_rect(midtop=(cx, cy + int(radio_base) + 8)))

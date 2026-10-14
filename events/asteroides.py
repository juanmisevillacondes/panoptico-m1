from core.base_event import BaseEvent
import pygame
import math
import random
import threading
import requests
import time
import configparser

class AsteroidesEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="28. EL CENTINELA DE ASTEROIDES (OBJETOS CERCANOS A LA TIERRA)")
        self.mensaje = "CONECTANDO CON NASA NEOWS (OBJETOS CERCANOS A LA TIERRA)..."

        self.width = 800
        self.height = 430

        # Panel de radar simbólico: los asteroides NO tienen una posición geográfica
        # real sobre la Tierra (no son satélites, no sobrevuelan un punto fijo), así
        # que en vez de inventar un lat/lon falso, se representan en este panel.
        # El ÁNGULO de cada punto es decorativo (solo para repartirlos visualmente);
        # la DISTANCIA, el TAMAÑO y la PELIGROSIDAD mostrados son reales.
        self.centro_radar = (700, 350)
        self.radio_radar = 65
        self.anillos_ld = [5, 15, 30]  # Distancias Lunares de referencia (1 LD ≈ 384.400 km)

        self.asteroides = []
        self.indice_teletipo = 0
        self.ultimo_cambio_teletipo = 0

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_neows)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def _leer_clave(self):
        # Clave gratuita de api.nasa.gov (opcional). DEMO_KEY funciona de sobra para
        # el ritmo de sondeo de esta capa (cada 4h), pero puedes poner la tuya propia
        # en settings.ini [API] nasa_key para más fiabilidad.
        try:
            config = configparser.ConfigParser()
            config.read("settings.ini", encoding="utf-8")
            clave = config.get("API", "nasa_key", fallback="").strip()
            return clave if clave else "DEMO_KEY"
        except Exception:
            return "DEMO_KEY"

    def obtener_datos_neows(self):
        url = "https://api.nasa.gov/neo/rest/v1/feed/today"

        while self.ejecutando_hilo:
            try:
                respuesta = requests.get(url, params={"api_key": self._leer_clave()}, timeout=15)
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    procesados = []

                    for fecha, lista in datos.get("near_earth_objects", {}).items():
                        for neo in lista:
                            aproximacion = neo.get("close_approach_data", [{}])[0]
                            distancia_ld = float(aproximacion.get("miss_distance", {}).get("lunar", 999))
                            velocidad_kmh = float(aproximacion.get("relative_velocity", {}).get("kilometers_per_hour", 0))
                            diametro_max = neo.get("estimated_diameter", {}).get("meters", {}).get("estimated_diameter_max", 0)

                            procesados.append({
                                "nombre": neo.get("name", "DESCONOCIDO"),
                                "peligroso": neo.get("is_potentially_hazardous_asteroid", False),
                                "distancia_ld": distancia_ld,
                                "velocidad_kmh": velocidad_kmh,
                                "diametro_m": diametro_max,
                                "fecha": aproximacion.get("close_approach_date_full", fecha),
                            })

                    if procesados:
                        procesados.sort(key=lambda a: a["distancia_ld"])
                        self.asteroides = procesados
                        peligrosos = sum(1 for a in procesados if a["peligroso"])
                        self.mensaje = (
                            f"NASA NEOWS: {len(procesados)} OBJETOS CERCANOS HOY "
                            f"({peligrosos} POTENCIALMENTE PELIGROSOS)."
                        )
                    else:
                        self.asteroides = []
                        self.mensaje = "NASA NEOWS: NINGÚN OBJETO CERCANO CATALOGADO PARA HOY."
                else:
                    raise Exception(f"HTTP {respuesta.status_code}")
            except Exception:
                if not self.asteroides:
                    self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON NASA NEOWS. SIN DATOS DE ASTEROIDES."

            # Es un catalogo que se actualiza a diario: 4 sondeos al dia es de sobra
            time.sleep(14400)

    def update(self, tiempo_actual):
        if self.asteroides and tiempo_actual - self.ultimo_cambio_teletipo > random.randint(8000, 15000):
            self.ultimo_cambio_teletipo = tiempo_actual
            self.indice_teletipo = (self.indice_teletipo + 1) % len(self.asteroides)
            a = self.asteroides[self.indice_teletipo]
            alerta = "⚠ POTENCIALMENTE PELIGROSO — " if a["peligroso"] else ""
            self.mensaje = (
                f"{alerta}{a['nombre']} — DISTANCIA {a['distancia_ld']:.1f} LD — "
                f"Ø {a['diametro_m']:.0f}m — VEL {a['velocidad_kmh']:.0f} KM/H — {a['fecha']}"
            )

    def _radio_desde_distancia(self, distancia_ld):
        maximo_ld = self.anillos_ld[-1]
        proporcion = min(distancia_ld / maximo_ld, 1.0)
        return 6 + proporcion * (self.radio_radar - 6)

    def draw(self, surface, color_linea, color_fondo):
        cx, cy = self.centro_radar

        # Anillos de referencia (distancias lunares reales)
        for ld in self.anillos_ld:
            radio = self._radio_desde_distancia(ld)
            pygame.draw.circle(surface, color_linea, (cx, cy), int(radio), 1)

        fuente_mini = pygame.font.SysFont("consolas", 8)
        for ld in self.anillos_ld:
            radio = self._radio_desde_distancia(ld)
            etiqueta = fuente_mini.render(f"{ld}LD", True, color_linea)
            surface.blit(etiqueta, (cx + radio - 10, cy - 9))

        pygame.draw.line(surface, color_linea, (cx - 4, cy), (cx + 4, cy), 1)
        pygame.draw.line(surface, color_linea, (cx, cy - 4), (cx, cy + 4), 1)

        titulo = fuente_mini.render("CENTINELA NEO", True, color_fondo)
        fondo_titulo = titulo.get_rect(midbottom=(cx, cy - self.radio_radar - 4)).inflate(4, 2)
        pygame.draw.rect(surface, color_linea, fondo_titulo)
        surface.blit(titulo, titulo.get_rect(midbottom=(cx, cy - self.radio_radar - 3)))

        # Puntos: el ÁNGULO es decorativo (reparte los puntos visualmente), la
        # DISTANCIA radial y el tamaño/relleno (peligrosidad) son reales.
        for i, a in enumerate(self.asteroides):
            radio = self._radio_desde_distancia(a["distancia_ld"])
            angulo = (hash(a["nombre"]) % 360) * math.pi / 180.0
            px = cx + math.cos(angulo) * radio
            py = cy + math.sin(angulo) * radio

            tamano = 2 + min(a["diametro_m"] / 500.0, 1.0) * 3
            if a["peligroso"]:
                pygame.draw.circle(surface, color_linea, (int(px), int(py)), int(tamano) + 1, 0)
            else:
                pygame.draw.circle(surface, color_linea, (int(px), int(py)), int(tamano), 1)

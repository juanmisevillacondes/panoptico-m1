from core.base_event import BaseEvent
import pygame
import math
import random
import threading
import requests
import time

class HuracanesEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="23. EL OJO DEL HURACÁN (CICLONES TROPICALES)")
        self.mensaje = "CONECTANDO CON GDACS (SEGUIMIENTO DE CICLONES TROPICALES)..."

        self.width = 800
        self.height = 430

        # Respaldo de seguridad: huracanes históricos reales (nombre, pico de
        # viento real en km/h, coordenadas reales de máxima intensidad), usado
        # solo si GDACS no responde.
        self.historico_seguridad = [
            {"nombre": "KATRINA (2005)", "pais": "ESTADOS UNIDOS", "lat": 29.5, "lon": -89.6, "viento_kmh": 280, "alerta": "Red"},
            {"nombre": "HAIYAN (2013)", "pais": "FILIPINAS", "lat": 11.0, "lon": 125.0, "viento_kmh": 315, "alerta": "Red"},
            {"nombre": "IRMA (2017)", "pais": "CARIBE", "lat": 18.3, "lon": -64.8, "viento_kmh": 295, "alerta": "Red"},
            {"nombre": "DORIAN (2019)", "pais": "BAHAMAS", "lat": 26.5, "lon": -77.0, "viento_kmh": 295, "alerta": "Red"},
            {"nombre": "PATRICIA (2015)", "pais": "MÉXICO", "lat": 19.1, "lon": -104.7, "viento_kmh": 345, "alerta": "Red"},
        ]

        # Lista real, rellenada por el hilo secundario con ciclones activos de GDACS
        self.ciclones_reales = []

        self.indice_teletipo = 0
        self.ultimo_cambio_teletipo = 0

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_gdacs)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_gdacs(self):
        # GDACS (Global Disaster Alert and Coordination System, ONU/Comisión
        # Europea): API pública y gratuita, sin necesidad de clave.
        # Tipo de evento "TC" = ciclón tropical / huracán / tifón.
        url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventtypes=TC"

        while self.ejecutando_hilo:
            try:
                respuesta = requests.get(url, timeout=15, headers={"User-Agent": "Panoptico-M1"})
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    ciclones_procesados = []

                    for feature in datos.get("features", []):
                        props = feature.get("properties", {})
                        if props.get("eventtype") != "TC":
                            continue

                        lon, lat = feature.get("geometry", {}).get("coordinates", [None, None])
                        if lat is None or lon is None:
                            continue

                        nombre = (props.get("eventname") or props.get("name", "CICLÓN SIN NOMBRE")).strip()
                        viento = props.get("severitydata", {}).get("severity") or 0

                        ciclones_procesados.append({
                            "nombre": nombre.upper(),
                            "lat": float(lat),
                            "lon": float(lon),
                            "viento_kmh": float(viento),
                            "alerta": props.get("alertlevel", "Green"),
                            "pais": props.get("country", "ZONA OCEÁNICA"),
                        })

                    if ciclones_procesados:
                        self.ciclones_reales = ciclones_procesados
                        self.mensaje = f"GDACS: {len(ciclones_procesados)} CICLONES TROPICALES ACTIVOS A NIVEL GLOBAL."
                    else:
                        self.ciclones_reales = []
                        self.mensaje = "GDACS: SIN CICLONES TROPICALES SIGNIFICATIVOS ACTIVOS AHORA MISMO."
                else:
                    raise Exception(f"HTTP {respuesta.status_code}")
            except Exception:
                if not self.ciclones_reales:
                    self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON GDACS. MOSTRANDO HURACANES HISTÓRICOS."

            # La trayectoria de un ciclón apenas cambia en minutos: refrescar cada 30 min es de sobra
            time.sleep(1800)

    def proyectar_coordenadas(self, lat, lon):
        # Misma calibración que el resto de capas, para encajar sobre mapamundi.jpg
        ESCALA_X, ESCALA_Y = 1.0, 1.20
        centro_y = self.height / 2
        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        base_y = centro_y - (lat * (self.height / 180)) * ESCALA_Y
        OFFSET_X, OFFSET_Y = -25, 10
        return base_x + OFFSET_X, base_y + OFFSET_Y

    def _lista_activa(self):
        return self.ciclones_reales if self.ciclones_reales else self.historico_seguridad

    def update(self, tiempo_actual):
        # El teletipo va rotando entre todos los ciclones activos (todos se
        # dibujan a la vez en el mapa; el texto solo destaca uno cada vez)
        lista = self._lista_activa()
        if lista and tiempo_actual - self.ultimo_cambio_teletipo > random.randint(8000, 15000):
            self.ultimo_cambio_teletipo = tiempo_actual
            self.indice_teletipo = (self.indice_teletipo + 1) % len(lista)
            ciclon = lista[self.indice_teletipo]
            etiqueta = "REAL" if self.ciclones_reales else "HISTÓRICO"
            self.mensaje = (
                f"[{etiqueta}] {ciclon['nombre']} — {ciclon['pais']} — "
                f"VIENTO {ciclon['viento_kmh']:.0f} KM/H — ALERTA {ciclon['alerta'].upper()}"
            )

    def draw(self, surface, color_linea, color_fondo):
        tiempo_actual = pygame.time.get_ticks()

        for ciclon in self._lista_activa():
            cx, cy = self.proyectar_coordenadas(ciclon["lat"], ciclon["lon"])

            # El radio y la velocidad de rotación crecen con la intensidad real del viento
            viento = max(0.0, min(350.0, ciclon["viento_kmh"]))
            radio_max = 10 + (viento / 350.0) * 28
            velocidad_rotacion = 0.0015 + (viento / 350.0) * 0.004

            fase = tiempo_actual * velocidad_rotacion + hash(ciclon["nombre"]) % 1000

            # Brazos espirales (clásico remolino de huracán, estilo vectorial Bauhaus)
            for brazo in range(2):
                offset_brazo = brazo * math.pi
                puntos = []
                pasos = 18
                for i in range(pasos + 1):
                    t = i / pasos
                    r = radio_max * t
                    angulo = fase + offset_brazo + t * 3.2 * math.pi
                    px = cx + math.cos(angulo) * r
                    py = cy + math.sin(angulo) * r
                    puntos.append((px, py))
                if len(puntos) > 1:
                    pygame.draw.lines(surface, color_linea, False, puntos, 1)

            # El ojo del huracán (punto central sólido)
            pygame.draw.circle(surface, color_linea, (int(cx), int(cy)), 2)

            # Etiqueta solo para los más intensos (huracán mayor, >200 km/h), para no saturar el mapa
            if viento > 200:
                fuente = pygame.font.SysFont("arial", 9, bold=True)
                etiqueta = f"{ciclon['nombre']} | {int(viento)} KM/H"
                texto = fuente.render(etiqueta, True, color_fondo)
                rect_texto = texto.get_rect(topleft=(int(cx) + int(radio_max) + 4, int(cy) - 5))
                fondo_rect = rect_texto.inflate(4, 4)
                pygame.draw.rect(surface, color_linea, fondo_rect)
                surface.blit(texto, rect_texto)

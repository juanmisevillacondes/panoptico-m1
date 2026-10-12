from core.base_event import BaseEvent
import pygame
import math
import random
import threading
import requests
import time
from datetime import datetime, timezone

try:
    from sgp4.api import Satrec, jday
    SGP4_DISPONIBLE = True
except ImportError:
    SGP4_DISPONIBLE = False


class RedOrbitalEvent(BaseEvent):
    # Categorías reales de satélites (grupo de CelesTrak -> etiqueta y forma de
    # dibujo). De cada grupo solo tomamos una muestra pequeña para no saturar
    # el mapa: el objetivo es mostrar la diversidad de la red orbital, no
    # trackear miles de satélites a la vez.
    CATEGORIAS = {
        "stations": {"url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
                     "etiqueta": "ESTACIÓN ESPACIAL", "muestra": 2,
                     "preferidos": ["ISS (ZARYA)", "CSS (TIANHE)"]},
        "weather": {"url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
                    "etiqueta": "METEOROLÓGICO", "muestra": 3, "preferidos": []},
        "gps-ops": {"url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle",
                    "etiqueta": "NAVEGACIÓN GPS", "muestra": 3, "preferidos": []},
        "science": {"url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=science&FORMAT=tle",
                    "etiqueta": "CIENTÍFICO", "muestra": 3, "preferidos": ["HST"]},
    }

    def __init__(self):
        super().__init__(name="25. LA RED ORBITAL (SATÉLITES EN TIEMPO REAL)")
        self.mensaje = "CALIBRANDO RED DE SEGUIMIENTO ORBITAL (CELESTRAK)..."

        self.width = 800
        self.height = 430

        # Catálogo real: lista de {"nombre","categoria","tle":(l1,l2)}
        self.catalogo = []

        # Posiciones calculadas: lista de {"nombre","categoria","x","y","estela":[(x,y),...],"alt_km"}
        self.posiciones = []
        self.ultimo_calculo = 0
        self.indice_teletipo = 0
        self.ultimo_cambio_teletipo = 0

        self.ejecutando_hilo = True
        if SGP4_DISPONIBLE:
            self.hilo_datos = threading.Thread(target=self.obtener_catalogo_celestrak)
            self.hilo_datos.daemon = True
            self.hilo_datos.start()
        else:
            self.mensaje = "FALTA LA LIBRERÍA 'sgp4' (pip install sgp4) — CAPA INACTIVA."

    def obtener_catalogo_celestrak(self):
        while self.ejecutando_hilo:
            try:
                catalogo_nuevo = []
                for clave, info in self.CATEGORIAS.items():
                    respuesta = requests.get(info["url"], timeout=15, headers={"User-Agent": "Panoptico-M1"})
                    if respuesta.status_code != 200:
                        continue

                    satelites = self._parsear_tle(respuesta.text)

                    # Preferimos nombres concretos (mayor variedad real, evita p.ej.
                    # mostrar dos módulos de la misma estación como si fueran dos
                    # satélites distintos); si no aparecen, completamos con los primeros.
                    elegidos = {}
                    for nombre_preferido in info["preferidos"]:
                        if nombre_preferido in satelites:
                            elegidos[nombre_preferido] = satelites[nombre_preferido]

                    for nombre, tle in satelites.items():
                        if len(elegidos) >= info["muestra"]:
                            break
                        if nombre not in elegidos:
                            elegidos[nombre] = tle

                    for nombre, (l1, l2) in elegidos.items():
                        catalogo_nuevo.append({
                            "nombre": nombre,
                            "categoria": info["etiqueta"],
                            "tle": (l1, l2),
                        })

                if catalogo_nuevo:
                    self.catalogo = catalogo_nuevo
                    self.mensaje = f"CELESTRAK: {len(catalogo_nuevo)} SATÉLITES EN SEGUIMIENTO ACTIVO."
                else:
                    raise Exception("Catálogo vacío.")

            except Exception:
                if not self.catalogo:
                    self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON CELESTRAK. SIN SEGUIMIENTO ORBITAL."

            # Los elementos orbitales son válidos varios días: refrescar cada 4h es de sobra
            time.sleep(14400)

    def _parsear_tle(self, texto):
        lineas = [l for l in texto.splitlines() if l.strip()]
        catalogo = {}
        for i in range(0, len(lineas) - 2, 3):
            nombre = lineas[i].strip()
            l1, l2 = lineas[i + 1], lineas[i + 2]
            try:
                Satrec.twoline2rv(l1, l2)  # valida que el TLE es parseable
                catalogo[nombre] = (l1, l2)
            except Exception:
                continue
        return catalogo

    # ---------------------------------------------------------------
    # ASTRODINÁMICA: TEME -> ECEF -> latitud/longitud/altitud geodésicas
    # (mismo motor que radiotelescopios.py, aquí sin necesitar un observador)
    # ---------------------------------------------------------------
    def _gmst_rad(self, jd, fr):
        t_ut1 = (jd + fr - 2451545.0) / 36525.0
        gmst_seg = (67310.54841
                    + (876600.0 * 3600 + 8640184.812866) * t_ut1
                    + 0.093104 * t_ut1 ** 2
                    - 6.2e-6 * t_ut1 ** 3)
        gmst_seg %= 86400.0
        return math.radians(gmst_seg / 240.0) % (2 * math.pi)

    def _posicion_geodetica(self, tle, jd, fr):
        linea1, linea2 = tle
        sat = Satrec.twoline2rv(linea1, linea2)
        error, r_teme, _ = sat.sgp4(jd, fr)
        if error != 0:
            return None

        theta = self._gmst_rad(jd, fr)
        x, y, z = r_teme
        x_ecef = x * math.cos(theta) + y * math.sin(theta)
        y_ecef = -x * math.sin(theta) + y * math.cos(theta)
        z_ecef = z

        lon = math.degrees(math.atan2(y_ecef, x_ecef))
        hip = math.hypot(x_ecef, y_ecef)
        lat = math.degrees(math.atan2(z_ecef, hip))
        alt_km = math.sqrt(x_ecef ** 2 + y_ecef ** 2 + z_ecef ** 2) - 6378.137
        return lat, lon, alt_km

    def proyectar_coordenadas(self, lat, lon):
        ESCALA_X, ESCALA_Y = 1.0, 1.20
        centro_y = self.height / 2
        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        base_y = centro_y - (lat * (self.height / 180)) * ESCALA_Y
        OFFSET_X, OFFSET_Y = -25, 10
        return base_x + OFFSET_X, base_y + OFFSET_Y

    def _recalcular_posiciones(self):
        if not self.catalogo or not SGP4_DISPONIBLE:
            self.posiciones = []
            return

        ahora = datetime.now(timezone.utc)
        jd, fr = jday(ahora.year, ahora.month, ahora.day, ahora.hour, ahora.minute, ahora.second)
        # Dos instantes pasados (1 y 2 minutos antes) para dibujar una estela de dirección
        jd_m1, fr_m1 = jday(ahora.year, ahora.month, ahora.day, ahora.hour, ahora.minute, ahora.second - 60)
        jd_m2, fr_m2 = jday(ahora.year, ahora.month, ahora.day, ahora.hour, ahora.minute, ahora.second - 120)

        nuevas_posiciones = []
        for sat in self.catalogo:
            actual = self._posicion_geodetica(sat["tle"], jd, fr)
            if not actual:
                continue
            lat, lon, alt_km = actual

            estela = []
            for jd_e, fr_e in [(jd_m1, fr_m1), (jd_m2, fr_m2)]:
                punto = self._posicion_geodetica(sat["tle"], jd_e, fr_e)
                if punto:
                    estela.append(self.proyectar_coordenadas(punto[0], punto[1]))

            x, y = self.proyectar_coordenadas(lat, lon)
            nuevas_posiciones.append({
                "nombre": sat["nombre"],
                "categoria": sat["categoria"],
                "x": x, "y": y,
                "alt_km": alt_km,
                "estela": estela,
            })

        self.posiciones = nuevas_posiciones

    def update(self, tiempo_actual):
        # Recalcular posiciones orbitales ~1 vez por segundo (de sobra para que
        # se vea fluido a esta escala, sin recargar la CPU de la Raspberry Pi)
        if tiempo_actual - self.ultimo_calculo > 1000:
            self.ultimo_calculo = tiempo_actual
            self._recalcular_posiciones()

        if self.posiciones and tiempo_actual - self.ultimo_cambio_teletipo > random.randint(8000, 15000):
            self.ultimo_cambio_teletipo = tiempo_actual
            self.indice_teletipo = (self.indice_teletipo + 1) % len(self.posiciones)
            sat = self.posiciones[self.indice_teletipo]
            self.mensaje = (
                f"SEGUIMIENTO: {sat['nombre']} ({sat['categoria']}) — "
                f"ALTITUD {sat['alt_km']:.0f} KM"
            )

    def _dibujar_forma(self, surface, color, x, y, categoria):
        if categoria == "ESTACIÓN ESPACIAL":
            pygame.draw.rect(surface, color, (x - 3, y - 3, 6, 6))
        elif categoria == "METEOROLÓGICO":
            pygame.draw.circle(surface, color, (int(x), int(y)), 3, 1)
        elif categoria == "NAVEGACIÓN GPS":
            pygame.draw.polygon(surface, color, [(x, y - 4), (x + 4, y + 3), (x - 4, y + 3)], 1)
        else:  # CIENTÍFICO
            pygame.draw.polygon(surface, color, [(x, y - 4), (x + 4, y), (x, y + 4), (x - 4, y)], 1)

    def draw(self, surface, color_linea, color_fondo):
        fuente = pygame.font.SysFont("consolas", 9)

        for sat in self.posiciones:
            # Estela tenue mostrando la dirección real de desplazamiento reciente
            puntos_estela = [(sat["x"], sat["y"])] + sat["estela"]
            if len(puntos_estela) > 1:
                pygame.draw.lines(surface, color_linea, False, puntos_estela, 1)

            self._dibujar_forma(surface, color_linea, sat["x"], sat["y"], sat["categoria"])

            etiqueta = f"{sat['nombre']} | {int(sat['alt_km'])}km"
            texto = fuente.render(etiqueta, True, color_fondo)
            fondo_rect = texto.get_rect(topleft=(int(sat["x"]) + 7, int(sat["y"]) - 6)).inflate(4, 4)
            pygame.draw.rect(surface, color_linea, fondo_rect)
            surface.blit(texto, (int(sat["x"]) + 9, int(sat["y"]) - 4))

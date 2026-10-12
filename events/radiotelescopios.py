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


class VigiaCosmosEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="21. EL VIGÍA DEL COSMOS (RADIOTELESCOPIOS)")
        self.mensaje = "CALIBRANDO RED DE RADIOASTRONOMÍA GLOBAL..."

        self.width = 800
        self.height = 430

        # Coordenadas reales de los mayores radiotelescopios del mundo (lat, lon)
        self.observatorios = [
            {"nombre": "VLA (NUEVO MÉXICO)", "lat": 34.0784, "lon": -107.6184},
            {"nombre": "ALMA (CHILE)", "lat": -23.0193, "lon": -67.7532},
            {"nombre": "FAST (CHINA)", "lat": 25.6529, "lon": 106.8567},
            {"nombre": "PARKES (AUSTRALIA)", "lat": -32.9984, "lon": 148.2628},
            {"nombre": "EFFELSBERG (ALEMANIA)", "lat": 50.5247, "lon": 6.8828},
        ]

        # Objetivos de respaldo (modo autónomo): se usan si no hay catálogo TLE
        # o si en este instante ningún satélite real es visible desde ningún observatorio
        self.objetivos_cosmicos_ficticios = [
            "PÚLSAR PSR B1919+21",
            "AGUJERO NEGRO M87*",
            "NEBULOSA DE ORIÓN (M42)",
            "GALAXIA DE ANDRÓMEDA (M31)",
            "EXOPLANETA TRAPPIST-1e",
            "CUÁSAR 3C 273",
            "ANOMALÍA RADIO (SEÑAL WOW!)",
        ]

        # Catálogo real de satélites (TLE), rellenado por el hilo secundario
        self.catalogo_tle = {}

        self.observaciones_activas = []
        self.ultimo_cambio = 0

        self.ejecutando_hilo = True
        if SGP4_DISPONIBLE:
            self.hilo_datos = threading.Thread(target=self.obtener_catalogo_celestrak)
            self.hilo_datos.daemon = True
            self.hilo_datos.start()
        else:
            self.mensaje = "FALTA LA LIBRERÍA 'sgp4' (pip install sgp4) — MODO AUTÓNOMO ACTIVO."

        self._asignar_observaciones(random.randint(2, 3))

    # ---------------------------------------------------------------
    # DESCARGA DEL CATÁLOGO ORBITAL (CelesTrak, API pública sin clave)
    # ---------------------------------------------------------------
    def obtener_catalogo_celestrak(self):
        url_visual = "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle"
        url_hubble = "https://celestrak.org/NORAD/elements/gp.php?CATNR=20580&FORMAT=tle"

        while self.ejecutando_hilo:
            try:
                catalogo_nuevo = {}

                respuesta = requests.get(url_visual, timeout=15, headers={"User-Agent": "Panoptico-M1"})
                if respuesta.status_code == 200:
                    catalogo_nuevo.update(self._parsear_tle(respuesta.text))

                try:
                    resp_hst = requests.get(url_hubble, timeout=10, headers={"User-Agent": "Panoptico-M1"})
                    if resp_hst.status_code == 200:
                        catalogo_nuevo.update(self._parsear_tle(resp_hst.text, nombre_forzado="HST (HUBBLE)"))
                except Exception:
                    pass  # El catálogo "visual" ya es suficiente si Hubble falla puntualmente

                if catalogo_nuevo:
                    self.catalogo_tle = catalogo_nuevo
                    self.mensaje = f"CELESTRAK: {len(catalogo_nuevo)} OBJETOS EN SEGUIMIENTO ACTIVO."
                else:
                    raise Exception("Catálogo TLE vacío.")

            except Exception:
                if not self.catalogo_tle:
                    self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON CELESTRAK. SIMULANDO OBJETIVOS CÓSMICOS."

            # Los elementos orbitales (TLE) son válidos varios días: refrescar cada 4h es de sobra
            time.sleep(14400)

    def _parsear_tle(self, texto, nombre_forzado=None):
        lineas = [l for l in texto.splitlines() if l.strip()]
        catalogo = {}
        for i in range(0, len(lineas) - 2, 3):
            nombre = nombre_forzado or lineas[i].strip()
            linea1, linea2 = lineas[i + 1], lineas[i + 2]
            try:
                Satrec.twoline2rv(linea1, linea2)  # valida que el TLE es parseable
                catalogo[nombre] = (linea1, linea2)
            except Exception:
                continue
        return catalogo

    # ---------------------------------------------------------------
    # ASTRODINÁMICA: TEME -> ECEF -> Azimut/Elevación topocéntrica
    # ---------------------------------------------------------------
    def _gmst_rad(self, jd, fr):
        t_ut1 = (jd + fr - 2451545.0) / 36525.0
        gmst_seg = (67310.54841
                    + (876600.0 * 3600 + 8640184.812866) * t_ut1
                    + 0.093104 * t_ut1 ** 2
                    - 6.2e-6 * t_ut1 ** 3)
        gmst_seg %= 86400.0
        return math.radians(gmst_seg / 240.0) % (2 * math.pi)

    def _teme_a_ecef(self, r_teme, jd, fr):
        theta = self._gmst_rad(jd, fr)
        x, y, z = r_teme
        return (
            x * math.cos(theta) + y * math.sin(theta),
            -x * math.sin(theta) + y * math.cos(theta),
            z,
        )

    def _geodetica_a_ecef(self, lat_deg, lon_deg, alt_km=0.0):
        a, f = 6378.137, 1 / 298.257223563
        e2 = f * (2 - f)
        lat, lon = math.radians(lat_deg), math.radians(lon_deg)
        n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        return (
            (n + alt_km) * math.cos(lat) * math.cos(lon),
            (n + alt_km) * math.cos(lat) * math.sin(lon),
            (n * (1 - e2) + alt_km) * math.sin(lat),
        )

    def _azimut_elevacion(self, lat_obs, lon_obs, ecef_obs, ecef_sat):
        dx = ecef_sat[0] - ecef_obs[0]
        dy = ecef_sat[1] - ecef_obs[1]
        dz = ecef_sat[2] - ecef_obs[2]
        lat, lon = math.radians(lat_obs), math.radians(lon_obs)

        este = -math.sin(lon) * dx + math.cos(lon) * dy
        norte = (-math.sin(lat) * math.cos(lon) * dx
                 - math.sin(lat) * math.sin(lon) * dy
                 + math.cos(lat) * dz)
        arriba = (math.cos(lat) * math.cos(lon) * dx
                  + math.cos(lat) * math.sin(lon) * dy
                  + math.sin(lat) * dz)

        rango = math.sqrt(este ** 2 + norte ** 2 + arriba ** 2)
        azimut = math.degrees(math.atan2(este, norte)) % 360
        elevacion = math.degrees(math.asin(arriba / rango)) if rango > 0 else -90
        return azimut, elevacion, rango

    def _calcular_pases_visibles(self):
        """Devuelve [(observatorio, nombre_satelite, az, el, rango), ...] con elevación > 5°."""
        if not self.catalogo_tle:
            return []

        ahora = datetime.now(timezone.utc)
        jd, fr = jday(ahora.year, ahora.month, ahora.day, ahora.hour, ahora.minute, ahora.second)

        visibles = []
        for nombre_sat, (l1, l2) in self.catalogo_tle.items():
            try:
                sat = Satrec.twoline2rv(l1, l2)
                error, r_teme, _ = sat.sgp4(jd, fr)
                if error != 0:
                    continue
                ecef_sat = self._teme_a_ecef(r_teme, jd, fr)
            except Exception:
                continue

            for obs in self.observatorios:
                ecef_obs = self._geodetica_a_ecef(obs["lat"], obs["lon"])
                az, el, rango = self._azimut_elevacion(obs["lat"], obs["lon"], ecef_obs, ecef_sat)
                if el > 5:
                    visibles.append((obs, nombre_sat, az, el, rango))

        return visibles

    def proyectar_coordenadas(self, lat, lon):
        # Misma calibración que el resto de capas, para que los observatorios
        # encajen exactamente sobre mapamundi.jpg igual que todas las demás.
        ESCALA_X, ESCALA_Y = 1.0, 1.20
        centro_y = self.height / 2
        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        base_y = centro_y - (lat * (self.height / 180)) * ESCALA_Y
        OFFSET_X, OFFSET_Y = -25, 10
        return base_x + OFFSET_X, base_y + OFFSET_Y

    # ---------------------------------------------------------------
    # SELECCIÓN DE OBSERVACIONES (reales si hay pase visible, si no, respaldo)
    # ---------------------------------------------------------------
    def _asignar_observaciones(self, cantidad):
        pases_reales = self._calcular_pases_visibles() if SGP4_DISPONIBLE else []

        self.observaciones_activas = []

        if pases_reales:
            seleccionados = random.sample(pases_reales, min(cantidad, len(pases_reales)))
            for obs, nombre_sat, az, el, rango in seleccionados:
                self.observaciones_activas.append({
                    "observatorio": obs,
                    "real": True,
                    "objetivo": nombre_sat,
                    "azimut": az,
                    "elevacion": el,
                    "rango": rango,
                })
            primero = self.observaciones_activas[0]
            self.mensaje = (
                f"{primero['observatorio']['nombre']} SIGUE A {primero['objetivo']} (REAL) — "
                f"AZ {primero['azimut']:.0f}° EL {primero['elevacion']:.0f}° — {primero['rango']:.0f} KM"
            )
        else:
            seleccionados = random.sample(self.observatorios, min(cantidad, len(self.observatorios)))
            for obs in seleccionados:
                self.observaciones_activas.append({
                    "observatorio": obs,
                    "real": False,
                    "objetivo": random.choice(self.objetivos_cosmicos_ficticios),
                    "angulo": random.uniform(0, 2 * math.pi),
                    "velocidad": random.uniform(0.0005, 0.0015) * random.choice([-1, 1]),
                })
            primero = self.observaciones_activas[0]
            sufijo = "" if self.catalogo_tle else " (SIN CATÁLOGO TLE)"
            self.mensaje = (
                f"MODO AUTÓNOMO{sufijo}: {primero['observatorio']['nombre']} "
                f"RASTREANDO {primero['objetivo']} (SIMULADO)."
            )

    def update(self, tiempo_actual):
        # Cambiar los objetivos y observatorios activos cada 15-30 segundos
        if tiempo_actual - self.ultimo_cambio > random.randint(15000, 30000):
            self.ultimo_cambio = tiempo_actual
            self._asignar_observaciones(random.randint(1, 4))

        # Barrido cinemático SOLO para las observaciones ficticias de respaldo
        for obs in self.observaciones_activas:
            if not obs["real"]:
                obs["angulo"] += obs["velocidad"]

    def draw(self, surface, color_linea, color_fondo):
        for obs_activa in self.observaciones_activas:
            base = obs_activa["observatorio"]
            x_base, y_base = self.proyectar_coordenadas(base["lat"], base["lon"])

            if obs_activa["real"]:
                # La longitud del vector decae con la elevación real: casi en el cenit
                # (90°) el vector se acorta al mínimo; cerca del horizonte (0°) se alarga.
                elevacion = max(0.0, min(90.0, obs_activa["elevacion"]))
                radio_vector = 150 * (1 - elevacion / 90.0) + 20
                angulo = math.radians(90 - obs_activa["azimut"])  # azimut (N=0,E=90) -> ángulo de pantalla
                x_fin = x_base + math.cos(angulo) * radio_vector
                y_fin = y_base - math.sin(angulo) * radio_vector
            else:
                radio_vector = 1000
                angulo = obs_activa["angulo"]
                x_fin = x_base + math.cos(angulo) * radio_vector
                y_fin = y_base + math.sin(angulo) * radio_vector

            # 1. El Vector de Observación (Línea recta, tensa y finísima de 1 píxel)
            pygame.draw.line(surface, color_linea, (x_base, y_base), (x_fin, y_fin), 1)

            # 2. La marca táctica de la antena (Una micro-cruz geométrica en el punto de origen)
            pygame.draw.line(surface, color_linea, (x_base - 4, y_base), (x_base + 4, y_base), 1)
            pygame.draw.line(surface, color_linea, (x_base, y_base - 4), (x_base, y_base + 4), 1)

            # Vaciamos el centro de la cruz para máxima precisión visual
            pygame.draw.circle(surface, color_fondo, (int(x_base), int(y_base)), 2)

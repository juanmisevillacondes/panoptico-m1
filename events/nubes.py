from core.base_event import BaseEvent
import pygame
import threading
import requests
import io
import time
from datetime import datetime, timedelta, timezone

class NubesEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="26. EL OJO DEL CIELO (FOTO SATELITAL REAL)")
        self.mensaje = "CONECTANDO CON NASA GIBS (INSTANTÁNEA SATELITAL GLOBAL)..."

        self.width = 800
        self.height = 430

        self.imagen_nubes = None

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_gibs)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def _pedir_capa(self, capa, fecha):
        url = (
            "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
            f"?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS={capa}"
            f"&TIME={fecha}"
            f"&BBOX=-180,-60,180,85&WIDTH={self.width}&HEIGHT={self.height}"
            "&SRS=EPSG:4326&FORMAT=image/png&TRANSPARENT=TRUE"
        )
        respuesta = requests.get(url, timeout=20)
        if respuesta.status_code != 200:
            raise Exception(f"HTTP {respuesta.status_code} pidiendo {capa}")
        return pygame.image.load(io.BytesIO(respuesta.content)).convert_alpha()

    def obtener_datos_gibs(self):
        # Un único satélite polar (Terra o Aqua) deja huecos en su pasada diaria;
        # combinando los dos (horas de cruce distintas) se reduce bastante el hueco.
        # Pedimos el día de AYER (no "hoy") para tener siempre el mosaico completo
        # de las 24h, en vez de una pasada parcial a medio completar.
        while self.ejecutando_hilo:
            try:
                ayer = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

                terra = self._pedir_capa("MODIS_Terra_CorrectedReflectance_TrueColor", ayer)
                aqua = self._pedir_capa("MODIS_Aqua_CorrectedReflectance_TrueColor", ayer)

                combinada = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                combinada.blit(terra, (0, 0))
                combinada.blit(aqua, (0, 0))  # Aqua encima rellena parte de los huecos de Terra
                combinada.set_alpha(235)  # Deja asomar ligeramente el reloj/mapa de fondo

                self.imagen_nubes = combinada
                self.mensaje = (
                    f"NASA GIBS (TERRA+AQUA): INSTANTÁNEA GLOBAL DE NUBES DEL {ayer} "
                    f"(FOTO SATELITAL REAL, ~24-48H DE RETRASO)."
                )

            except Exception:
                if not self.imagen_nubes:
                    self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON NASA GIBS. SIN INSTANTÁNEA DE NUBES."

            # Es un mosaico diario: comprobar cada 3h es de sobra para detectar el cambio de dia
            time.sleep(10800)

    def update(self, tiempo_actual):
        pass  # Instantánea diaria estática: no hay nada que animar fotograma a fotograma

    def draw(self, surface, color_linea, color_fondo):
        if self.imagen_nubes:
            # Mismo desplazamiento de calibración que incendios.py (misma BBOX/tamaño WMS)
            OFFSET_X, OFFSET_Y = -25, -15
            surface.blit(self.imagen_nubes, (OFFSET_X, OFFSET_Y))

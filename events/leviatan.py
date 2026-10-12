from core.base_event import BaseEvent
import pygame
import random
import threading
import requests
import time

class LeviatanEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="05. EL LEVIATÁN DE DATOS")
        self.mensaje = "CONECTANDO CON GBIF (RED GLOBAL DE BIODIVERSIDAD)..."
        self.ultimo_tiempo = 0

        self.width = 800
        self.height = 430

        # Variable persistente: Guarda (x, y) del último ping para que NO desaparezca
        self.ping_activo = None
        # Variable para la animación del anillo de sonar continuo
        self.radio_onda = 0

        # Especies de megafauna marina a consultar, con su nombre común para el teletipo
        self.especies = {
            "Carcharodon carcharias": "TIBURÓN BLANCO",
            "Rhincodon typus": "TIBURÓN BALLENA",
            "Orcinus orca": "ORCA",
            "Balaenoptera musculus": "BALLENA AZUL",
            "Megaptera novaeangliae": "BALLENA JOROBADA",
            "Physeter macrocephalus": "CACHALOTE",
        }

        # Lista de respaldo (modo autónomo), usada solo si GBIF no responde
        self.especies_ficticias = [
            "TIBURÓN BLANCO (HEMBRA) / PESO: 950KG",
            "TIBURÓN TIGRE (MACHO) / PESO: 610KG",
            "ORCA (MACHO - POD C) / PESO: 3200KG",
            "TIBURÓN MAKO / VEL: 45 KM/H",
            "BALLENA AZUL (JUVENIL) / RUMBO SUR",
            "CACHALOTE / INMERSIÓN PROFUNDA DETECTADA",
        ]

        # Avistamientos reales, rellenados por el hilo secundario
        self.avistamientos_reales = []

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_gbif)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_gbif(self):
        # GBIF (Global Biodiversity Information Facility): red mundial de avistamientos
        # y registros reales de fauna (ciencia ciudadana, mareógrafos, campañas científicas...).
        # API pública, gratuita, sin necesidad de clave.
        url = "https://api.gbif.org/v1/occurrence/search"

        while self.ejecutando_hilo:
            try:
                avistamientos = []
                for nombre_cientifico, nombre_comun in self.especies.items():
                    params = {
                        "scientificName": nombre_cientifico,
                        "hasCoordinate": "true",
                        "hasGeospatialIssue": "false",
                        "order": "desc",
                        "sort": "eventDate",
                        "limit": 10,
                    }
                    respuesta = requests.get(url, params=params, timeout=15, headers={"User-Agent": "Panoptico-M1"})
                    if respuesta.status_code == 200:
                        for registro in respuesta.json().get("results", []):
                            lat = registro.get("decimalLatitude")
                            lon = registro.get("decimalLongitude")
                            if lat is None or lon is None:
                                continue
                            avistamientos.append({
                                "nombre_comun": nombre_comun,
                                "lat": float(lat),
                                "lon": float(lon),
                                "pais": registro.get("country", "ALTA MAR"),
                                "fecha": (registro.get("eventDate") or "")[:10],
                            })
                    time.sleep(1)  # cortesía entre consultas por especie

                if avistamientos:
                    self.avistamientos_reales = avistamientos
                    self.mensaje = f"GBIF: {len(avistamientos)} AVISTAMIENTOS REALES DE MEGAFAUNA SINCRONIZADOS."
                else:
                    raise Exception("GBIF no devolvió avistamientos con coordenadas válidas.")

            except Exception:
                if not self.avistamientos_reales:
                    self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON GBIF. SIMULANDO TELEMETRÍA."

            # Los avistamientos no cambian minuto a minuto: refrescar cada 6h es de sobra
            time.sleep(21600)

    def proyectar_coordenadas(self, lat, lon):
        # Misma calibración que el resto de capas, para encajar sobre mapamundi.jpg
        ESCALA_X, ESCALA_Y = 1.0, 1.20
        centro_y = self.height / 2
        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        base_y = centro_y - (lat * (self.height / 180)) * ESCALA_Y
        OFFSET_X, OFFSET_Y = -25, 10
        return base_x + OFFSET_X, base_y + OFFSET_Y

    def update(self, tiempo_actual):
        # 1. Lógica del Sonar Continuo (el anillo crece infinitamente y se reinicia)
        self.radio_onda += 0.4
        if self.radio_onda > 35:
            self.radio_onda = 0

        # 2. Lógica de salto del Ping (cada 8-15 segundos cambiamos de animal)
        if tiempo_actual - self.ultimo_tiempo > random.randint(8000, 15000):
            self.ultimo_tiempo = tiempo_actual
            self.radio_onda = 0  # Reiniciamos la onda para que nazca centrada en el nuevo punto

            if self.avistamientos_reales:
                avistamiento = random.choice(self.avistamientos_reales)
                self.ping_activo = self.proyectar_coordenadas(avistamiento["lat"], avistamiento["lon"])
                self.mensaje = (
                    f"AVISTAMIENTO REAL: {avistamiento['nombre_comun']} — "
                    f"{avistamiento['pais']} — {avistamiento['fecha']} (GBIF)"
                )
            else:
                # Modo autónomo: coordenadas aleatorias simulando los océanos
                x = random.randint(50, 750)
                y = random.randint(100, 380)
                self.ping_activo = (x, y)
                info = random.choice(self.especies_ficticias)
                self.mensaje = f"MODO AUTÓNOMO — ÚLTIMO PING: {info}"

    def draw(self, surface, color_linea, color_fondo):
        # Solo dibujamos si ya hemos detectado el primer ping
        if self.ping_activo:
            px, py = self.ping_activo

            # 1. El marcador ESTÁTICO (una cruz de precisión que se queda fija)
            pygame.draw.line(surface, color_linea, (px - 6, py), (px + 6, py), 1)
            pygame.draw.line(surface, color_linea, (px, py - 6), (px, py + 6), 1)

            # 2. El núcleo del transpondedor (un punto cuadrado fijo en el centro)
            pygame.draw.rect(surface, color_linea, (px - 1, py - 1, 3, 3))

            # 3. La onda de sonar que pulsa continuamente alrededor de la coordenada fija
            pygame.draw.circle(surface, color_linea, (int(px), int(py)), int(self.radio_onda), 1)

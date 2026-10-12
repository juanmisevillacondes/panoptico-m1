from core.base_event import BaseEvent
import pygame
import threading
import requests
import time
import configparser

class VigilanciaEstrategicaEvent(BaseEvent):
    # Prefijos de indicativo (callsign) reales y públicamente documentados de
    # aviación militar/gubernamental/humanitaria. No es información sensible:
    # son convenciones de nomenclatura ADS-B de dominio público.
    CATEGORIAS = {
        "RCH": ("USAF", "TRANSPORTE/REABASTECIMIENTO MILITAR (REACH)"),
        "SAM": ("EEUU", "MISIÓN AÉREA ESPECIAL (TRANSPORTE GUBERNAMENTAL)"),
        "NOAA": ("NOAA", "CAZA-HURACANES / INVESTIGACIÓN ATMOSFÉRICA"),
        "CFC": ("CANADÁ", "FUERZAS ARMADAS CANADIENSES"),
        "ASY": ("AUSTRALIA", "FUERZA AÉREA REAL AUSTRALIANA"),
        "NAVY": ("EEUU", "ARMADA DE LOS ESTADOS UNIDOS"),
        "ARMY": ("EEUU", "EJÉRCITO DE LOS ESTADOS UNIDOS"),
        "SAMU": ("FRANCIA", "EVACUACIÓN MÉDICA DE URGENCIA"),
    }

    def __init__(self):
        super().__init__(name="24. LA VIGILANCIA ESTRATÉGICA (VUELOS MILITARES Y GUBERNAMENTALES)")
        self.vuelos = []
        self.mensaje = "CONECTANDO CON RADARES ATC (OPENSKY NETWORK)..."
        self.fuente_radar = pygame.font.SysFont("consolas", 12)

        self._token = None
        self._token_expira = 0

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_opensky)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def _leer_credenciales(self):
        try:
            config = configparser.ConfigParser()
            config.read("settings.ini", encoding="utf-8")
            client_id = config.get("API", "opensky_client_id", fallback="").strip()
            client_secret = config.get("API", "opensky_client_secret", fallback="").strip()
            return (client_id, client_secret) if client_id and client_secret else (None, None)
        except Exception:
            return None, None

    def _obtener_token(self):
        if self._token and time.time() < self._token_expira:
            return self._token

        client_id, client_secret = self._leer_credenciales()
        if not client_id:
            return None

        try:
            url_auth = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
            respuesta = requests.post(
                url_auth,
                data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
                timeout=10,
            )
            if respuesta.status_code == 200:
                datos = respuesta.json()
                self._token = datos["access_token"]
                self._token_expira = time.time() + datos.get("expires_in", 1800) - 60
                return self._token
        except Exception:
            pass

        return None

    def _identificar_categoria(self, callsign):
        cs = callsign.strip().upper()
        for prefijo, (entidad, descripcion) in self.CATEGORIAS.items():
            if cs.startswith(prefijo):
                return entidad, descripcion
        return None, None

    def obtener_datos_opensky(self):
        url = "https://opensky-network.org/api/states/all"

        while self.ejecutando_hilo:
            try:
                token = self._obtener_token()
                headers = {"Authorization": f"Bearer {token}"} if token else {}

                respuesta = requests.get(url, headers=headers, timeout=10)

                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    vuelos_detectados = []

                    if datos and "states" in datos and datos["states"]:
                        for state in datos["states"]:
                            callsign_crudo = state[1]
                            if not callsign_crudo:
                                continue

                            entidad, descripcion = self._identificar_categoria(callsign_crudo)
                            if not entidad:
                                continue

                            lon, lat = state[5], state[6]
                            altitud = state[7] if state[7] else 0
                            velocidad = state[9] if state[9] else 0

                            if lon is not None and lat is not None:
                                x = (lon + 180) * (800 / 360)
                                y = (90 - lat) * (430 / 180)
                                vuelos_detectados.append({
                                    "x": x, "y": y,
                                    "callsign": callsign_crudo.strip(),
                                    "entidad": entidad,
                                    "descripcion": descripcion,
                                    "altitud": altitud,
                                    "velocidad_kmh": velocidad * 3.6,
                                })

                    self.vuelos = vuelos_detectados

                    if len(self.vuelos) > 0:
                        destacado = self.vuelos[0]
                        self.mensaje = (
                            f"VIGILANCIA ESTRATÉGICA: {len(self.vuelos)} VUELOS DETECTADOS — "
                            f"{destacado['callsign']} ({destacado['entidad']}: {destacado['descripcion']})"
                        )
                    else:
                        prefijo = "AUTENTICADO" if token else "ANÓNIMO"
                        self.mensaje = f"VIGILANCIA ({prefijo}): NINGÚN VUELO MILITAR/GUBERNAMENTAL RECONOCIDO AHORA MISMO."

                elif respuesta.status_code == 429:
                    espera = int(respuesta.headers.get("X-Rate-Limit-Retry-After-Seconds", 60))
                    espera = max(60, min(espera, 1800))
                    self.mensaje = f"OPENSKY: LÍMITE DE PETICIONES ALCANZADO. REINTENTANDO EN {espera}S."
                    time.sleep(espera)
                    continue

                else:
                    self.mensaje = f"ESPERANDO VENTANA DE CONEXIÓN CON OPENSKY NETWORK (HTTP {respuesta.status_code})..."

            except Exception:
                self.mensaje = "INTERFERENCIA EN LA RECEPCIÓN ATC. REINTENTANDO..."

            # 180s: esta capa comparte la cuota diaria de OpenSky con la capa de
            # vector de emergencia (ambas consultan el mismo endpoint /states/all).
            time.sleep(180)

    def update(self, tiempo_actual):
        pass  # Posición y lista se actualizan directamente desde el hilo de red

    def draw(self, surface, color_linea, color_fondo):
        for vuelo in self.vuelos:
            x, y = vuelo["x"], vuelo["y"]

            # Marcador en forma de rombo (distinto del cross de "Vector de Emergencia"):
            # vigilancia discreta, no una alarma.
            puntos = [(x, y - 6), (x + 6, y), (x, y + 6), (x - 6, y)]
            pygame.draw.lines(surface, color_linea, True, puntos, 1)
            pygame.draw.circle(surface, color_linea, (int(x), int(y)), 1)

            etiqueta = f"{vuelo['callsign']} | {vuelo['entidad']} | {int(vuelo['altitud'])}m"
            texto = self.fuente_radar.render(etiqueta, True, color_fondo)
            fondo_rect = texto.get_rect(topleft=(int(x) + 9, int(y) - 7)).inflate(6, 4)
            pygame.draw.rect(surface, color_linea, fondo_rect)
            surface.blit(texto, (int(x) + 12, int(y) - 5))

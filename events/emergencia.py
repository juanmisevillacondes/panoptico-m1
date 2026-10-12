from core.base_event import BaseEvent
import pygame
import threading
import requests
import time
import configparser

class EmergenciaEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="VECTOR DE EMERGENCIA")
        self.vuelos = []
        self.mensaje = "CONECTANDO CON RADARES ATC (OPENSKY NETWORK)..."
        self.fuente_radar = pygame.font.SysFont("consolas", 12)

        self._token = None
        self._token_expira = 0  # epoch seconds

        # Hilo secundario para no bloquear los gráficos
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_opensky)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def _leer_credenciales(self):
        # Cuenta gratuita de OpenSky Network (opcional) para multiplicar el
        # límite de peticiones (la API anónima se satura con facilidad).
        # Regístrate en https://opensky-network.org -> My Account -> API Client
        # y pega el client_id / client_secret en settings.ini -> [API]
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
            return self._token  # token todavía válido, lo reutilizamos

        client_id, client_secret = self._leer_credenciales()
        if not client_id:
            return None

        try:
            url_auth = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
            respuesta = requests.post(
                url_auth,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=10,
            )
            if respuesta.status_code == 200:
                datos = respuesta.json()
                self._token = datos["access_token"]
                # Margen de 60s de seguridad antes de que expire de verdad
                self._token_expira = time.time() + datos.get("expires_in", 1800) - 60
                return self._token
        except Exception:
            pass

        return None

    def obtener_datos_opensky(self):
        url = "https://opensky-network.org/api/states/all"

        while self.ejecutando_hilo:
            try:
                token = self._obtener_token()
                headers = {"Authorization": f"Bearer {token}"} if token else {}

                # OpenSky puede ser lento, le damos 10 segundos de margen
                respuesta = requests.get(url, headers=headers, timeout=10)

                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    vuelos_emergencia = []

                    if datos and "states" in datos and datos["states"]:
                        for state in datos["states"]:
                            squawk = state[14]  # El índice 14 contiene el código del transpondedor

                            # Filtramos por código 7700 (Emergencia General)
                            if squawk == "7700":
                                callsign = state[1].strip() if state[1] else "DESC."
                                lon = state[5]
                                lat = state[6]
                                altitud = state[7] if state[7] else 0

                                # Si tenemos coordenadas válidas, aplicamos las matemáticas de proyección
                                if lon is not None and lat is not None:
                                    x = (lon + 180) * (800 / 360)
                                    y = (90 - lat) * (430 / 180)
                                    vuelos_emergencia.append({
                                        "x": x, "y": y,
                                        "callsign": callsign,
                                        "altitud": altitud,
                                        "animacion": 0  # Variable para el radar pulsante
                                    })

                    self.vuelos = vuelos_emergencia

                    # Actualizamos el teletipo
                    if len(self.vuelos) > 0:
                        nombres = ", ".join([v["callsign"] for v in self.vuelos])
                        self.mensaje = f"ALERTA ATC: {len(self.vuelos)} AERONAVE(S) EN EMERGENCIA (7700) - {nombres}"
                    else:
                        prefijo = "RADAR ATC (AUTENTICADO)" if token else "RADAR ATC"
                        self.mensaje = f"{prefijo}: NO SE DETECTAN AERONAVES EN EMERGENCIA (SQUAWK 7700) ACTUALMENTE."

                elif respuesta.status_code == 429:
                    espera = int(respuesta.headers.get("X-Rate-Limit-Retry-After-Seconds", 60))
                    espera = max(60, min(espera, 1800))  # entre 1 y 30 min, nunca más
                    sugerencia = "" if token else " (regístrate gratis en opensky-network.org para ampliar el límite)"
                    self.mensaje = f"OPENSKY: LÍMITE DE PETICIONES ALCANZADO. REINTENTANDO EN {espera}S{sugerencia}."
                    time.sleep(espera)
                    continue

                else:
                    self.mensaje = f"ESPERANDO VENTANA DE CONEXIÓN CON OPENSKY NETWORK (HTTP {respuesta.status_code})..."

            except Exception:
                self.mensaje = "INTERFERENCIA EN LA RECEPCIÓN ATC. REINTENTANDO..."

            # ATENCIÓN: OpenSky banea temporalmente si haces peticiones muy seguidas.
            # 60 segundos es el tiempo de espera perfecto y respetuoso.
            time.sleep(60)

    def update(self, tiempo_actual):
        # Animamos un anillo expansivo alrededor del avión para llamar la atención
        for vuelo in self.vuelos:
            vuelo["animacion"] += 0.5
            if vuelo["animacion"] > 15:
                vuelo["animacion"] = 0

    def draw(self, surface, color_linea, color_fondo):
        for vuelo in self.vuelos:
            x, y = vuelo["x"], vuelo["y"]

            # Cruz central del avión
            pygame.draw.line(surface, color_linea, (x - 4, y), (x + 4, y), 1)
            pygame.draw.line(surface, color_linea, (x, y - 4), (x, y + 4), 1)

            # Anillo de alerta pulsante
            pygame.draw.circle(surface, color_linea, (int(x), int(y)), int(vuelo["animacion"]), 1)

            # Etiqueta con el número de vuelo y la altitud
            texto_radar = self.fuente_radar.render(f"{vuelo['callsign']} {int(vuelo['altitud'])}m", True, color_fondo)
            fondo_rect = texto_radar.get_rect(topleft=(int(x) + 8, int(y) - 8)).inflate(6, 4)
            pygame.draw.rect(surface, color_linea, fondo_rect)
            surface.blit(texto_radar, (int(x) + 11, int(y) - 6))

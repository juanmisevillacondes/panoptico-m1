from core.base_event import BaseEvent
import pygame
import threading
import requests
import time

class EmergenciaEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="VECTOR DE EMERGENCIA")
        self.vuelos = []
        self.mensaje = "CONECTANDO CON RADARES ATC (OPENSKY NETWORK)..."
        self.fuente_radar = pygame.font.SysFont("consolas", 12)

        # Hilo secundario para no bloquear los gráficos
        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_opensky)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_opensky(self):
        # API pública de OpenSky Network
        url = "https://opensky-network.org/api/states/all"

        while self.ejecutando_hilo:
            try:
                # OpenSky puede ser lento, le damos 10 segundos de margen
                respuesta = requests.get(url, timeout=10)
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    vuelos_emergencia = []
                    
                    if datos and "states" in datos and datos["states"]:
                        for state in datos["states"]:
                            squawk = state[14] # El índice 14 contiene el código del transpondedor
                            
                            # Filtramos por código 7700 (Emergencia General)///poner codigo 1000 para naves comerciales
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
                                        "animacion": 0 # Variable para el radar pulsante
                                    })

                    self.vuelos = vuelos_emergencia
                    
                    # Actualizamos el teletipo
                    if len(self.vuelos) > 0:
                        nombres = ", ".join([v["callsign"] for v in self.vuelos])
                        self.mensaje = f"ALERTA ATC: {len(self.vuelos)} AERONAVE(S) EN EMERGENCIA (7700) - {nombres}"
                    else:
                        self.mensaje = "RADAR ATC: NO SE DETECTAN AERONAVES EN EMERGENCIA (SQUAWK 7700) ACTUALMENTE."
                
                else:
                    self.mensaje = "ESPERANDO VENTANA DE CONEXIÓN CON OPENSKY NETWORK..."
                    
            except Exception as e:
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
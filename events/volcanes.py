from core.base_event import BaseEvent
import pygame
import random
import math
import threading
import requests
import time

class VolcanesEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="08. EL ALIENTO GEOLÓGICO (CENIZA)")
        self.mensaje = "CONECTANDO CON GDACS (CENTRO GLOBAL DE ALERTA DE DESASTRES)..."

        self.width = 800
        self.height = 430

        # Base de datos de seguridad: volcanes activos notables (usada si GDACS no responde)
        self.historico_seguridad = [
            {"nombre": "FAGRADALSFJALL", "lat": 63.89, "lon": -22.27, "region": "ISLANDIA", "alerta": None},
            {"nombre": "ETNA", "lat": 37.75, "lon": 14.99, "region": "ITALIA", "alerta": None},
            {"nombre": "POPOCATÉPETL", "lat": 19.02, "lon": -98.62, "region": "MÉXICO", "alerta": None},
            {"nombre": "SAKURAJIMA", "lat": 31.59, "lon": 130.65, "region": "JAPÓN", "alerta": None},
            {"nombre": "KRAKATOA", "lat": -6.10, "lon": 105.42, "region": "INDONESIA", "alerta": None},
            {"nombre": "VILLARRICA", "lat": -39.42, "lon": -71.93, "region": "CHILE", "alerta": None},
            {"nombre": "MAUNA LOA", "lat": 19.47, "lon": -155.60, "region": "HAWÁI", "alerta": None},
        ]

        # Lista real, rellenada por el hilo secundario con erupciones activas de GDACS
        self.volcanes_reales = []

        self.erupciones_activas = []
        self.ultimo_evento = 0
        self.tiempo_entre_eventos = 0

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_gdacs)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_gdacs(self):
        # GDACS (Global Disaster Alert and Coordination System, ONU/Comisión Europea):
        # API pública y gratuita, sin necesidad de clave. Tipo de evento "VO" = erupción volcánica.
        url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventtypes=VO"

        while self.ejecutando_hilo:
            try:
                respuesta = requests.get(url, timeout=15, headers={"User-Agent": "Panoptico-M1"})
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    volcanes_procesados = []

                    for feature in datos.get("features", []):
                        props = feature.get("properties", {})
                        if props.get("eventtype") != "VO":
                            continue

                        lon, lat = feature.get("geometry", {}).get("coordinates", [None, None])
                        if lat is None or lon is None:
                            continue

                        nombre = (props.get("eventname") or props.get("name", "VOLCÁN DESCONOCIDO")).strip()

                        volcanes_procesados.append({
                            "nombre": nombre.upper(),
                            "lat": float(lat),
                            "lon": float(lon),
                            "region": props.get("country", "REGIÓN DESCONOCIDA"),
                            "alerta": props.get("alertlevel"),
                        })

                    if volcanes_procesados:
                        self.volcanes_reales = volcanes_procesados
                        self.mensaje = f"GDACS: {len(volcanes_procesados)} ERUPCIONES ACTIVAS MONITORIZADAS A NIVEL GLOBAL."
                    else:
                        raise Exception("GDACS no reporta erupciones activas en este momento.")
                else:
                    raise Exception(f"HTTP {respuesta.status_code}")
            except Exception:
                self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON GDACS. USANDO BASE HISTÓRICA DE VOLCANES ACTIVOS."

            # La actividad volcánica no cambia minuto a minuto: refrescar cada 30 min es de sobra
            time.sleep(1800)

    def proyectar_coordenadas(self, lat, lon):
        # --- MATEMÁTICAS CON CALIBRACIÓN DE PROYECCIÓN (heredada de la versión original) ---
        ESCALA_X = 1.0
        ESCALA_Y = 1.0  # Factor para comprimir el mapa y bajar las coordenadas europeas

        centro_y = self.height / 2

        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        desviacion_y = (lat * (self.height / 180)) * ESCALA_Y
        base_y = centro_y - desviacion_y

        # --- TORNILLOS DE AJUSTE FINO MANUAL ---
        OFFSET_X = -25
        OFFSET_Y = 30

        return base_x + OFFSET_X, base_y + OFFSET_Y

    def update(self, tiempo_actual):
        # Disparar un nuevo evento volcánico de forma intermitente, eligiendo entre
        # erupciones REALES activas (GDACS) o el histórico si no hay red.
        if tiempo_actual - self.ultimo_evento > self.tiempo_entre_eventos:
            self.ultimo_evento = tiempo_actual
            self.tiempo_entre_eventos = random.randint(8000, 15000)  # Nueva erupción cada 8-15 seg

            lista_origen = self.volcanes_reales if self.volcanes_reales else self.historico_seguridad
            volcan = random.choice(lista_origen)

            final_x, final_y = self.proyectar_coordenadas(volcan["lat"], volcan["lon"])

            # Añadir a la lista de erupciones [x, y, radio_actual, radio_max, nombre, region]
            radio_maximo = random.randint(60, 150)  # El alcance del VAAC
            self.erupciones_activas.append([final_x, final_y, 0.0, radio_maximo, volcan["nombre"], volcan["region"]])

            # Teletipo clínico
            sufijo_alerta = f" — ALERTA GDACS: {volcan['alerta'].upper()}" if volcan.get("alerta") else ""
            self.mensaje = f"ERUPCIÓN EN {volcan['nombre']} ({volcan['region']}) — NUBE DE CENIZA EN EXPANSIÓN{sufijo_alerta}."

        # Expandir lentamente las nubes de ceniza
        for erupcion in self.erupciones_activas[:]:
            erupcion[2] += 0.2  # Velocidad de expansión lenta y agónica
            if erupcion[2] >= erupcion[3]:
                self.erupciones_activas.remove(erupcion)

    def draw(self, surface, color_linea, color_fondo):
        tiempo_actual = pygame.time.get_ticks()

        for erupcion in self.erupciones_activas:
            ex, ey = erupcion[0], erupcion[1]
            radio = erupcion[2]

            # 1. Dibujar la nube de ceniza (Granulado / Halftone matemático)
            for r in range(4, int(radio), 6):
                circunferencia = 2 * math.pi * r
                num_puntos = int(circunferencia / 6)

                if num_puntos > 0:
                    for i in range(num_puntos):
                        angulo = (i / num_puntos) * 2 * math.pi + (tiempo_actual * 0.0002) + (r * 0.1)
                        px = ex + math.cos(angulo) * r
                        py = ey + math.sin(angulo) * r

                        pygame.draw.rect(surface, color_linea, (int(px), int(py), 1, 1))

            # 2. Dibujar el epicentro (Punto absoluto)
            pygame.draw.rect(surface, color_linea, (int(ex) - 2, int(ey) - 2, 5, 5))

            # 3. Tipografía clínica
            if radio > 10:
                fuente = pygame.font.SysFont("arial", 10, bold=True)
                etiqueta = f"{erupcion[4]} | {int(radio * 10)} KM"
                texto = fuente.render(etiqueta, True, color_fondo)

                rect_texto = texto.get_rect(topleft=(int(ex) + 8, int(ey) - 5))
                fondo_rect = rect_texto.inflate(4, 4)

                pygame.draw.rect(surface, color_linea, fondo_rect)
                surface.blit(texto, (int(ex) + 10, int(ey) - 3))

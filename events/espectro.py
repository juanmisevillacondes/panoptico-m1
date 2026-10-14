from core.base_event import BaseEvent
import pygame
import random
import math
import threading
import requests
import time

class EspectroLuminicoEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="17. EL ESPECTRO LUMÍNICO (APAGONES)")
        self.mensaje = "CONECTANDO CON IODA (DETECCIÓN DE CORTES DE INTERNET)..."
        self.width = 800
        self.height = 430

        # Red eléctrica global (Píxel X, Píxel Y, Radio de Dispersión, Cantidad de luces, país ISO2)
        # Las grandes capitales (coordenadas hand-placed originales) rara vez sufren
        # cortes reales — se mantienen como textura ambiental de "infraestructura viva".
        self.nodos_urbanos = [
            # NORTEAMÉRICA
            (205, 115, 9, 350, "US"), (195, 125, 7, 200, "US"), (120, 125, 8, 250, "US"),
            (115, 115, 6, 150, "US"), (180, 115, 9, 200, "US"), (160, 140, 8, 150, "US"),
            (195, 150, 6, 120, "US"), (150, 160, 8, 180, "MX"),
            # SUDAMÉRICA
            (270, 255, 8, 250, "BR"), (275, 250, 6, 150, "BR"), (250, 290, 8, 150, "AR"),
            (240, 290, 6, 100, "CL"), (220, 230, 6, 80, "PE"), (215, 205, 6, 100, "CO"),
            # EUROPA
            (365, 90, 6, 250, "GB"), (360, 80, 5, 150, "GB"), (375, 100, 8, 300, "FR"),
            (395, 95, 9, 350, "DE"), (405, 115, 7, 200, "IT"), (365, 120, 6, 180, "ES"),
            (375, 115, 5, 120, "ES"), (450, 80, 10, 200, "RU"),
            # ÁFRICA
            (425, 145, 6, 150, "EG"), (390, 205, 7, 150, "NG"), (425, 285, 7, 120, "ZA"),
            # ASIA
            (675, 120, 7, 350, "JP"), (665, 125, 5, 200, "JP"), (635, 140, 9, 400, "CN"),
            (610, 165, 7, 250, "HK"), (615, 115, 9, 300, "CN"), (525, 165, 9, 350, "IN"),
            (515, 185, 7, 200, "IN"), (590, 185, 7, 180, "TH"), (595, 215, 5, 120, "SG"),
            (485, 160, 5, 100, "AE"),
            # OCEANÍA
            (695, 295, 7, 150, "AU"), (680, 310, 5, 100, "AU"), (740, 315, 5, 80, "NZ"),

            # --- Países que, en la práctica, protagonizan la mayoría de los cortes
            # reales detectados por IODA (zonas de conflicto, apagones gubernamentales,
            # infraestructura frágil). Densidad de luces deliberadamente menor: son
            # ciudades más pequeñas, no megalópolis.
            (398, 120, 5, 40, "TN"),   # Túnez
            (456, 129, 5, 35, "SY"),   # Siria (Damasco)
            (454, 128, 4, 30, "LB"),   # Líbano (Beirut)
            (489, 123, 6, 50, "IR"),   # Irán (Teherán)
            (537, 128, 6, 45, "PK"),   # Pakistán (Islamabad)
            (589, 169, 6, 40, "MM"),   # Myanmar (Naipyidó)
            (447, 180, 5, 35, "SD"),   # Sudán (Jartum)
            (445, 211, 4, 20, "SS"),   # Sudán del Sur (Yuba)
            (461, 199, 5, 30, "ET"),   # Etiopía (Addis Abeba)
            (192, 159, 5, 35, "CU"),   # Cuba (La Habana)
            (226, 195, 5, 30, "VE"),   # Venezuela (Caracas)
            (576, 157, 6, 45, "BD"),   # Bangladés (Daca)
            (565, 146, 4, 25, "NP"),   # Nepal (Katmandú)
            (474, 110, 4, 20, "AM"),   # Armenia (Ereván)
            (473, 181, 4, 20, "YE"),   # Yemen (Saná)
            (404, 131, 4, 20, "LY"),   # Libia (Trípoli)
            (702, 252, 4, 15, "PG"),   # Papúa Nueva Guinea (Port Moresby)
            (654, 250, 3, 10, "TL"),   # Timor Oriental (Dili)
            (422, 103, 3, 15, "XK"),   # Kosovo (Pristina)
            (252, 208, 3, 10, "SR"),   # Surinam (Paramaribo)
            (440, 235, 3, 10, "BI"),   # Burundi (Buyumbura)
            (436, 71, 5, 25, "BY"),    # Bielorrusia (Minsk)
            (378, 207, 3, 10, "TG"),   # Togo (Lomé)
            (528, 115, 3, 10, "TJ"),   # Tayikistán (Dusambé)
            (243, 187, 3, 10, "BB"),   # Barbados (Bridgetown)
            (674, 204, 3, 10, "PW"),   # Palaos (Ngerulmud)
        ]

        self.red_puntos = []
        self.generar_red()

        self.paises_afectados = {}
        self.apagones_activos = []

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_ioda)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def generar_red(self):
        for cx, cy, dispersion, cantidad, _pais in self.nodos_urbanos:
            for _ in range(cantidad):
                px = random.gauss(cx, dispersion)
                py = random.gauss(cy, dispersion)
                if 0 <= px <= self.width and 0 <= py <= self.height:
                    self.red_puntos.append([px, py, random.random() * math.pi * 2])

    def obtener_datos_ioda(self):
        # IODA (Internet Outage Detection and Analysis, Georgia Tech): API pública
        # y gratuita, sin necesidad de clave. Detecta caídas reales de conectividad
        # a Internet por país (no apagones eléctricos en sí, sino su síntoma más
        # visible desde fuera: el país deja de responder en la red).
        url = "https://api.ioda.inetintel.cc.gatech.edu/v2/outages/summary"

        while self.ejecutando_hilo:
            try:
                ahora = int(time.time())
                respuesta = requests.get(
                    url,
                    params={
                        "from": ahora - 86400,
                        "until": ahora,
                        "entityType": "country",
                        "ignoreMethods": "*.sarima",
                    },
                    timeout=15, headers={"User-Agent": "Panoptico-M1"},
                )

                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    afectados = {}

                    for item in datos.get("data", []):
                        entidad = item.get("entity", {})
                        codigo = entidad.get("code")
                        score = item.get("scores", {}).get("overall", 0)
                        if codigo and score and score > 50:
                            afectados[codigo] = {"nombre": entidad.get("name", codigo), "score": score}

                    self.paises_afectados = afectados

                    if afectados:
                        peor = max(afectados.items(), key=lambda kv: kv[1]["score"])
                        self.mensaje = (
                            f"IODA: {len(afectados)} PAÍSES CON ANOMALÍAS DE CONECTIVIDAD — "
                            f"MÁXIMA: {peor[1]['nombre'].upper()} (PUNTUACIÓN {peor[1]['score']:.0f})"
                        )
                    else:
                        self.mensaje = "IODA: SIN ANOMALÍAS DE CONECTIVIDAD SIGNIFICATIVAS EN LAS ÚLTIMAS 24H."
                else:
                    raise Exception(f"HTTP {respuesta.status_code}")

            except Exception:
                if not self.paises_afectados:
                    self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON IODA. SIN DATOS DE CONECTIVIDAD."

            # Las puntuaciones de IODA se agregan por horas: 15 min de sondeo es de sobra
            time.sleep(900)

    def update(self, tiempo_actual):
        # Recalculamos en cada fotograma qué nodos coinciden con un país con
        # anomalía real ahora mismo (nada de temporizadores ni apagones inventados)
        nodos_afectados = []
        for cx, cy, disp, _cant, pais in self.nodos_urbanos:
            info = self.paises_afectados.get(pais)
            if info:
                radio = min(80, 20 + info["score"] / 2000.0)
                nodos_afectados.append({
                    "x": cx, "y": cy, "radio": radio,
                    "nombre": info["nombre"], "score": info["score"],
                })
        self.apagones_activos = nodos_afectados

    def draw(self, surface, color_linea, color_fondo):
        tiempo_sec = pygame.time.get_ticks() / 1000.0

        for punto in self.red_puntos:
            px, py, offset = punto
            en_apagon = False

            for apagon in self.apagones_activos:
                dist_cuadrada = (px - apagon["x"]) ** 2 + (py - apagon["y"]) ** 2
                if dist_cuadrada < apagon["radio"] ** 2:
                    en_apagon = True
                    break

            if not en_apagon:
                frecuencia = math.sin(tiempo_sec * 6.0 + offset)
                if frecuencia > -0.3:
                    pygame.draw.rect(surface, color_linea, (int(px), int(py), 1, 1))

        fuente = pygame.font.SysFont("consolas", 9)
        for apagon in self.apagones_activos:
            etiqueta = fuente.render(f"{apagon['nombre'].upper()} | {apagon['score']:.0f}", True, color_fondo)
            fondo_rect = etiqueta.get_rect(midtop=(int(apagon["x"]), int(apagon["y"]) + int(apagon["radio"]) + 2)).inflate(4, 4)
            pygame.draw.rect(surface, color_linea, fondo_rect)
            surface.blit(etiqueta, fondo_rect.inflate(-4, -4))

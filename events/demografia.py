from core.base_event import BaseEvent
import pygame
import random
import threading
import requests
import time

class LatidoDemograficoEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="15. EL LATIDO DEMOGRÁFICO")
        self.mensaje = "CONECTANDO CON EL BANCO MUNDIAL (TASAS DEMOGRÁFICAS GLOBALES)..."

        self.width = 800
        self.height = 430

        # Contadores desde que se activa el módulo
        self.total_nacimientos = 0
        self.total_defunciones = 0

        # Temporizadores para el flujo de eventos
        self.ultimo_nacimiento = 0
        self.ultima_defuncion = 0

        # Tasas de referencia (modo autónomo): ~140M nacimientos/año y ~61M
        # defunciones/año según consenso demográfico ONU, usadas solo hasta que
        # el Banco Mundial responda o si no hay red.
        self.ritmo_nacimiento_base = 232  # ms entre nacimientos (~4.3/s)
        self.ritmo_defuncion_base = 500   # ms entre defunciones (~2.0/s)

        self.ritmo_nacimiento = self.ritmo_nacimiento_base
        self.ritmo_defuncion = self.ritmo_defuncion_base

        # Breve etiqueta de estado de la fuente, combinada cada frame con el balance
        # de sesión (si no, el aviso del hilo de red quedaría tapado en <1 frame)
        self.estado_fuente = "CONECTANDO..."

        self.simbolos_activos = []

        # Nodos demográficos principales (Latitud, Longitud, Peso Poblacional)
        self.nodos_poblacion = [
            (20.0, 77.0, 18),   # India
            (35.0, 104.0, 18),  # China
            (9.0, 8.0, 4),      # Nigeria
            (-0.5, 113.0, 4),   # Indonesia
            (37.0, -95.0, 4),   # EE.UU.
            (30.0, 70.0, 3),    # Pakistán
            (-14.0, -51.0, 3),  # Brasil
            (23.0, 90.0, 2),    # Bangladesh
            (61.0, 105.0, 2),   # Rusia
            (23.0, -102.0, 2),  # México
            (36.0, 138.0, 1),   # Japón
            (9.0, 40.0, 2),     # Etiopía
            (26.0, 30.0, 1),    # Egipto
            (-4.0, 21.0, 2),    # RD Congo
            (48.0, 10.0, 4),    # Europa Central
            (4.0, -72.0, 1),    # Colombia
            (14.0, 121.0, 1),   # Filipinas
        ]

        # Expandimos la lista basándonos en los pesos para hacer una selección probabilística rápida
        self.ruleta_demografica = []
        for lat, lon, peso in self.nodos_poblacion:
            self.ruleta_demografica.extend([(lat, lon)] * peso)

        # Tipografía estricta para los símbolos matemáticos
        self.fuente_simbolo = pygame.font.SysFont("courier", 20, bold=True)

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_bancomundial)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_bancomundial(self):
        # API pública y gratuita del Banco Mundial (sin clave). No existe ningún feed
        # en vivo de "nacimiento/defunción individual" en el mundo (no puede existir),
        # pero SÍ existen las tasas reales anuales con las que el mundo mide esto.
        # Usamos esas tasas reales para fijar el RITMO estadístico de la animación.
        base_url = "https://api.worldbank.org/v2/country/WLD/indicator/{}?format=json&per_page=1&mrnev=1"

        while self.ejecutando_hilo:
            try:
                r_natalidad = requests.get(base_url.format("SP.DYN.CBRT.IN"), timeout=15)
                r_mortalidad = requests.get(base_url.format("SP.DYN.CDRT.IN"), timeout=15)
                r_poblacion = requests.get(base_url.format("SP.POP.TOTL"), timeout=15)

                natalidad_1000 = r_natalidad.json()[1][0]["value"]
                mortalidad_1000 = r_mortalidad.json()[1][0]["value"]
                poblacion = r_poblacion.json()[1][0]["value"]
                anio = r_poblacion.json()[1][0]["date"]

                if not (natalidad_1000 and mortalidad_1000 and poblacion):
                    raise Exception("El Banco Mundial devolvió valores vacíos.")

                segundos_por_anio = 365.25 * 86400
                nacimientos_por_seg = (natalidad_1000 * poblacion) / 1000 / segundos_por_anio
                defunciones_por_seg = (mortalidad_1000 * poblacion) / 1000 / segundos_por_anio

                self.ritmo_nacimiento_base = max(20, int(1000 / nacimientos_por_seg))
                self.ritmo_defuncion_base = max(20, int(1000 / defunciones_por_seg))

                self.estado_fuente = (
                    f"TASAS REALES BM {anio}: NAT {nacimientos_por_seg:.2f}/s "
                    f"MORT {defunciones_por_seg:.2f}/s"
                )

            except Exception:
                self.estado_fuente = "MODO AUTÓNOMO (SIN ENLACE BM, TASAS DE REFERENCIA ONU)"

            # Son estadísticas anuales: refrescar una vez al día es más que suficiente
            time.sleep(86400)

    def proyectar_coordenadas(self, lat, lon):
        ESCALA_X = 1.0
        ESCALA_Y = 1.20
        centro_y = self.height / 2

        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        desviacion_y = (lat * (self.height / 180)) * ESCALA_Y
        base_y = centro_y - desviacion_y

        OFFSET_X = -25
        OFFSET_Y = 10

        return base_x + OFFSET_X, base_y + OFFSET_Y

    def generar_evento(self, tipo, tiempo_actual):
        # Elegir un país basándonos en la densidad de población real
        lat_base, lon_base = random.choice(self.ruleta_demografica)

        # Añadir dispersión (ruido) para que no caigan todos en el mismo píxel exacto
        lat = lat_base + random.uniform(-4.0, 4.0)
        lon = lon_base + random.uniform(-4.0, 4.0)

        px, py = self.proyectar_coordenadas(lat, lon)

        # Guardamos el símbolo con opacidad máxima (255)
        self.simbolos_activos.append({
            "tipo": tipo,
            "x": px,
            "y": py,
            "alpha": 255,
            "nacimiento": tiempo_actual
        })

    def update(self, tiempo_actual):
        # 1. Comprobar si toca nacer a alguien (ritmo centrado en la tasa REAL del Banco Mundial)
        if tiempo_actual - self.ultimo_nacimiento > self.ritmo_nacimiento:
            self.ritmo_nacimiento = random.randint(
                int(self.ritmo_nacimiento_base * 0.65), int(self.ritmo_nacimiento_base * 1.5)
            )
            self.ultimo_nacimiento = tiempo_actual
            self.total_nacimientos += 1
            self.generar_evento("+", tiempo_actual)

        # 2. Comprobar si toca morir a alguien (ritmo centrado en la tasa REAL del Banco Mundial)
        if tiempo_actual - self.ultima_defuncion > self.ritmo_defuncion:
            self.ritmo_defuncion = random.randint(
                int(self.ritmo_defuncion_base * 0.8), int(self.ritmo_defuncion_base * 1.3)
            )
            self.ultima_defuncion = tiempo_actual
            self.total_defunciones += 1
            self.generar_evento("-", tiempo_actual)

        # Actualizar el teletipo con el estado de la fuente + el balance neto de sesión
        balance_neto = self.total_nacimientos - self.total_defunciones
        self.mensaje = (
            f"[{self.estado_fuente}] BALANCE SESIÓN: [+] {self.total_nacimientos}  "
            f"[-] {self.total_defunciones}  |  NETO: +{balance_neto}"
        )

        # 3. Decaimiento de la opacidad (Fade-out)
        for simbolo in self.simbolos_activos[:]:
            edad = tiempo_actual - simbolo["nacimiento"]
            # Los símbolos duran 1.5 segundos (1500 ms) en pantalla
            if edad > 1500:
                self.simbolos_activos.remove(simbolo)
            else:
                # Calculamos el desvanecimiento progresivo
                simbolo["alpha"] = max(0, 255 - int((edad / 1500.0) * 255))

    def draw(self, surface, color_linea, color_fondo):
        # Al no dibujar nada extra (ni círculos ni cuadrados), respetamos la estética minimalista total.
        for simbolo in self.simbolos_activos:
            texto = self.fuente_simbolo.render(simbolo["tipo"], True, color_linea)

            # Aplicar la transparencia calculada para el efecto de desvanecimiento
            texto.set_alpha(simbolo["alpha"])

            # Centrar el texto en las coordenadas exactas
            rect_texto = texto.get_rect(center=(int(simbolo["x"]), int(simbolo["y"])))

            surface.blit(texto, rect_texto)

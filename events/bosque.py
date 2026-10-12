from core.base_event import BaseEvent
import pygame
import random
import math
import threading
import requests
import time
import configparser
from datetime import datetime, timedelta, timezone

class MemoriaBosqueEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="18. LA MEMORIA DEL BOSQUE (DEFORESTACIÓN)")
        self.mensaje = "SINCRONIZANDO CON SATÉLITES DE OBSERVACIÓN TERRESTRE (GLOBAL FOREST WATCH)..."
        self.width = 800
        self.height = 430

        # Coordenadas centrales de las grandes cuencas (Ajustadas a tu mapa)
        self.centros_cuencas = {
            "AMAZONÍA": (260, 260),
            "CONGO": (420, 240),
            "BORNEO": (600, 235)
        }

        # Cajas geográficas reales (lat_min, lat_max, lon_min, lon_max) de cada cuenca,
        # usadas para consultar alertas reales de deforestación (dataset GLAD-L de GFW)
        self.cajas_geograficas = {
            "AMAZONÍA": (-10.0, 5.0, -70.0, -50.0),
            "CONGO": (-5.0, 5.0, 15.0, 30.0),
            "BORNEO": (-4.0, 7.0, 108.0, 119.0),
        }

        self.bosques = []
        self._generar_cuencas()

        self.ultimo_evento = 0
        self.pixeles_perdidos = 0
        # Velocidad de deforestación por defecto: un píxel destruido cada X milisegundos.
        # Si hay datos reales de GFW, esta velocidad se recalcula en función de las alertas reales.
        self.velocidad_tala = 250
        self.alertas_reales = {}  # {"AMAZONÍA": 1234, "CONGO": 88, ...} — cuenta de los últimos 7 días

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_gfw)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def _leer_api_key(self):
        # Clave gratuita de Global Forest Watch, leída de settings.ini -> [API] gfw_key
        # (cada módulo gestiona su propia conexión de red, sin depender del main)
        try:
            config = configparser.ConfigParser()
            config.read("settings.ini", encoding="utf-8")
            clave = config.get("API", "gfw_key", fallback="").strip()
            return clave if clave else None
        except Exception:
            return None

    def obtener_datos_gfw(self):
        # Dataset GLAD-L (Landsat) de Global Forest Watch: alertas diarias de pérdida de
        # cobertura forestal en el trópico (incluye justo Amazonía, Congo e Indonesia/Borneo).
        # Requiere una API key gratuita: https://www.globalforestwatch.org/my-gfw/
        url = "https://data-api.globalforestwatch.org/dataset/umd_glad_landsat_alerts/latest/query"

        while self.ejecutando_hilo:
            api_key = self._leer_api_key()

            if not api_key:
                self.mensaje = "SIN API KEY DE GLOBAL FOREST WATCH (settings.ini) — EROSIÓN EN MODO ESTADÍSTICO."
                time.sleep(3600)
                continue

            try:
                desde = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
                alertas_temp = {}

                for cuenca, (lat_min, lat_max, lon_min, lon_max) in self.cajas_geograficas.items():
                    sql = (
                        f"SELECT count(*) as total FROM data WHERE "
                        f"latitude BETWEEN {lat_min} AND {lat_max} AND "
                        f"longitude BETWEEN {lon_min} AND {lon_max} AND "
                        f"alert__date >= '{desde}'"
                    )
                    respuesta = requests.get(
                        url,
                        params={"sql": sql},
                        headers={"x-api-key": api_key},
                        timeout=15,
                    )
                    if respuesta.status_code == 200:
                        filas = respuesta.json().get("data", [])
                        alertas_temp[cuenca] = int(filas[0]["total"]) if filas else 0
                    else:
                        raise Exception(f"HTTP {respuesta.status_code} consultando {cuenca}")

                    time.sleep(1)  # cortesía entre consultas, no saturar la API

                self.alertas_reales = alertas_temp
                total_global = sum(alertas_temp.values())

                # Más alertas reales = erosión visual más rápida (acotada para no romper la animación)
                self.velocidad_tala = max(60, 300 - min(total_global, 2400) // 10)

                self.mensaje = f"GLOBAL FOREST WATCH: {total_global} ALERTAS GLAD-L REALES EN LOS ÚLTIMOS 7 DÍAS."

            except Exception:
                self.mensaje = "ERROR DE ENLACE CON GLOBAL FOREST WATCH. EROSIÓN EN MODO ESTADÍSTICO."

            # El dataset GLAD-L se actualiza a diario: 4 consultas/día es más que suficiente
            time.sleep(21600)

    def _generar_cuencas(self):
        # Generar bloques sólidos y geométricos para cada cuenca
        radios = {"AMAZONÍA": 30, "CONGO": 22, "BORNEO": 16}

        for nombre, (cx, cy) in self.centros_cuencas.items():
            radio = radios[nombre]
            # Usamos un paso de 2 para crear bloques densos pero pixelados
            for x in range(cx - radio, cx + radio, 2):
                for y in range(cy - radio, cy + radio, 2):
                    # Forma de círculo geométrico base
                    if (x - cx)**2 + (y - cy)**2 <= radio**2:
                        self.bosques.append({
                            "x": x,
                            "y": y,
                            "cuenca": nombre,
                            # Precalculamos la distancia al centro para el algoritmo de erosión
                            "distancia_centro": math.sqrt((x - cx)**2 + (y - cy)**2)
                        })

    def update(self, tiempo_actual):
        if not self.bosques:
            self.mensaje = "PÉRDIDA TOTAL DE MASA FORESTAL PRIMARIA."
            return

        # Algoritmo de erosión (Astillado desde los bordes)
        if tiempo_actual - self.ultimo_evento > self.velocidad_tala:
            self.ultimo_evento = tiempo_actual

            # Seleccionamos una muestra aleatoria de 10 píxeles que aún existen
            muestra = random.sample(self.bosques, min(10, len(self.bosques)))

            # De esa muestra, sacrificamos el que esté más lejos del centro
            # Esto asegura que la deforestación se coma el bloque desde fuera hacia adentro
            victima = max(muestra, key=lambda p: p["distancia_centro"])

            self.bosques.remove(victima)
            self.pixeles_perdidos += 1

            # Actualizar el teletipo esporádicamente para no saturar la lectura
            if self.pixeles_perdidos % 5 == 0:
                cuenca = victima["cuenca"]
                if self.alertas_reales:
                    alertas_cuenca = self.alertas_reales.get(cuenca, 0)
                    self.mensaje = f"GFW REAL: {alertas_cuenca} ALERTAS GLAD-L (7 DÍAS) EN CUENCA {cuenca}."
                else:
                    # Sin datos reales: estimación estadística heredada
                    hectareas = self.pixeles_perdidos * 450
                    self.mensaje = f"ALERTA SATELITAL: TALA ACTIVA EN CUENCA {cuenca} — {hectareas} HECTÁREAS ERRADICADAS (ESTIMADO)."

    def draw(self, surface, color_linea, color_fondo):
        # Dibujar la masa forestal restante
        for b in self.bosques:
            # Dibujamos rectángulos de 2x2 para darle ese peso industrial y sólido
            pygame.draw.rect(surface, color_linea, (b["x"], b["y"], 2, 2))

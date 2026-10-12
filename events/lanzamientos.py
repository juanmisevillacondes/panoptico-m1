from core.base_event import BaseEvent
import pygame
import threading
import requests
import time
import random
from datetime import datetime, timezone

class GravedadVerticalEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="20. LA GRAVEDAD VERTICAL (LANZAMIENTOS)")
        self.mensaje = "CONECTANDO CON LAUNCH LIBRARY 2 (THE SPACE DEVS)..."

        self.width = 800
        self.height = 430

        # Respaldo de seguridad: las 5 bases de lanzamiento más activas del planeta,
        # con coordenadas reales (lat/lon), usado solo si la API no responde.
        self.historico_seguridad = [
            {"base": "CABO CAÑAVERAL", "agencia": "NASA/SPACEX", "mision": "VENTANA EN ESPERA", "lat": 28.5, "lon": -80.6, "net": None},
            {"base": "STARBASE, TEXAS", "agencia": "SPACEX", "mision": "VENTANA EN ESPERA", "lat": 25.9, "lon": -97.2, "net": None},
            {"base": "PUERTO DE KOUROU", "agencia": "ESA", "mision": "VENTANA EN ESPERA", "lat": 5.2, "lon": -52.8, "net": None},
            {"base": "BASE DE BAIKONUR", "agencia": "ROSCOSMOS", "mision": "VENTANA EN ESPERA", "lat": 45.9, "lon": 63.3, "net": None},
            {"base": "CENTRO DE JIUQUAN", "agencia": "CNSA", "mision": "VENTANA EN ESPERA", "lat": 40.6, "lon": 99.5, "net": None},
        ]

        # Lista real, rellenada por el hilo secundario con los próximos lanzamientos mundiales
        self.datos_lanzamientos = []

        self.lanzamientos_activos = []
        self.ultimo_lanzamiento = 0

        self.ejecutando_hilo = True
        self.hilo_datos = threading.Thread(target=self.obtener_datos_launchlibrary)
        self.hilo_datos.daemon = True
        self.hilo_datos.start()

    def obtener_datos_launchlibrary(self):
        # API pública y gratuita de The Space Devs (sin necesidad de clave)
        url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=15&mode=normal"

        while self.ejecutando_hilo:
            try:
                respuesta = requests.get(url, timeout=10)
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    lanzamientos_procesados = []

                    for res in datos.get("results", []):
                        pad = res.get("pad") or {}
                        lat = pad.get("latitude")
                        lon = pad.get("longitude")
                        if lat is None or lon is None:
                            continue

                        mision = res.get("mission")
                        nombre_mision = mision.get("name") if mision else res.get("name", "MISIÓN SIN NOMBRE")
                        agencia = (res.get("launch_service_provider") or {}).get("name", "AGENCIA DESCONOCIDA")
                        ubicacion = (pad.get("location") or {}).get("name") or pad.get("name", "BASE DESCONOCIDA")

                        lanzamientos_procesados.append({
                            "base": ubicacion,
                            "agencia": agencia,
                            "mision": nombre_mision,
                            "lat": float(lat),
                            "lon": float(lon),
                            "net": res.get("net"),
                        })

                    if lanzamientos_procesados:
                        self.datos_lanzamientos = lanzamientos_procesados
                        self.mensaje = f"LAUNCH LIBRARY 2: {len(lanzamientos_procesados)} LANZAMIENTOS PRÓXIMOS SINCRONIZADOS."
                    else:
                        raise Exception("Respuesta sin lanzamientos con coordenadas válidas.")
                else:
                    raise Exception(f"HTTP {respuesta.status_code}")
            except Exception:
                self.mensaje = "MODO AUTÓNOMO: SIN ENLACE CON LAUNCH LIBRARY 2. USANDO BASES HISTÓRICAS."

            # Los lanzamientos no cambian cada segundo: refrescar cada 20 min
            # respeta de sobra el límite gratuito de la API (15 peticiones/hora).
            time.sleep(1200)

    def proyectar_coordenadas(self, lat, lon):
        # Misma calibración que el resto de capas para que todas encajen sobre mapamundi.jpg
        ESCALA_X = 1.0
        ESCALA_Y = 1.20
        centro_y = self.height / 2

        base_x = ((lon + 180) * (self.width / 360)) * ESCALA_X
        desviacion_y = (lat * (self.height / 180)) * ESCALA_Y
        base_y = centro_y - desviacion_y

        OFFSET_X = -25
        OFFSET_Y = 10

        return base_x + OFFSET_X, base_y + OFFSET_Y

    def calcular_cuenta_atras(self, net_iso):
        if not net_iso:
            return None
        try:
            net_dt = datetime.fromisoformat(net_iso)
            ahora = datetime.now(timezone.utc)
            segundos = int((net_dt - ahora).total_seconds())

            if segundos > 0:
                h, resto = divmod(segundos, 3600)
                m, s = divmod(resto, 60)
                return f"T-{h:02d}:{m:02d}:{s:02d}"
            else:
                return "EN VENTANA DE LANZAMIENTO"
        except Exception:
            return None

    def update(self, tiempo_actual):
        # Disparamos la animación cada 12-25s para mantener el valor contemplativo,
        # eligiendo entre lanzamientos REALES próximos (o el histórico si no hay red).
        if tiempo_actual - self.ultimo_lanzamiento > random.randint(12000, 25000):
            self.ultimo_lanzamiento = tiempo_actual

            lista_origen = self.datos_lanzamientos if self.datos_lanzamientos else self.historico_seguridad
            lanzamiento = random.choice(lista_origen)
            x_base, y_base = self.proyectar_coordenadas(lanzamiento["lat"], lanzamiento["lon"])

            self.lanzamientos_activos.append({
                "x_base": x_base,
                "y_base": y_base,
                "altitud_y": y_base,     # El pilar nace exactamente en la base
                "velocidad_y": 0.2,      # Empuje inicial bajo para simular la masa del cohete
                "mach": 0.0,
                "datos": lanzamiento,
            })

            cuenta_atras = self.calcular_cuenta_atras(lanzamiento.get("net"))
            sufijo = f" — {cuenta_atras}" if cuenta_atras else ""
            self.mensaje = f"DESPEGUE: {lanzamiento['mision']} ({lanzamiento['agencia']}) DESDE {lanzamiento['base']}{sufijo}"

        # Lógica cinética (Aceleración constante escapando de la gravedad)
        lanzamientos_vivos = []
        for cohete in self.lanzamientos_activos:
            cohete["velocidad_y"] += 0.20
            cohete["altitud_y"] -= cohete["velocidad_y"]
            cohete["mach"] += cohete["velocidad_y"] * 0.04

            # El cohete desaparece al abandonar la estratosfera (fuera de pantalla)
            if cohete["altitud_y"] > -50:
                lanzamientos_vivos.append(cohete)

        self.lanzamientos_activos = lanzamientos_vivos

    def draw(self, surface, color_linea, color_fondo):
        fuente_telemetria = pygame.font.SysFont("consolas", 11, bold=True)

        for cohete in self.lanzamientos_activos:
            x_base = cohete["x_base"]
            y_base = cohete["y_base"]
            y_actual = int(cohete["altitud_y"])

            # 1. El Pilar de Empuje (Línea vectorial gruesa y sólida)
            pygame.draw.line(surface, color_linea, (x_base, y_base), (x_base, y_actual), 4)

            # 2. El Vehículo / Flama de escape (Bloque contundente en la punta)
            pygame.draw.rect(surface, color_linea, (x_base - 2, y_actual - 4, 8, 8))

            # 3. Telemetría de Velocidad (Caja invertida para máximo contraste)
            mach_texto = f"MACH {cohete['mach']:.1f}"
            texto_superficie = fuente_telemetria.render(mach_texto, True, color_fondo)

            fondo_rect = texto_superficie.get_rect(topleft=(x_base + 12, y_actual - 4)).inflate(6, 4)
            pygame.draw.rect(surface, color_linea, fondo_rect)
            surface.blit(texto_superficie, (x_base + 15, y_actual - 2))

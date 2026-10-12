
from core.base_event import BaseEvent
import pygame
import random
import urllib.request
import json
import threading

class CaosDigitalEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="08. EL PULSO DEL CAOS DIGITAL")
        
        self.vectores_activos = []
        self.impactos = []
        self.amenazas_reales = []
        self.descarga_completada = False
        
        self.mensaje = "INICIALIZANDO CONEXIÓN SEGURA SANS ISC DSHIELD..."
        self.tipos_ataque = ["SSH BRUTEFORCE", "TELNET SCAN", "MALWARE DROP", "PORT 445 SMB", "WEB EXPLOIT"]

        # Nodos de destino (Los servidores víctimas: grandes infraestructuras globales)
        self.nodos_destino = [
            {"id": "US-WEST", "lat": 37.3, "lon": -121.9},
            {"id": "EU-FRA", "lat": 50.1, "lon": 8.6},
            {"id": "JP-TYO", "lat": 35.6, "lon": 139.6},
            {"id": "BR-SAO", "lat": -23.5, "lon": -46.6},
            {"id": "AU-SYD", "lat": -33.8, "lon": 151.2}
        ]

        # Mapeo aproximado de coordenadas para los códigos de país que devuelve la API de SANS
        self.geo_paises = {
            "CN": (35.8, 104.1), "US": (37.0, -95.7), "RU": (61.5, 105.3),
            "BR": (-14.2, -51.9), "IN": (20.5, 78.9), "NL": (52.1, 5.2),
            "DE": (51.1, 10.4), "VN": (14.0, 108.2), "TW": (23.6, 120.9),
            "KR": (35.9, 127.7), "GB": (55.3, -3.4), "FR": (46.2, 2.2),
            "IR": (32.4, 53.6), "KP": (40.3, 127.5), "UA": (48.3, 31.1),
            "MX": (23.6, -102.5), "RO": (45.9, 24.9), "ZA": (-30.5, 22.9)
        }

        # Iniciamos la descarga en un hilo secundario para NO congelar la interfaz gráfica al arrancar
        threading.Thread(target=self._descargar_datos_reales, daemon=True).start()

    def _descargar_datos_reales(self):
        try:
            # Petición a la API pública de SANS DShield (Top 20 orígenes de ataque recientes)
            url = "https://isc.sans.edu/api/sources/attacks/20?json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Panoptico M1)'})
            
            with urllib.request.urlopen(req, timeout=8) as response:
                datos = json.loads(response.read().decode())
                
                for ip_data in datos:
                    codigo_pais = ip_data.get('country', 'US')
                    # Si tenemos las coordenadas del país, registramos el atacante real
                    if codigo_pais in self.geo_paises:
                        lat, lon = self.geo_paises[codigo_pais]
                        self.amenazas_reales.append({
                            "ip": ip_data.get('ip', '0.0.0.0'),
                            "lat": lat,
                            "lon": lon,
                            "pais": codigo_pais
                        })

            if not self.amenazas_reales:
                raise Exception("JSON vacío o países no mapeados.")
            
            self.descarga_completada = True
            self.mensaje = f"SANS DSHIELD: {len(self.amenazas_reales)} IP's HOSTILES CONFIRMADAS Y CARGADAS."
            
        except Exception as e:
            print(f"Error descargando datos de amenazas: {e}")
            # MODO OFFLINE (Fallback): Si la caja pierde la conexión Wi-Fi, simulamos con datos geopolíticos plausibles
            self.amenazas_reales = [
                {"ip": "193.201.224.X", "lat": 61.5, "lon": 105.3, "pais": "RU"},
                {"ip": "114.114.114.X", "lat": 35.8, "lon": 104.1, "pais": "CN"},
                {"ip": "45.12.X.X", "lat": -14.2, "lon": -51.9, "pais": "BR"}
            ]
            self.descarga_completada = True
            self.mensaje = "MODO OFFLINE (SIN RED): SIMULANDO INFRAESTRUCTURA BASE."

    def update(self, tiempo_actual):
        # No disparamos nada hasta que no tengamos los datos reales descargados
        if not self.descarga_completada:
            return

        # 15% de probabilidad por frame de lanzar un ataque
        if random.random() < 0.15:
            # Tomamos un atacante REAL del registro de las últimas 24h
            origen = random.choice(self.amenazas_reales)
            destino = random.choice(self.nodos_destino)
            
            # Añadimos una variación minúscula (+/- 2 grados) para que los rayos 
            # no salgan exactamente del mismo píxel, dando aspecto de nube de servidores
            lat_origen = origen['lat'] + random.uniform(-2.0, 2.0)
            lon_origen = origen['lon'] + random.uniform(-2.0, 2.0)

            # Proyección Equirrectangular + Calibración fina
            OFFSET_X, OFFSET_Y = 20, -5
            orig_x = (lon_origen + 180) * (800 / 360) + OFFSET_X
            orig_y = (90 - lat_origen) * (430 / 180) + OFFSET_Y
            dest_x = (destino['lon'] + 180) * (800 / 360) + OFFSET_X
            dest_y = (90 - destino['lat']) * (430 / 180) + OFFSET_Y
            
            tipo = random.choice(self.tipos_ataque)
            velocidad = random.uniform(0.015, 0.04)
            longitud_traza = random.uniform(0.08, 0.2)
            
            self.vectores_activos.append({
                "ox": orig_x, "oy": orig_y, 
                "dx": dest_x, "dy": dest_y,
                "progreso": 0.0, "vel": velocidad, "longitud": longitud_traza
            })
            
            # El teletipo escupe direcciones IP hostiles completamente reales
            self.mensaje = f"ATACANTE [{origen['pais']}] {origen['ip']} -> {destino['id']} | {tipo}"

        # Actualizar física de trazadoras
        for vector in self.vectores_activos[:]:
            vector["progreso"] += vector["vel"]
            if vector["progreso"] - vector["longitud"] >= 1.0:
                self.impactos.append({"x": vector["dx"], "y": vector["dy"], "vida": 10})
                self.vectores_activos.remove(vector)

        # Actualizar animaciones de impacto
        for impacto in self.impactos[:]:
            impacto["vida"] -= 1
            if impacto["vida"] <= 0:
                self.impactos.remove(impacto)

    def draw(self, surface, color_linea, color_fondo):
        # 1. Dibujar los Nodos de Destino (Víctimas)
        for nodo in self.nodos_destino:
            OFFSET_X, OFFSET_Y = 20, -5
            nx = (nodo['lon'] + 180) * (800 / 360) + OFFSET_X
            ny = (90 - nodo['lat']) * (430 / 180) + OFFSET_Y
            pygame.draw.line(surface, color_linea, (nx - 2, ny), (nx + 2, ny), 1)
            pygame.draw.line(surface, color_linea, (nx, ny - 2), (nx, ny + 2), 1)

        # 2. Dibujar las Trazadoras (Rayos)
        for vector in self.vectores_activos:
            p_cabeza = min(1.0, vector["progreso"])
            p_cola = max(0.0, vector["progreso"] - vector["longitud"])
            
            if p_cabeza > 0 and p_cola < 1.0:
                hx = vector["ox"] + (vector["dx"] - vector["ox"]) * p_cabeza
                hy = vector["oy"] + (vector["dy"] - vector["oy"]) * p_cabeza
                tx = vector["ox"] + (vector["dx"] - vector["ox"]) * p_cola
                ty = vector["oy"] + (vector["dy"] - vector["oy"]) * p_cola
                
                pygame.draw.line(surface, color_linea, (tx, ty), (hx, hy), 1)
                pygame.draw.rect(surface, color_linea, (hx - 1, hy - 1, 3, 3))

        # 3. Dibujar Impactos
        for imp in self.impactos:
            radio = 12 - imp["vida"]
            pygame.draw.rect(surface, color_linea, (imp["x"] - radio/2, imp["y"] - radio/2, radio, radio), 1)
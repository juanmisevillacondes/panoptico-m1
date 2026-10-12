import importlib
import json

class EventManager:
    def __init__(self, config_path="config.json"):
        self.events = {}
        self.mensaje_actual = "SISTEMA INICIADO..."
        self.load_config_and_plugins(config_path)

    def load_config_and_plugins(self, config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        for event_key, settings in config["events"].items():
            if settings["active"]:
                # Importa dinámicamente desde la carpeta events
                module = importlib.import_module(settings["module"])
                event_class = getattr(module, settings["class_name"])
                self.events[event_key] = event_class()
                self.events[event_key].enabled = False # Todo apagado por defecto

    def activar_modo(self, estado_sistema):
        # 1. Apagamos todas las capas primero
        for ev in self.events.values():
            ev.enabled = False
            
        # 2. Encendemos según lo que hayas elegido con el Encoder
        if estado_sistema == "01. MODO PANÓPTICO GLOBAL":
            for ev in self.events.values():
                ev.enabled = True
            self.mensaje_actual = "PANÓPTICO INICIADO — MONITOREO TOTAL ACTIVO..."
            
        elif estado_sistema == "02. SISMÓGRAFO PLANETARIO":
            if "sismografo" in self.events: self.events["sismografo"].enabled = True
            self.mensaje_actual = "MONITOREO SÍSMICO ACTIVO..."
            
        elif estado_sistema == "03. EL VECTOR DE EMERGENCIA":
            if "emergencia" in self.events: self.events["emergencia"].enabled = True
            self.mensaje_actual = "RADAR ATC ACTIVO — ESPERANDO CÓDIGO 7700..."
            
        elif estado_sistema == "04. COSECHADOR DE TORMENTAS":
            if "tormentas" in self.events: self.events["tormentas"].enabled = True
            self.mensaje_actual = "ESCANEANDO ACTIVIDAD ELÉCTRICA ATMOSFÉRICA..."
            
        elif estado_sistema == "05. VIGÍA ORBITAL (ISS)":
            if "vigia" in self.events: self.events["vigia"].enabled = True
            self.mensaje_actual = "RASTREANDO TELEMETRÍA ESTACIÓN ESPACIAL INTERNACIONAL..."

    def obtener_mensaje_teletipo(self):
        # Si un módulo activo tiene una emergencia (ej. un rayo o un sismo), pisamos el mensaje base
        for ev in self.events.values():
            if ev.enabled and hasattr(ev, 'mensaje') and ev.mensaje != "":
                return ev.mensaje
        return self.mensaje_actual

    def update_all(self, tiempo_actual):
        for event in self.events.values():
            if event.enabled:
                event.update(tiempo_actual)

    def draw_all(self, surface, color_texto, color_fondo):
        for event in self.events.values():
            if event.enabled:
                # Le pasamos los colores del Tema Claro/Oscuro a cada módulo
                event.draw(surface, color_texto, color_fondo)
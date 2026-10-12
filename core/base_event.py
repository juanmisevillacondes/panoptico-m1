from abc import ABC, abstractmethod

class BaseEvent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.enabled = False
        self.mensaje = "" # Mensaje de alerta individual del módulo

    @abstractmethod
    def update(self, tiempo_actual):
        pass

    @abstractmethod
    def draw(self, surface, color_linea, color_fondo):
        pass

import pygame
import sys
import os
import importlib
import pkgutil
import threading
import subprocess
import time
import configparser
import urllib.request
from datetime import datetime
from core.base_event import BaseEvent

# --- 1. CONFIGURACIÓN DEL SISTEMA ---
pygame.init()
ANCHO, ALTO = 1024, 600
pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.FULLSCREEN)
pygame.display.set_caption("Panóptico M1 - Sistema de Carga Dinámica v1.5.13")
reloj_pygame = pygame.time.Clock()
pygame.mouse.set_visible(False)

# Lienzo interno de trabajo: TODOS los módulos de events/ asumen un sistema de
# coordenadas de 800x430 para sus cálculos de proyección lat/lon -> píxel.
# Debe coincidir exactamente con ese tamaño o las capas se desalinean verticalmente.
lienzo_eventos = pygame.Surface((800, 430), pygame.SRCALPHA)

ZONA_TELETIPO_ALTO = 50
ALTO_MAPA_DISPONIBLE = ALTO - ZONA_TELETIPO_ALTO

# Declaramos la variable antes de lanzar el hilo para que el semáforo funcione
ejecutando = True  

# --- HILO: VERIFICADOR HÍBRIDO (AP + INTERNET REAL) ---
estado_red = "DESCONECTADO" # "WIFI", "AP" o "DESCONECTADO"
def hilo_verificar_red():
    global estado_red
    while ejecutando:
        try:
            # 1. Comprobar si estamos emitiendo la red de rescate
            salida = subprocess.getoutput("/usr/bin/nmcli -t -f NAME connection show --active")
            
            if "Panoptico-WiFi" in salida or "wifi-connect" in salida:
                estado_red = "AP"
            else:
                # 2. Si no estamos en AP, exigir conexión real a internet
                try:
                    urllib.request.urlopen("https://www.google.com", timeout=2)
                    estado_red = "WIFI"
                except Exception:
                    estado_red = "DESCONECTADO"
        except Exception:
            estado_red = "DESCONECTADO"
        time.sleep(3)

threading.Thread(target=hilo_verificar_red, daemon=True).start()

# --- 2. CARGAS EXTERNAS ---
# Calculamos el lienzo MÁS GRANDE que cabe en la pantalla disponible (encima del
# teletipo) SIN deformar el mapamundi, respetando su proporción real. El resto
# del espacio se rellena con el color de fondo del tema (efecto "letterbox"),
# en vez de estirar el mapa para forzarlo a llenar toda la pantalla.
try:
    temp_img = pygame.image.load("mapamundi.jpg").convert()
    aspecto_mapa = temp_img.get_width() / temp_img.get_height()
except Exception:
    temp_img = None
    aspecto_mapa = lienzo_eventos.get_width() / lienzo_eventos.get_height()  # 800/430 de respaldo

if ANCHO / ALTO_MAPA_DISPONIBLE > aspecto_mapa:
    LIENZO_ALTO = ALTO_MAPA_DISPONIBLE
    LIENZO_ANCHO = int(LIENZO_ALTO * aspecto_mapa)
else:
    LIENZO_ANCHO = ANCHO
    LIENZO_ALTO = int(LIENZO_ANCHO / aspecto_mapa)

LIENZO_OFFSET_X = (ANCHO - LIENZO_ANCHO) // 2
LIENZO_OFFSET_Y = (ALTO_MAPA_DISPONIBLE - LIENZO_ALTO) // 2

try:
    mapa_img = pygame.transform.smoothscale(temp_img, (LIENZO_ANCHO, LIENZO_ALTO)) if temp_img else None
except Exception:
    mapa_img = None

try:
    with open("leyenda.txt", "r", encoding="utf-8") as f:
        texto_leyenda = [linea.rstrip() for linea in f.readlines()]
except Exception:
    texto_leyenda = ["ERROR: Archivo 'leyenda.txt' no encontrado en el sistema."]

# --- 3. TEMAS Y ESTÉTICA ---
COLOR_MAP = {
    "CLARO": {"FONDO": (255, 255, 255), "LINEA": (0, 0, 0), "AGUA": (180, 180, 180)},
    "OSCURO": {"FONDO": (0, 0, 0), "LINEA": (255, 255, 255), "AGUA": (80, 80, 80)}
}

# --- 4. CARGA DINÁMICA DE MÓDULOS ---
def cargar_modulos_dinamicos(ruta):
    modulos = []
    for finder, name, ispkg in pkgutil.iter_modules([ruta]):
        try:
            mod = importlib.import_module(f"events.{name}")
            for key in dir(mod):
                cls = getattr(mod, key)
                if isinstance(cls, type) and issubclass(cls, BaseEvent) and cls is not BaseEvent:
                    modulos.append(cls())
        except Exception as e:
            pass
    return sorted(modulos, key=lambda x: x.name)

modulos_eventos = cargar_modulos_dinamicos("events")

# --- 5. GESTIÓN DE CONFIGURACIÓN Y PERSISTENCIA ---
config = configparser.ConfigParser()
config.read('settings.ini', encoding='utf-8')

if 'SISTEMA' not in config: config['SISTEMA'] = {}
if 'tema' not in config['SISTEMA']: config['SISTEMA']['tema'] = 'OSCURO'
if 'reloj_alpha' not in config['SISTEMA']: config['SISTEMA']['reloj_alpha'] = '150'
if 'mapa_alpha' not in config['SISTEMA']: config['SISTEMA']['mapa_alpha'] = '255'

tema_actual = config['SISTEMA']['tema']
reloj_alpha = int(config['SISTEMA']['reloj_alpha'])
mapa_alpha = int(config['SISTEMA']['mapa_alpha'])

if 'CAPAS' not in config: config['CAPAS'] = {}
visibilidad_capas = {}
for mod in modulos_eventos:
    visibilidad_capas[mod.name] = config.getboolean('CAPAS', mod.name, fallback=True)

def guardar_configuracion():
    config['SISTEMA']['tema'] = tema_actual
    config['SISTEMA']['reloj_alpha'] = str(reloj_alpha)
    config['SISTEMA']['mapa_alpha'] = str(mapa_alpha)
    # Reconstruimos [CAPAS] desde cero en cada guardado: si no hacemos esto,
    # cualquier capa renombrada o eliminada deja para siempre una clave
    # huérfana en el archivo (así se generaron los duplicados con acentos
    # rotos que se iban acumulando sin borrarse nunca).
    config['CAPAS'] = {}
    for k, v in visibilidad_capas.items():
        config['CAPAS'][k] = str(v)
    with open('settings.ini', 'w', encoding='utf-8') as f: config.write(f)
    
guardar_configuracion()

# --- 6. TIPOGRAFÍAS ---
try:
    fuente_titulo = pygame.font.SysFont("arial", 70, bold=True)
    fuente_autor = pygame.font.SysFont("arial", 30, bold=True)
    fuente_instruccion = pygame.font.SysFont("arial", 26, bold=True)
    fuente_menu = pygame.font.SysFont("arial", 28, bold=True)
    fuente_teletipo = pygame.font.SysFont("consolas", 20)
    fuente_selector = pygame.font.SysFont("arial", 22)
    fuente_reloj_fondo = pygame.font.SysFont("arial", 220, bold=True)
    fuente_leyenda = pygame.font.SysFont("consolas", 18)
except Exception:
    fuente_titulo = fuente_autor = fuente_instruccion = fuente_menu = fuente_teletipo = fuente_selector = fuente_reloj_fondo = fuente_leyenda = pygame.font.Font(None, 30)

# --- 7. ESTADOS DEL SISTEMA ---
estado_sistema = "BOOT_1"
indice_menu, indice_selector, indice_ajustes = 0, 0, 0
evento_actual_individual = None
tiempo_inicio_boot = pygame.time.get_ticks()

scroll_offset_menu, scroll_offset_selector, scroll_offset_leyenda = 0, 0, 0
MENU_VISIBLE_ITEMS = 10  
SELECTOR_VISIBLE_ITEMS = 10 
LEYENDA_VISIBLE_ITEMS = 20
editando_ajuste = False
mensaje_ajustes = ""

# Construcción del Menú
menu_opciones = ["00. MODO PANÓPTICO GLOBAL"]
for i, mod in enumerate(modulos_eventos):
    clean_name = mod.name.split('. ', 1)[1] if '. ' in mod.name else mod.name
    menu_opciones.append(f"{i+1:02d}. {clean_name}")

menu_opciones.append("95. AJUSTES Y RED WI-FI MANUAL")
menu_opciones.append("96. MANUAL DE CAMPO (LEYENDA)")
menu_opciones.append("97. REVISAR ACTUALIZACIONES OTA")
menu_opciones.append("98. ALTERNAR TEMA")
menu_opciones.append("99. MODO REPOSO (SOLO RELOJ)")
menu_opciones.append("100. APAGAR SISTEMA")

# --- 8. FUNCIONES DE SISTEMA ---
mensaje_ota = ""

def ejecutar_actualizacion_ota():
    global estado_sistema, mensaje_ota
    estado_sistema = "ACTUALIZACION"
    mensaje_ota = "CONECTANDO CON EL REPOSITORIO..."

    try:
        # 1. Solo consultamos qué hay en el remoto, sin tocar nada local todavía.
        subprocess.run(
            ["git", "fetch", "origin"],
            check=True, capture_output=True, text=True, timeout=30
        )

        rev_local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True
        ).stdout.strip()
        rev_remoto = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            check=True, capture_output=True, text=True
        ).stdout.strip()

        if rev_local == rev_remoto:
            mensaje_ota = "YA ESTÁS EN LA ÚLTIMA VERSIÓN. NO HAY CAMBIOS QUE APLICAR."
            time.sleep(3)
            estado_sistema = "MENU"
            return

        # 2. Hay una versión nueva: forzamos el estado local a coincidir EXACTAMENTE
        # con lo publicado (nunca un merge, para que el dispositivo sea 100%
        # reproducible). settings.ini y demás estado de usuario viven fuera del
        # control de versiones (ver .gitignore), así que no se pierden ajustes.
        mensaje_ota = "DESCARGANDO E INSTALANDO ACTUALIZACIÓN..."
        subprocess.run(
            ["git", "reset", "--hard", "origin/main"],
            check=True, capture_output=True, text=True, timeout=30
        )

        mensaje_ota = "ACTUALIZACIÓN APLICADA. REINICIANDO SISTEMA..."
        time.sleep(2)
        os.execv(sys.executable, ['python3'] + sys.argv)

    except Exception:
        mensaje_ota = "ERROR DE ACTUALIZACIÓN: SIN RED O REPOSITORIO OTA NO CONFIGURADO."
        time.sleep(4)
        estado_sistema = "MENU"

def apagar_sistema():
    global ejecutando

    pantalla.fill(COLOR_MAP["OSCURO"]["FONDO"])
    texto = fuente_titulo.render("APAGANDO SISTEMA...", True, COLOR_MAP["OSCURO"]["LINEA"])
    aviso = fuente_instruccion.render("NO DESCONECTES LA CORRIENTE TODAVÍA", True, (220, 50, 50))
    pantalla.blit(texto, texto.get_rect(center=(ANCHO // 2, ALTO // 2 - 20)))
    pantalla.blit(aviso, aviso.get_rect(center=(ANCHO // 2, ALTO // 2 + 40)))
    pygame.display.flip()

    # os.system() bloqueaba sin límite si sudo pedía una contraseña que nunca
    # llegaba (sin terminal interactiva), dejando "APAGANDO SISTEMA..." congelado
    # para siempre sin que hubiera forma de saber si era seguro desenchufar.
    # Con timeout, como mucho esperamos 10s y SIEMPRE mostramos un resultado claro.
    try:
        resultado = subprocess.run(
            ["sudo", "shutdown", "-h", "now"],
            timeout=10, capture_output=True, text=True
        )
        orden_enviada = (resultado.returncode == 0)
    except Exception:
        orden_enviada = False

    pantalla.fill(COLOR_MAP["OSCURO"]["FONDO"])
    if orden_enviada:
        t1 = fuente_instruccion.render("ORDEN DE APAGADO ENVIADA CORRECTAMENTE.", True, COLOR_MAP["OSCURO"]["LINEA"])
        t2 = fuente_instruccion.render("ESPERA A QUE EL LED VERDE (ACT) DEJE DE PARPADEAR", True, (220, 50, 50))
        t3 = fuente_instruccion.render("ANTES DE DESCONECTAR LA CORRIENTE.", True, (220, 50, 50))
    else:
        t1 = fuente_instruccion.render("ERROR: NO SE PUDO INICIAR EL APAGADO.", True, (220, 50, 50))
        t2 = fuente_instruccion.render("EL SISTEMA SIGUE ENCENDIDO CON NORMALIDAD.", True, COLOR_MAP["OSCURO"]["AGUA"])
        t3 = fuente_instruccion.render("NO LO DESCONECTES: REINTÉNTALO O APÁGALO DESDE UNA TERMINAL.", True, COLOR_MAP["OSCURO"]["AGUA"])
    pantalla.blit(t1, t1.get_rect(center=(ANCHO // 2, ALTO // 2 - 30)))
    pantalla.blit(t2, t2.get_rect(center=(ANCHO // 2, ALTO // 2 + 10)))
    pantalla.blit(t3, t3.get_rect(center=(ANCHO // 2, ALTO // 2 + 40)))
    pygame.display.flip()
    time.sleep(4)

    if orden_enviada:
        ejecutando = False
        pygame.quit()
        sys.exit()
    else:
        # No se pudo apagar: volvemos al menú en vez de cerrar la app a ciegas
        return

def dibujar_lienzo_base(superficie, tema):
    colores = COLOR_MAP[tema]
    superficie.fill(colores["FONDO"])
    if mapa_img:
        mapa_img.set_alpha(mapa_alpha)
        superficie.blit(mapa_img, (LIENZO_OFFSET_X, LIENZO_OFFSET_Y), special_flags=pygame.BLEND_RGB_SUB if tema == "CLARO" else pygame.BLEND_RGB_ADD)

    texto_reloj = fuente_reloj_fondo.render(datetime.now().strftime("%H:%M"), True, colores["AGUA"])
    texto_reloj.set_alpha(reloj_alpha)
    superficie.blit(texto_reloj, texto_reloj.get_rect(center=(ANCHO//2, ALTO_MAPA_DISPONIBLE//2)))

# --- 9. BUCLE PRINCIPAL ---
while ejecutando:
    tiempo_actual = pygame.time.get_ticks()
    color_fondo, color_linea = COLOR_MAP[tema_actual]["FONDO"], COLOR_MAP[tema_actual]["LINEA"]
    
    if estado_sistema == "BOOT_1" and tiempo_actual - tiempo_inicio_boot > 3000:
        estado_sistema, tiempo_inicio_boot = "BOOT_2", tiempo_actual
    elif estado_sistema == "BOOT_2" and tiempo_actual - tiempo_inicio_boot > 4000:
        estado_sistema = "GLOBAL"

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT: ejecutando = False
            
        if evento.type == pygame.KEYDOWN:
            if estado_sistema == "MENU":
                if evento.key == pygame.K_UP: indice_menu = (indice_menu - 1) % len(menu_opciones)
                elif evento.key == pygame.K_DOWN: indice_menu = (indice_menu + 1) % len(menu_opciones)
                
                if indice_menu < scroll_offset_menu: scroll_offset_menu = indice_menu
                elif indice_menu >= scroll_offset_menu + MENU_VISIBLE_ITEMS: scroll_offset_menu = indice_menu - MENU_VISIBLE_ITEMS + 1

            elif estado_sistema == "GLOBAL_SELECTOR":
                if evento.key == pygame.K_UP: indice_selector = (indice_selector - 1) % len(modulos_eventos)
                elif evento.key == pygame.K_DOWN: indice_selector = (indice_selector + 1) % len(modulos_eventos)
                
                if indice_selector < scroll_offset_selector: scroll_offset_selector = indice_selector
                elif indice_selector >= scroll_offset_selector + SELECTOR_VISIBLE_ITEMS: scroll_offset_selector = indice_selector - SELECTOR_VISIBLE_ITEMS + 1

            elif estado_sistema == "LEYENDA":
                if evento.key == pygame.K_UP and scroll_offset_leyenda > 0: scroll_offset_leyenda -= 1
                elif evento.key == pygame.K_DOWN and scroll_offset_leyenda < len(texto_leyenda) - LEYENDA_VISIBLE_ITEMS: scroll_offset_leyenda += 1

            elif estado_sistema == "AJUSTES":
                if evento.key == pygame.K_UP:
                    if not editando_ajuste: indice_ajustes = (indice_ajustes - 1) % 3
                    else:
                        if indice_ajustes == 1: reloj_alpha = min(255, reloj_alpha + 15)
                        elif indice_ajustes == 2: mapa_alpha = min(255, mapa_alpha + 15)
                elif evento.key == pygame.K_DOWN:
                    if not editando_ajuste: indice_ajustes = (indice_ajustes + 1) % 3
                    else:
                        if indice_ajustes == 1: reloj_alpha = max(0, reloj_alpha - 15)
                        elif indice_ajustes == 2: mapa_alpha = max(0, mapa_alpha - 15)

            if evento.key == pygame.K_SPACE:
                if estado_sistema == "MENU":
                    seleccion = menu_opciones[indice_menu]
                    if seleccion.startswith("00."): estado_sistema = "GLOBAL"
                    elif seleccion.startswith("95."): 
                        estado_sistema = "AJUSTES"
                        indice_ajustes, editando_ajuste = 0, False
                        mensaje_ajustes = ""
                    elif seleccion.startswith("96."): estado_sistema, scroll_offset_leyenda = "LEYENDA", 0
                    elif seleccion.startswith("97."): threading.Thread(target=ejecutar_actualizacion_ota).start()
                    elif seleccion.startswith("98."): 
                        tema_actual = "OSCURO" if tema_actual == "CLARO" else "CLARO"
                        guardar_configuracion()
                    elif seleccion.startswith("99."): estado_sistema = "REPOSO"
                    elif seleccion.startswith("100."): apagar_sistema()
                    else:
                        evento_actual_individual = modulos_eventos[indice_menu - 1]
                        estado_sistema = "INDIVIDUAL"
                
                elif estado_sistema == "GLOBAL":
                    estado_sistema, indice_selector, scroll_offset_selector = "GLOBAL_SELECTOR", 0, 0
                
                elif estado_sistema == "GLOBAL_SELECTOR":
                    capa_key = modulos_eventos[indice_selector].name
                    visibilidad_capas[capa_key] = not visibilidad_capas[capa_key]
                    guardar_configuracion()
                    
                elif estado_sistema == "AJUSTES":
                    if not editando_ajuste:
                        if indice_ajustes == 0:
                            def lanzar_ap():
                                # VOLVEMOS A LA ORDEN DE FUERZA BRUTA PARA EVITAR QUE EL ROUTER PELEE CON EL AP
                                os.system("sudo /usr/bin/nmcli device disconnect wlan0")
                                time.sleep(2)
                                os.system("sudo /bin/systemctl start auto-wifi.service")
                            
                            threading.Thread(target=lanzar_ap).start()
                            mensaje_ajustes = "INICIANDO EMISIÓN AP (PANOPTICO-WIFI). EL ICONO PASARÁ A AZUL."
                        else:
                            editando_ajuste = True
                    else:
                        editando_ajuste = False
                        guardar_configuracion()

            elif evento.key == pygame.K_RETURN:
                if estado_sistema == "GLOBAL_SELECTOR": 
                    estado_sistema = "GLOBAL"
                elif estado_sistema == "AJUSTES" and editando_ajuste:
                    editando_ajuste = False
                    guardar_configuracion()
                elif estado_sistema in ["GLOBAL", "INDIVIDUAL", "REPOSO", "LEYENDA", "AJUSTES"]: 
                    estado_sistema = "MENU"

    if estado_sistema in ["GLOBAL", "GLOBAL_SELECTOR"]:
        for mod in modulos_eventos:
            if visibilidad_capas[mod.name]: mod.update(tiempo_actual)
    elif estado_sistema == "INDIVIDUAL":
        evento_actual_individual.update(tiempo_actual)

    if estado_sistema in ["MENU", "ACTUALIZACION", "BOOT_1", "BOOT_2", "LEYENDA", "AJUSTES"]:
        pantalla.fill(color_fondo)

    if estado_sistema == "BOOT_1":
        t1, t2 = fuente_titulo.render("PANÓPTICO M1", True, color_linea), fuente_autor.render("DeJuanmi", True, COLOR_MAP[tema_actual]["AGUA"])
        pantalla.blit(t1, t1.get_rect(center=(ANCHO//2, ALTO//2 - 20)))
        pantalla.blit(t2, t2.get_rect(center=(ANCHO//2, ALTO//2 + 40)))

    elif estado_sistema == "ACTUALIZACION":
        texto_ota = fuente_menu.render(mensaje_ota, True, color_linea)
        pantalla.blit(texto_ota, texto_ota.get_rect(center=(ANCHO // 2, ALTO // 2)))

    elif estado_sistema == "BOOT_2":
        t1 = fuente_instruccion.render("MANUAL DE OPERACIÓN:", True, color_linea)
        t2 = fuente_instruccion.render("PULSACIÓN LARGA [ENTER] -> MENÚ DE SISTEMA", True, COLOR_MAP[tema_actual]["AGUA"])
        t3 = fuente_instruccion.render("PULSAR [ESPACIO] -> GESTOR DE CAPAS", True, COLOR_MAP[tema_actual]["AGUA"])
        pantalla.blit(t1, t1.get_rect(center=(ANCHO//2, ALTO//2 - 50)))
        pantalla.blit(t2, t2.get_rect(center=(ANCHO//2, ALTO//2 + 10)))
        pantalla.blit(t3, t3.get_rect(center=(ANCHO//2, ALTO//2 + 60)))

    elif estado_sistema == "MENU":
        for i in range(MENU_VISIBLE_ITEMS):
            idx = scroll_offset_menu + i
            if idx < len(menu_opciones):
                y_texto = 50 + (i * 45)
                if idx == indice_menu:
                    pygame.draw.rect(pantalla, color_linea, pygame.Rect(40, y_texto - 5, 800, 40))
                    pantalla.blit(fuente_menu.render(menu_opciones[idx], True, color_fondo), (60, y_texto))
                else:
                    pantalla.blit(fuente_menu.render(menu_opciones[idx], True, color_linea), (60, y_texto))

        if scroll_offset_menu > 0: pygame.draw.polygon(pantalla, color_linea, [(380, 20), (420, 20), (400, 10)])
        if scroll_offset_menu + MENU_VISIBLE_ITEMS < len(menu_opciones): pygame.draw.polygon(pantalla, color_linea, [(380, ALTO - 20), (420, ALTO - 20), (400, ALTO - 10)])

    elif estado_sistema == "LEYENDA":
        pantalla.blit(fuente_menu.render("MANUAL DE CAMPO", True, color_linea), (30, 20))
        pygame.draw.line(pantalla, color_linea, (30, 55), (ANCHO - 30, 55), 1)
        
        for i in range(LEYENDA_VISIBLE_ITEMS):
            idx = scroll_offset_leyenda + i
            if idx < len(texto_leyenda):
                pantalla.blit(fuente_leyenda.render(texto_leyenda[idx], True, color_linea), (30, 70 + (i * 22)))
                
        pygame.draw.line(pantalla, color_linea, (0, ALTO - 50), (ANCHO, ALTO - 50), 1)
        pantalla.blit(fuente_teletipo.render("MANTÉN PULSADO EL ENCODER PARA VOLVER AL MENÚ", True, color_linea), (30, ALTO - 35))
        
        if scroll_offset_leyenda > 0: pygame.draw.polygon(pantalla, color_linea, [(ANCHO - 30, 80), (ANCHO - 10, 80), (ANCHO - 20, 70)])
        if scroll_offset_leyenda + LEYENDA_VISIBLE_ITEMS < len(texto_leyenda): pygame.draw.polygon(pantalla, color_linea, [(ANCHO - 30, ALTO - 70), (ANCHO - 10, ALTO - 70), (ANCHO - 20, ALTO - 60)])

    elif estado_sistema == "AJUSTES":
        pantalla.blit(fuente_menu.render("AJUSTES DE SISTEMA Y RED WI-FI", True, color_linea), (30, 20))
        pygame.draw.line(pantalla, color_linea, (30, 55), (ANCHO - 30, 55), 1)
        
        opciones_ajustes = ["ACTIVAR MODO AP (RED PANOPTICO-WIFI)", "INTENSIDAD RELOJ INTERNO", "OPACIDAD DEL MAPAMUNDI"]
        
        for i, op in enumerate(opciones_ajustes):
            y_texto = 120 + (i * 80)
            
            if i == indice_ajustes:
                pygame.draw.rect(pantalla, color_linea, pygame.Rect(30, y_texto - 10, 964, 60))
                color_texto = color_fondo
                if editando_ajuste and i > 0: op = f"< {op} >" 
            else:
                color_texto = color_linea
                
            pantalla.blit(fuente_menu.render(op, True, color_texto), (50, y_texto + 5))
            
            if i > 0:
                val = reloj_alpha if i == 1 else mapa_alpha
                w_barra = int((val / 255) * 350)
                pygame.draw.rect(pantalla, color_texto, (580, y_texto + 10, w_barra, 20))
                pygame.draw.rect(pantalla, color_texto, (580, y_texto + 10, 350, 20), 2)
                
        if mensaje_ajustes:
            pantalla.blit(fuente_instruccion.render(mensaje_ajustes, True, COLOR_MAP[tema_actual]["AGUA"]), (30, 420))
        
        pygame.draw.line(pantalla, color_linea, (0, ALTO - 50), (ANCHO, ALTO - 50), 1)
        pantalla.blit(fuente_teletipo.render("[ESPACIO] SELECCIONAR/EDITAR   [LARGA] VOLVER", True, color_linea), (30, ALTO - 35))

    elif estado_sistema in ["GLOBAL", "GLOBAL_SELECTOR", "INDIVIDUAL", "REPOSO"]:
        dibujar_lienzo_base(pantalla, tema_actual)
        
        lienzo_eventos.fill((0, 0, 0, 0)) 
        
        if estado_sistema in ["GLOBAL", "GLOBAL_SELECTOR"]:
            for mod in modulos_eventos:
                if visibilidad_capas[mod.name]: mod.draw(lienzo_eventos, color_linea, color_fondo)
        elif estado_sistema == "INDIVIDUAL":
            evento_actual_individual.draw(lienzo_eventos, color_linea, color_fondo)
        
        pantalla.blit(pygame.transform.smoothscale(lienzo_eventos, (LIENZO_ANCHO, LIENZO_ALTO)), (LIENZO_OFFSET_X, LIENZO_OFFSET_Y))
        
        pygame.draw.rect(pantalla, color_fondo, (0, ALTO - 50, ANCHO, 50))
        pygame.draw.line(pantalla, color_linea, (0, ALTO - 50), (ANCHO, ALTO - 50), 1)
        
        if estado_sistema == "REPOSO": teletipo = "MODO REPOSO ACTIVO — SISTEMAS SUSPENDIDOS."
        elif estado_sistema == "INDIVIDUAL": teletipo = getattr(evento_actual_individual, "mensaje", "MONITOREO ACTIVO...")
        else:
            capas_activas = [mod for mod in modulos_eventos if visibilidad_capas[mod.name]]
            if not capas_activas: teletipo = "PANÓPTICO GLOBAL — TODAS LAS CAPAS DESACTIVADAS."
            else:
                mod_vis = capas_activas[(tiempo_actual // 3500) % len(capas_activas)]
                teletipo = f"[{mod_vis.name.split('. ', 1)[1] if '. ' in mod_vis.name else mod_vis.name}] {getattr(mod_vis, 'mensaje', 'MONITOREO ACTIVO')}"
            
        pantalla.blit(fuente_teletipo.render(teletipo, True, color_linea), (30, ALTO - 35))

        if estado_sistema == "GLOBAL_SELECTOR":
            surf_over = pygame.Surface((400, ALTO - 50))
            surf_over.fill(color_fondo)
            pygame.draw.rect(surf_over, color_linea, surf_over.get_rect(), 1)
            
            surf_over.blit(fuente_menu.render("GESTOR DE CAPAS", True, color_linea), (30, 20))
            pygame.draw.line(surf_over, color_linea, (30, 50), (370, 50), 1)

            for i in range(SELECTOR_VISIBLE_ITEMS):
                idx = scroll_offset_selector + i
                if idx < len(modulos_eventos):
                    mod = modulos_eventos[idx]
                    texto_capa = f"{'[X]' if visibilidad_capas[mod.name] else '[ ]'} {mod.name.split('. ', 1)[1] if '. ' in mod.name else mod.name}"
                    y_pos = 60 + (i * 35)
                    if idx == indice_selector:
                        pygame.draw.rect(surf_over, color_linea, pygame.Rect(20, y_pos - 5, 360, 35))
                        surf_over.blit(fuente_selector.render(texto_capa, True, color_fondo), (30, y_pos))
                    else:
                        surf_over.blit(fuente_selector.render(texto_capa, True, color_linea), (30, y_pos))
            
            surf_over.blit(fuente_selector.render("[LARGA] CERRAR  [CORTA] ON/OFF", True, color_linea), (15, ALTO - 80))
            pantalla.blit(surf_over, (ANCHO - 420, 25))

    # --- DIBUJADO DEL ICONO WI-FI TRICOLOR ---
    if estado_sistema not in ["BOOT_1", "BOOT_2"]:
        if estado_red == "WIFI":
            color_wifi = (50, 220, 50) # Verde
        elif estado_red == "AP":
            color_wifi = (50, 150, 255) # Azul
        else:
            color_wifi = (220, 50, 50) # Rojo

        pygame.draw.circle(pantalla, color_wifi, (ANCHO - 30, 30), 8)
        pygame.draw.circle(pantalla, color_linea, (ANCHO - 30, 30), 8, 2)

    pygame.display.flip()
    reloj_pygame.tick(60) 

pygame.quit()
sys.exit()
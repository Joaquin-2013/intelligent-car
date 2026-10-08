"""
Asistente de voz estilo "Siri" (en español)
============================================
  1. Escucha en silencio esperando la palabra de activación.
  2. Cuando la oye, dice "Te escucho" y entra en MODO CONVERSACIÓN:
     escucha orden tras orden SIN que tengas que repetir la palabra.
  3. Ejecuta cada orden y RESPONDE EN VOZ ALTA (texto a voz).
  4. Si pasan 15 segundos sin que hables, vuelve a dormirse solo.

Las órdenes son FLEXIBLES: no hay que decir la frase exacta, basta una
palabra clave. Ejemplos:
    "hora" / "qué hora es" / "dime la hora" ......... dice la hora
    "fecha" / "qué día es" / "qué fecha es hoy" ..... dice la fecha
    "abre youtube" / "ábreme el correo" ............. abre una página
    "busca gatos" / "googlea recetas" ............... busca en Google
    "reproduce despacito" / "pon música de queen" ... reproduce en YouTube
    "pausa" / "reanuda" / "continúa" ................ pausa o sigue la reproducción
    "siguiente" / "otra" / "anterior" ............... salta de canción
    "sube el volumen" / "baja el volumen" ........... cambia el volumen
    "silencio" / "mutea" ............................ silencia el sonido
    "quién es Einstein" / "qué es el sol" ........... responde (con la IA)
    cualquier pregunta o charla ..................... responde la IA con naturalidad
    "hola" / "gracias" / "cómo te llamas" ........... charla básica
    "adiós" / "terminar" / "apágate" ................ cierra el asistente
    "activa el carro" / "modo carro" ................ enciende la cámara y mueve el
                                                        carro según hacia dónde mueves la mano
    "para el carro" / "detén el carro" .............. apaga la cámara del modo carro
    "modo control" / "activa el control" ............ controlas el carro con el TECLADO
                                                        (W adelante, S atrás, A izq, D der)
    "para el control" / "apaga el control" .......... apaga el modo control
    "modo seguimiento" / "sígueme" .................. la cámara te detecta y el carro TE SIGUE
                                                        (te alejas: avanza; te acercas: para;
                                                         te vas a un lado: gira hacia ti)
    "para el seguimiento" / "deja de seguirme" ...... apaga el modo seguimiento

Instalar una sola vez en la terminal:
    pip install SpeechRecognition pyaudio pyttsx3
    pip install edge-tts pygame      (para la voz natural, no robótica)
    pip install pyautogui            (para pausar/saltar y controlar el volumen)
    pip install groq                 (para el cerebro de IA)
    pip install wikipedia            (opcional: respaldo si no usas la IA)
    pip install opencv-python mediapipe   (para el modo carro / modo control)
    pip install pyserial             (para hablar con el ESP32 y prender los LEDs)

    Si pyaudio falla:
      - Windows:  pip install pipwin  &&  pipwin install pyaudio
      - macOS:    brew install portaudio  &&  pip install pyaudio
      - Linux:    sudo apt install portaudio19-dev python3-pyaudio espeak

Cerebro de IA con Groq (para que NO sea tonta):
    Necesitas una clave de Groq (gratis en console.groq.com). Pon tu clave en
    la variable de entorno GROQ_API_KEY. Si no la pones, el asistente igual
    funciona, pero responde solo los comandos fijos.

    IMPORTANTE: NUNCA pongas tu clave directamente en este archivo. Si vas a
    compartir el código (o subirlo a GitHub), usa siempre la variable de
    entorno. Para configurarla:
      - Windows (PowerShell):  setx GROQ_API_KEY "tu_clave_aqui"
      - macOS / Linux:         export GROQ_API_KEY="tu_clave_aqui"

Cómo usarlo:
    python asistente.py
    Se abre una VENTANA de chat (estilo ChatGPT):
    - Tus mensajes salen a la derecha; las respuestas de Siri a la izquierda.
    - Habla diciendo "just give me my money" o pulsa el botón 🎤 (micrófono).
    - También puedes ESCRIBIR en el cuadro de abajo y enviar con ➤ o Enter.
    - Las fuentes (si las hay) salen como etiquetas que puedes abrir con clic.

LEDs y motores del ESP32 (modo carro y modo control):
    Este script le manda una letra por USB al ESP32 (que corre MicroPython,
    main.py). Las letras son las MISMAS que entiende el ESP32:
        'W' arriba (adelante), 'S' abajo (atrás),
        'A' izquierda,         'D' derecha,
        'X' (o cualquier otra) detiene todo.
    Configura el puerto correcto en PUERTO_ESP32 (más abajo).

MODO CONTROL (teclado):
    Al activarlo se abre una ventanita "Modo control". Con ESA ventana en
    primer plano, mientras mantengas presionada W/A/S/D el carro se mueve
    (simulador + ESP32). Al soltar la tecla manda 'X' y el carro se detiene.
"""

import asyncio
import datetime
import locale
import math
import os
import queue
import random
import re
import struct
import tempfile
import threading
import time
import wave
import webbrowser
import urllib.parse
import urllib.request

import tkinter as tk
from tkinter import scrolledtext

import speech_recognition as sr
import pyttsx3

# Voz natural (NO robótica) con voces neuronales de Microsoft. Es opcional:
# si no está instalada, se usa la voz del sistema (pyttsx3) como respaldo.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
try:
    import edge_tts
    import pygame
    pygame.mixer.init()
    HAY_VOZ_NATURAL = True
except Exception:
    HAY_VOZ_NATURAL = False

# Wikipedia es opcional: si no está instalado, el asistente sigue funcionando.
try:
    import wikipedia
    wikipedia.set_lang("es")
    HAY_WIKI = True
except ImportError:
    HAY_WIKI = False

# pyautogui es opcional: sirve para pausar/saltar y subir/bajar volumen.
try:
    import pyautogui
    HAY_TECLAS = True
except Exception:
    HAY_TECLAS = False

# La librería de Groq es opcional: es el "cerebro" inteligente (API estilo OpenAI).
try:
    from groq import Groq
    HAY_LIBRERIA_IA = True
except Exception:
    HAY_LIBRERIA_IA = False

# OpenCV, MediaPipe y NumPy son opcionales: hacen falta para el "modo carro"
# (gestos de mano) y para dibujar el simulador (también en el modo control).
try:
    import cv2
    import mediapipe as mp
    import numpy as np
    HAY_VISION = True
except Exception:
    HAY_VISION = False

# pyserial es opcional: solo hace falta si quieres que se prendan los LEDs
# físicos y se muevan los motores conectados al ESP32.
try:
    import serial
    HAY_LIBRERIA_SERIAL = True
except Exception:
    HAY_LIBRERIA_SERIAL = False

# ----- Puente entre el asistente (hilo de fondo) y la ventana (GUI) -----
cola_gui = queue.Queue()          # mensajes que el asistente manda a la ventana
detener_evento = threading.Event()  # para apagar el hilo del asistente
activar_evento = threading.Event()  # para despertar con un clic en la bolita
lock_voz = threading.Lock()       # evita que dos voces suenen a la vez

# ----- Estado del "modo carro" (detección de gestos de mano) -----
hilo_carro = None
detener_carro_evento = threading.Event()

# ----- Estado del "modo control" (teclado W/A/S/D) -----
hilo_control = None
detener_control_evento = threading.Event()
teclas_control = []          # teclas presionadas ahora; la última es la que manda

# ----- Estado del "modo seguimiento" (el carro te sigue con la cámara) -----
hilo_seguimiento = None
detener_seguimiento_evento = threading.Event()


def _enviar(tipo, dato=""):
    """Manda algo a la ventana de forma segura desde cualquier hilo."""
    cola_gui.put((tipo, dato))

# ----- Configuración -----
NOMBRE = "Siri"
PALABRA_ACTIVACION = "just give me my money"   # lo que dices para despertarlo
# Variantes que sirven para activarlo (el micrófono no siempre capta toda la frase)
DISPARADORES = ("just give me my money", "give me my money", "just give me",
                "my money", "money")

IDIOMA = "es-CO"                   # idioma de los COMANDOS (español)
IDIOMA_ACTIVACION = "en-US"        # idioma de la FRASE de activación (inglés)
VELOCIDAD_VOZ = 185                # palabras por minuto (solo para la voz del sistema)

# Voz natural. Para estilo MrBeast LATINO: voz masculina latina con energía.
#   es-MX-JorgeNeural    (hombre, México — acento "doblaje latino")  <- por defecto
#   es-CO-GonzaloNeural  (hombre, Colombia)
#   es-AR-TomasNeural    (hombre, Argentina)
# Si prefieres que pronuncie BIEN el inglés (pero con acento gringo, no latino):
#   en-US-BrianMultilingualNeural
VOZ_NATURAL = "es-MX-JorgeNeural"

# Velocidad: más alto = más rápido y enérgico. Ej: "+25%", "+45%".
VELOCIDAD_NATURAL = "+32%"

# Tono: más alto = más agudo/joven. Ej: "+8Hz", "+18Hz".
TONO_VOZ = "+12Hz"

# Volumen: más alto = más fuerte (más "hype"). Ej: "+0%", "+20%", "+40%".
VOLUMEN_NATURAL = "+25%"

# Lo que dice al arrancar (el saludo / intro).
SALUDO = ("Hola Joaquín, ¿me necesitas? ¿O quieres money? Pues solo di: "
          "just give me my money, y estaré ahí para ti. ¡Byeee!")

# Audio de intro (opcional). Si pones aquí el nombre de un archivo .mp3 (por
# ejemplo el AUDIO DEL MEME "just give me my money") y lo dejas en la MISMA
# carpeta que este programa, Siri lo reproduce al arrancar en vez de hablar.
# Déjalo en "" para usar la voz normal.
SONIDO_INTRO = "intro.mp3"

# Sensibilidad del micrófono: MENOR = más sensible (capta voz más baja/lejana).
# Si se activa solo o capta ruido, SUBE este número (p. ej. 400-700).
SENSIBILIDAD = 250

# Segundos de silencio en una conversación antes de volver a dormir.
TIEMPO_INACTIVO = 15

# Pausa BASE de fin de frase (corta = reacciona rápido). El asistente se
# adapta: si dices algo corto/conocido responde ya; si es largo, te espera.
PAUSA_FINAL = 0.7

# Ventana extra para frases largas: tras una pausa, espera este tiempo por si
# sigues hablando. Si te corta frases largas, súbelo (p. ej. 1.2).
CONTINUACION = 0.8

# Máximo de segundos que puede durar un trozo de orden.
MAX_FRASE = 15

# ----- Modo carro (gestos de mano) -----
# Qué tanto se tiene que mover la mano (escala 0.0-1.0, no en píxeles) para
# considerar que hubo un gesto. Súbelo si detecta movimientos falsos, bájalo
# si no detecta nada.
UMBRAL_MOVIMIENTO_MANO = 0.06
# Cuántos frames esperar antes de poder detectar otro gesto.
ENFRIAMIENTO_FRAMES_MANO = 8
# Ancho al que se reduce cada frame antes de procesarlo (más pequeño = más
# rápido). 320 es un buen balance entre velocidad y que aún detecte bien.
ANCHO_PROCESAMIENTO_CAMARA = 320
# Cuántos frames SEGUIDOS tiene que ver 2 manos antes de salir del modo carro
# (evita que un falso positivo de un instante te saque sin querer).
FRAMES_CONFIRMAR_DOS_MANOS = 10

# ----- Modo control (teclado) -----
# Cada cuántos segundos se repite la letra al ESP32 mientras mantienes la tecla.
INTERVALO_ENVIO_CONTROL = 0.1
# Cuántos píxeles se mueve el carro del simulador de lado por frame (A / D).
PASO_LATERAL_CONTROL = 6

# ----- Modo seguimiento (el carro te sigue) -----
# La cámara debe ir montada EN EL CARRO mirando hacia adelante.
SEG_INDICE_CAMARA = 0
# Espejar SOLO LA IMAGEN en pantalla (como un selfie): si te mueves a TU derecha,
# te ves a la derecha. No cambia hacia dónde gira el carro.
SEG_ESPEJAR_VISTA = True
# Si al probar, el carro gira al lado CONTRARIO al que debería (por cómo quedó
# la cámara o el cableado de los motores), pon esto en True.
SEG_INVERTIR_GIRO = False
SEG_ANCHO_PROCESAMIENTO = 320
# Distancia: ancho de hombros como fracción del ancho de la imagen.
# 0.25 ≈ 1.5 m con una webcam normal. Se recalibra con la tecla C.
SEG_TAMANO_OBJETIVO = 0.25
SEG_TOLERANCIA_TAMANO = 0.04            # margen antes de decidir "estás lejos"
SEG_TOLERANCIA_TAMANO_ALCANCE = 0.015   # ya casi llegó: deja de avanzar
# Lado: qué tan lejos del centro (0.0-1.0) tienes que estar para que gire.
SEG_TOLERANCIA_CENTRO = 0.12            # empieza a girar
SEG_SUAVIZADO = 0.35                    # más alto = más rápido pero más nervioso
SEG_FRAMES_PERDIDO = 6                  # frames sin verte antes de parar
SEG_INTERVALO_ENVIO = 0.1               # cada cuánto se repite la letra al ESP32
SEG_FACTOR_CARA_A_HOMBROS = 2.6         # ancho de hombros ≈ 2.6 × ancho de cara (respaldo)

# --- Giro por PULSOS (para que NO se quede dando vueltas) ---
# El carro gira un ratito (hasta SEG_GRADOS_MAX_POR_GIRO), se queda quieto un
# momento a que la cámara se estabilice, y luego AVANZA. Después vuelve a mirar.
SEG_FOV_HORIZONTAL = 60.0        # ángulo de visión horizontal de tu cámara (grados)
SEG_GRADOS_MAX_POR_GIRO = 20.0   # cuánto gira como máximo cada vez
SEG_GRADOS_POR_SEGUNDO = 90.0    # qué tan rápido gira el carro REAL (¡CALIBRA ESTO!)
                                 #   si gira DE MÁS -> súbelo; si gira DE MENOS -> bájalo
SEG_GIRO_MIN_S = 0.10            # el giro más corto que vale la pena (segundos)
SEG_PAUSA_TRAS_GIRO = 0.45       # quieto después de girar (segundos)
SEG_AVANCE_S = 0.6               # cuánto avanza cada tramo (segundos)
SEG_MAX_GIROS_SEGUIDOS = 1       # giros seguidos antes de OBLIGAR a avanzar

# ----- Simulador visual del carro (calle + carrito en pantalla) -----
SIM_ANCHO = 460
SIM_ALTO = 640
SIM_ANCHO_CALLE = 300          # ancho del asfalto
SIM_ANCHO_CARRO = 56
SIM_ALTO_CARRO = 98
SIM_PASO_CARRIL = 60           # cuánto se desplaza el carro por cada gesto izq/der
SIM_LIMITE_CARRIL = (SIM_ANCHO_CALLE - SIM_ANCHO_CARRO) // 2 - 4
# Velocidad CONSTANTE del carro (ya no acelera/frena con gestos arriba/abajo).
SIM_VELOCIDAD_CONSTANTE = 10.0

# ----- Tráfico: otros carros en la vía (para poder chocar CONTRA algo) -----
# Cada uno: (carril relativo -1/0/1, distancia inicial hacia adelante, color BGR)
SIM_CARRILES_NPC = (-1, 0, 1)
SIM_DESPLAZAMIENTO_CARRIL_NPC = int(SIM_LIMITE_CARRIL * 0.62)
NPCS_INICIALES = [
    (-1, 260, (60, 60, 220)),   # rojo
    (1, 560, (70, 200, 70)),    # verde
    (0, 900, (210, 210, 40)),   # celeste/amarillo
]
SIM_LARGO_MUNDO_NPC = 1150      # al pasar esta distancia, el carro reaparece más adelante
SIM_PROFUNDIDAD_MAX = 520       # qué tan "lejos" se alcanza a ver (para el efecto de profundidad)
SIM_ESCALA_MIN_LEJOS = 0.4      # qué tan chico se ve un carro cuando está lejos (efecto 3D)
SIM_DISTANCIA_CHOQUE = 60       # qué tan cerca tiene que estar un carro para chocar de verdad
SIM_TOLERANCIA_CARRIL_CHOQUE = SIM_PASO_CARRIL * 0.8
# Cuántos frames de "invulnerabilidad" tiene un NPC recién chocado antes de
# poder volver a chocar (evita que un mismo toque cuente varias veces seguidas).
SIM_ENFRIAMIENTO_CHOQUE_NPC = 20

# Frases que dice Siri según hacia dónde mueves la mano.
FRASES_CARRO = {
    "ARRIBA": "Carro avanzando",
    "ABAJO": "Carro retrocediendo",
    "IZQUIERDA": "Carro moviéndose a la izquierda",
    "DERECHA": "Carro moviéndose a la derecha",
}

# Aquí se guardan los audios de las 4 frases de arriba, YA GENERADOS.
_audios_carro_listos = {}

# Ruta del sonido de "choque" (se genera una sola vez, ver _preparar_sonido_choque).
# Si pones un archivo llamado "choque.mp3" o "choque.wav" en la MISMA carpeta
# que este programa, se usa ESE en vez del sonido generado automáticamente.
NOMBRE_ARCHIVO_CHOQUE = "choque.mp3"
_ruta_choque_lista = None

# ----- LEDs y motores del ESP32 (modo carro y modo control) -----
# Puerto donde está conectado el ESP32.
#   Windows:      "COM3", "COM5", etc.
#   Linux/Mac:    "/dev/ttyUSB0" o "/dev/cu.usbserial-XXXX"
# Para saber cuál es el tuyo, corre en una terminal (con el ESP32 conectado):
#   python -m serial.tools.list_ports
PUERTO_ESP32 = "COM8"
VELOCIDAD_SERIAL = 115200

# Letra que se le manda al ESP32 según la dirección detectada.
# DEBEN coincidir con las que entiende main.py del ESP32 (W/A/S/D).
LETRAS_LED = {
    "ARRIBA": "W",      # adelante
    "ABAJO": "S",       # atrás
    "IZQUIERDA": "A",   # izquierda
    "DERECHA": "D",     # derecha
}

esp32 = None
HAY_ESP32 = False
if HAY_LIBRERIA_SERIAL:
    try:
        esp32 = serial.Serial(PUERTO_ESP32, VELOCIDAD_SERIAL, timeout=0)
        time.sleep(2)   # muchas placas se reinician al abrir el puerto: esperar
        HAY_ESP32 = True
        print(f"[ESP32 conectado en {PUERTO_ESP32}]")
    except Exception as e:
        print(f"[No pude conectar con el ESP32 en {PUERTO_ESP32}: {e}]")
        print("[Los modos seguirán funcionando, pero sin los LEDs/motores físicos.]")
else:
    print("[pyserial no está instalado: los LEDs del ESP32 no se controlarán. "
          "Instálalo con: pip install pyserial]")


def _enviar_letra_esp32(letra):
    """Manda una letra cruda (W/A/S/D o X para detener) al ESP32."""
    if not HAY_ESP32:
        return
    try:
        esp32.write(letra.encode())
    except Exception as e:
        print(f"[Error enviando al ESP32: {e}]")


def _enviar_a_esp32(direccion):
    """Manda por serie la letra (W/A/S/D) que corresponde a la dirección detectada."""
    letra = LETRAS_LED.get(direccion)
    if letra:
        _enviar_letra_esp32(letra)


# ----- Cerebro de IA con Groq (para que NO sea tonta) -----
# La clave se toma SIEMPRE de la variable de entorno GROQ_API_KEY.
# Nunca la pegues directamente en el código si vas a compartirlo.
CLAVE_API = os.environ.get("GROQ_API_KEY", "")

# Modelo de Groq a usar.
#   "llama-3.3-70b-versatile" capaz y rápido en Groq; se compromete mejor  <- por defecto
#   "llama-3.1-8b-instant"    el más rápido, pero opina con menos firmeza
#   "groq/compound"           BUSCA EN INTERNET y da links, pero es LENTO
# La lista actual está en https://console.groq.com/docs/models
MODELO_IA = "llama-3.3-70b-versatile"
# -------------------------

# Id de la voz en español (se detecta una sola vez al arrancar)
VOZ_ID = None
_aviso_voz_mostrado = False   # para avisar solo una vez si la voz natural falla

# Páginas conocidas para "abre ..."
SITIOS = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://gmail.com",
    "correo": "https://gmail.com",
    "facebook": "https://facebook.com",
    "instagram": "https://instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "twitter": "https://twitter.com",
    "wikipedia": "https://es.wikipedia.org",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
}

# Para que la fecha salga en español (días y meses)
for _loc in ("es_ES.UTF-8", "es_CO.UTF-8", "Spanish_Spain", "es_ES"):
    try:
        locale.setlocale(locale.LC_TIME, _loc)
        break
    except locale.Error:
        continue


# ---------------------------------------------------------------------------
# Cerebro de IA (Groq)
# ---------------------------------------------------------------------------
# Se activa solo si está la librería Y hay una clave válida.
if HAY_LIBRERIA_IA and CLAVE_API:
    cliente_ia = Groq(api_key=CLAVE_API, timeout=20.0)   # no se cuelga más de 20s
    HAY_IA = True
else:
    cliente_ia = None
    HAY_IA = False

# Memoria de la conversación (se reinicia al cerrar el programa)
historial = []

# Instrucciones para la IA: breve por defecto, y SIEMPRE se moja al opinar.
SISTEMA_IA = (
    "Eres Siri, un asistente de voz que habla en español. Responde de forma "
    "BREVE y natural (1 a 3 frases) porque se lee en voz alta; si piden algo "
    "largo (una historia, una explicación), hazlo completo. "
    "REGLA CLAVE: cuando te pidan tu opinión o una predicción (un partido, el "
    "clima, comida, lo que sea), SIEMPRE te mojas y das una respuesta personal "
    "y concreta. Empieza con tu veredicto directo (por ejemplo: 'Yo creo que "
    "gana tal equipo' o 'Mi favorito es...') y luego justifícalo en una o dos "
    "frases. Está PROHIBIDO responder con 'depende', 'es difícil de predecir', "
    "'no puedo saberlo' o pedir más información para evadir: igual debes elegir "
    "una opción y comprometerte. Si no tienes datos del momento, usa tu mejor "
    "criterio y aun así da tu predicción (puedes aclararlo en pocas palabras, "
    "sin que eso te impida opinar). Sé sincero, directo y con personalidad. "
    "No uses listas con viñetas, markdown ni emojis."
)


def _extraer_fuentes(respuesta):
    """Saca las URLs que el modelo consultó en la web (si usó búsqueda)."""
    urls = []
    try:
        mensaje = respuesta.choices[0].message
        herramientas = getattr(mensaje, "executed_tools", None) or []
        for h in herramientas:
            datos = getattr(h, "search_results", None) or getattr(h, "output", h)
            urls += re.findall(r'https?://[^\s"\'\]\)]+', str(datos))
    except Exception:
        pass
    # quitar duplicados (y la basura de puntuación al final) conservando el orden
    limpias = []
    for u in urls:
        u = u.rstrip('.,;)')
        if u not in limpias:
            limpias.append(u)
    return limpias[:5]


def preguntar_a_ia(texto):
    """Le manda el texto a Groq (recordando la charla) y devuelve su respuesta."""
    historial.append({"role": "user", "content": texto})

    # Conservar solo lo reciente para no gastar de más, empezando siempre por 'user'
    while len(historial) > 10:
        historial.pop(0)
    while historial and historial[0]["role"] != "user":
        historial.pop(0)

    try:
        # Groq usa formato estilo OpenAI: el 'system' va como primer mensaje
        mensajes = [{"role": "system", "content": SISTEMA_IA}] + historial
        respuesta = cliente_ia.chat.completions.create(
            model=MODELO_IA,
            max_tokens=2048,          # suficiente para historias/explicaciones largas
            messages=mensajes,
        )
        salida = (respuesta.choices[0].message.content or "").strip()
        historial.append({"role": "assistant", "content": salida})

        # Mostrar los links que consultó (en consola y en la ventana)
        fuentes = _extraer_fuentes(respuesta)
        if fuentes:
            print("📚 Fuentes:")
            for i, url in enumerate(fuentes, 1):
                print(f"   {i}. {url}")
                _enviar("fuente", url)

        return salida
    except Exception as e:
        print(f"[Error consultando a la IA: {e}]")
        _enviar("info", f"⚠ La IA falló o tardó demasiado: {e}")
        if historial and historial[-1]["role"] == "user":
            historial.pop()      # deshacer para no dejar el historial roto
        return ""


def responder_inteligente(texto, consulta_wiki=None):
    """
    Responde con la IA (Groq) si está disponible.
    Si no hay IA, usa Wikipedia (para preguntas) o avisa que no entendió.
    """
    if HAY_IA:
        salida = preguntar_a_ia(texto)
        if salida:
            hablar(salida)
            return
    if consulta_wiki is not None:
        responder_wikipedia(consulta_wiki)
    else:
        hablar("No entendí esa orden.")


# ---------------------------------------------------------------------------
# Voz (texto a voz)
# ---------------------------------------------------------------------------
def elegir_voz():
    """Detecta UNA sola vez una voz en español del sistema (respaldo) y la devuelve."""
    motor = pyttsx3.init()
    elegido = None
    for voz in motor.getProperty("voices"):
        etiqueta = f"{voz.name} {voz.id}".lower()
        if any(p in etiqueta for p in
               ("spanish", "español", "es-", "es_", "helena",
                "sabina", "monica", "mónica", "diego", "jorge")):
            elegido = voz.id
            break
    motor.stop()
    return elegido


def _reproducir_audio(ruta):
    """Reproduce un archivo de audio (mp3/wav) usando el mixer de pygame."""
    if not HAY_VOZ_NATURAL:        # el mixer viene con la voz natural (pygame)
        return False
    try:
        with lock_voz:
            pygame.mixer.music.load(ruta)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        return True
    except Exception as e:
        print(f"[No pude reproducir {ruta}: {e}]")
        return False


def _ruta_intro():
    """Devuelve la ruta del audio de intro si existe (o None)."""
    if not SONIDO_INTRO:
        return None
    candidatos = [SONIDO_INTRO]
    try:
        aqui = os.path.dirname(os.path.abspath(__file__))
        candidatos.insert(0, os.path.join(aqui, SONIDO_INTRO))
    except NameError:
        pass
    for c in candidatos:
        if os.path.exists(c):
            return c
    return None


def _hablar_natural(texto):
    """Voz neuronal (suena casi humana). Genera un audio y lo reproduce."""
    ruta = os.path.join(tempfile.gettempdir(), "siri_voz.mp3")

    async def generar():
        com = edge_tts.Communicate(texto, VOZ_NATURAL, rate=VELOCIDAD_NATURAL,
                                   pitch=TONO_VOZ, volume=VOLUMEN_NATURAL)
        await com.save(ruta)

    asyncio.run(generar())
    pygame.mixer.music.load(ruta)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():       # esperar a que termine de hablar
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()                # liberar el archivo


def _hablar_sistema(texto):
    """Respaldo: voz del sistema (pyttsx3). Suena más robótica pero no falla."""
    motor = pyttsx3.init()
    motor.setProperty("rate", VELOCIDAD_VOZ)
    if VOZ_ID:
        motor.setProperty("voice", VOZ_ID)
    motor.say(texto)
    motor.runAndWait()
    motor.stop()


def hablar(texto):
    """
    Dice algo en voz alta, lo muestra en pantalla y lo envía a la ventana.
    Usa la voz natural si está disponible; si falla, la voz del sistema.
    """
    print(f"🔊 {texto}")
    _enviar("siri", texto)
    _enviar("estado", "Hablando")
    global _aviso_voz_mostrado
    with lock_voz:                       # que no hablen dos a la vez
        if HAY_VOZ_NATURAL:
            try:
                _hablar_natural(texto)
                return
            except Exception as e:
                print(f"[Voz natural no disponible, uso la del sistema: {e}]")
                if not _aviso_voz_mostrado:
                    _enviar("info", f"⚠ Voz natural falló (se usa la del sistema): {e}")
                    _aviso_voz_mostrado = True
        elif not _aviso_voz_mostrado:
            _enviar("info", "⚠ Voz natural apagada: instala edge-tts y pygame "
                            "(pip install edge-tts pygame)")
            _aviso_voz_mostrado = True
        _hablar_sistema(texto)


# ---------------------------------------------------------------------------
# Oído (reconocimiento de voz)
# ---------------------------------------------------------------------------
def escuchar(reconocedor, microfono, espera=None, max_frase=8, idioma=None):
    """
    Escucha el micrófono y devuelve:
      - el texto reconocido (en minúsculas) si entendió algo,
      - ""   si oyó algo pero NO lo entendió,
      - None si pasó el tiempo de 'espera' SIN que nadie hablara (silencio).
    'idioma' permite reconocer en inglés (activación) o español (comandos).
    """
    if idioma is None:
        idioma = IDIOMA
    with microfono as fuente:
        try:
            audio = reconocedor.listen(fuente, timeout=espera,
                                       phrase_time_limit=max_frase)
        except sr.WaitTimeoutError:
            return None
    try:
        return reconocedor.recognize_google(audio, language=idioma).lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"[Error de conexión: {e}]")
        return ""


def _es_corto_o_comando(texto):
    """True si la frase es corta o un comando/saludo conocido (responder YA)."""
    if len(texto.split()) <= 2:
        return True
    claves = ("hora", "fecha", "qué día", "que dia", "pausa", "reanuda",
              "continúa", "continua", "siguiente", "anterior", "silencio",
              "mutea", "sube", "baja", "volumen", "abre", "abrir", "reproduce",
              "pon ", "busca", "googlea", "hola", "gracias", "adiós", "adios",
              "chao", "apágate", "apagate", "carro", "control",
              "seguimiento", "sígueme", "sigueme", "seguirme")
    return any(k in texto for k in claves)


def escuchar_comando(reconocedor, microfono, espera):
    """
    Escucha una orden de forma ADAPTATIVA:
      - Si es corta o un comando conocido, la devuelve de inmediato.
      - Si parece una frase larga, espera por si sigues hablando (une los trozos).
    Devuelve texto, "" (no entendió) o None (silencio).
    """
    texto = escuchar(reconocedor, microfono, espera=espera, max_frase=MAX_FRASE)
    if not texto:                         # None (silencio) o "" (no entendió)
        return texto
    if _es_corto_o_comando(texto):        # respuesta rápida
        return texto
    # Frase larga: seguir capturando mientras el usuario siga hablando
    # (acotado a unas pocas vueltas para que NUNCA se quede pegado)
    for _ in range(5):
        extra = escuchar(reconocedor, microfono, espera=CONTINUACION,
                         max_frase=MAX_FRASE)
        if extra:                         # siguió hablando -> unir
            texto = (texto + " " + extra).strip()
        else:                             # silencio o no entendió -> terminó
            break
    return texto


# ---------------------------------------------------------------------------
# Utilidades para entender las órdenes de forma FLEXIBLE
# ---------------------------------------------------------------------------
def tiene_palabra(comando, palabras):
    """True si alguna palabra aparece COMPLETA (evita que 'ahora' active 'hora')."""
    tokens = comando.split()
    return any(p in tokens for p in palabras)


def tiene_frase(comando, frases):
    """True si alguna expresión aparece dentro del texto."""
    return any(f in comando for f in frases)


def extraer(comando, basura):
    """Quita del texto las palabras/expresiones de 'basura' para dejar la consulta limpia."""
    texto = comando
    for b in sorted(basura, key=len, reverse=True):   # primero las más largas
        texto = texto.replace(b, " ")
    return " ".join(texto.split())


def buscar_en_google(consulta):
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(consulta))


def tecla_media(tecla, veces=1):
    """
    Envía una tecla multimedia del sistema (play/pausa, siguiente, volumen...).
    Estas teclas controlan el reproductor del navegador aunque no esté en foco.
    """
    if not HAY_TECLAS:
        hablar("Para controlar la reproducción necesito el paquete pyautogui. "
               "Instálalo con: pip install pyautogui")
        return False
    for _ in range(veces):
        pyautogui.press(tecla)
    return True


def reproducir_youtube(consulta):
    """
    Busca en YouTube y abre DIRECTAMENTE el primer video, así empieza a
    reproducirse solo (no solo lleva a la lista de resultados).

    Cómo: pide la página de resultados, saca el ID del primer video y abre
    /watch?v=ID. Si algo falla, como plan B abre los resultados de búsqueda.
    """
    url_busqueda = ("https://www.youtube.com/results?search_query=" +
                    urllib.parse.quote(consulta))
    try:
        pedido = urllib.request.Request(
            url_busqueda, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(pedido, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        ids = re.findall(r'"videoId":"([\w-]{11})"', html)
        if ids:
            webbrowser.open(f"https://www.youtube.com/watch?v={ids[0]}")
            return True
    except Exception as e:
        print(f"[No pude abrir el video directo: {e}]")
    # Plan B: al menos mostrar los resultados de búsqueda
    webbrowser.open(url_busqueda)
    return False


def responder_wikipedia(consulta):
    if not consulta:
        hablar("¿Sobre qué quieres que te cuente?")
        return
    if not HAY_WIKI:
        hablar("Para responder preguntas necesito el paquete wikipedia. "
               "Instálalo con: pip install wikipedia")
        return
    try:
        resumen = wikipedia.summary(consulta, sentences=2, auto_suggest=True)
        hablar(resumen)
    except wikipedia.DisambiguationError as e:
        hablar(f"Hay varias opciones sobre {consulta}. "
               f"Por ejemplo: {', '.join(e.options[:3])}.")
    except Exception:
        hablar(f"No encontré información sobre {consulta}.")


def _preparar_audios_carro():
    """
    Genera UNA SOLA VEZ el audio de las 4 frases del modo carro y las deja
    guardadas en archivos temporales (ya no se usa en el flujo normal, pero
    se deja por si quieres volver a anunciar los movimientos por voz).
    """
    if not HAY_VOZ_NATURAL:
        return

    async def generar_uno(texto, ruta):
        com = edge_tts.Communicate(texto, VOZ_NATURAL, rate=VELOCIDAD_NATURAL,
                                   pitch=TONO_VOZ, volume=VOLUMEN_NATURAL)
        await com.save(ruta)

    for direccion, frase in FRASES_CARRO.items():
        ruta = os.path.join(tempfile.gettempdir(), f"siri_carro_{direccion}.mp3")
        try:
            asyncio.run(generar_uno(frase, ruta))
            _audios_carro_listos[direccion] = ruta
        except Exception as e:
            print(f"[No pude pre-generar el audio de '{frase}': {e}]")


def _decir_direccion_carro(direccion):
    """
    Reproduce al instante el audio de la dirección (si ya está pre-generado).
    Si no hay audio en caché, usa hablar() como respaldo (más lento).
    """
    frase = FRASES_CARRO.get(direccion, "")
    ruta = _audios_carro_listos.get(direccion)
    print(f"🔊 {frase}")
    _enviar("siri", frase)
    if ruta and os.path.exists(ruta):
        with lock_voz:
            pygame.mixer.music.load(ruta)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(30)
            pygame.mixer.music.unload()
    else:
        hablar(frase)


def _generar_wav_choque(ruta, duracion=0.5, tasa=22050):
    """
    Genera un efecto de sonido de "choque" (golpe seco + ruido que se apaga
    rápido) sin necesitar ningún archivo de audio externo, y lo guarda como
    .wav en la ruta indicada.
    """
    n_muestras = int(duracion * tasa)
    muestras = []
    for i in range(n_muestras):
        t = i / tasa
        decaimiento = math.exp(-9 * t)                       # se apaga rápido
        ruido = random.uniform(-1, 1)                         # el "crash"
        golpe = math.sin(2 * math.pi * 70 * t) * math.exp(-18 * t)  # el "thump" grave
        valor = (ruido * 0.55 + golpe * 0.9) * decaimiento
        valor = max(-1.0, min(1.0, valor))
        muestras.append(int(valor * 32000))

    with wave.open(ruta, "w") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(tasa)
        archivo.writeframes(b"".join(struct.pack("<h", s) for s in muestras))


def _preparar_sonido_choque():
    """Deja listo el sonido de choque (propio si existe, o generado) una sola vez."""
    global _ruta_choque_lista

    # Si el usuario puso su propio archivo de choque en la carpeta, se usa ese.
    try:
        aqui = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        aqui = "."
    for nombre in (NOMBRE_ARCHIVO_CHOQUE, "choque.wav"):
        candidato = os.path.join(aqui, nombre)
        if os.path.exists(candidato):
            _ruta_choque_lista = candidato
            return

    # Si no hay archivo propio, generamos uno sintético en una carpeta temporal.
    ruta_generada = os.path.join(tempfile.gettempdir(), "siri_choque.wav")
    try:
        _generar_wav_choque(ruta_generada)
        _ruta_choque_lista = ruta_generada
    except Exception as e:
        print(f"[No pude generar el sonido de choque: {e}]")


def _reproducir_choque():
    """Reproduce el sonido de choque (instantáneo, ya está pre-generado)."""
    print("💥 ¡Choque!")
    _enviar("siri", "💥 ¡Choque!")
    if _ruta_choque_lista and os.path.exists(_ruta_choque_lista) and HAY_VOZ_NATURAL:
        with lock_voz:
            pygame.mixer.music.load(_ruta_choque_lista)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(30)
            pygame.mixer.music.unload()
    else:
        hablar("Choque")


def _dibujar_carro(lienzo, cx, cy, ancho, alto, color_cuerpo, mirando_arriba=True,
                   chispas=False):
    """
    Dibuja un carrito con sombreado (más claro de un lado, más oscuro del
    otro, como si le diera la luz), cabina, parabrisas y luces. No es un
    render 3D real, pero con el sombreado y las proporciones da sensación
    de volumen en vez de un rectángulo plano.
    """
    ancho = max(10, int(ancho))
    alto = max(14, int(alto))
    x0, y0 = cx - ancho // 2, cy - alto // 2
    x1, y1 = cx + ancho // 2, cy + alto // 2

    # Sombra en el piso (da la sensación de que el carro "flota" un poco sobre la calle)
    cv2.ellipse(lienzo, (cx, y1 - 3), (ancho // 2 + 5, max(4, alto // 10)),
                0, 0, 360, (30, 55, 30), -1)

    color_claro = tuple(min(255, int(c * 1.45)) for c in color_cuerpo)
    color_oscuro = tuple(int(c * 0.55) for c in color_cuerpo)
    radio = max(3, min(ancho, alto) // 6)

    # Cuerpo con esquinas redondeadas (rectángulo + círculos en las puntas)
    cv2.rectangle(lienzo, (x0 + radio, y0), (x1 - radio, y1), color_cuerpo, -1)
    cv2.rectangle(lienzo, (x0, y0 + radio), (x1, y1 - radio), color_cuerpo, -1)
    for ex, ey in ((x0 + radio, y0 + radio), (x1 - radio, y0 + radio),
                  (x0 + radio, y1 - radio), (x1 - radio, y1 - radio)):
        cv2.circle(lienzo, (ex, ey), radio, color_cuerpo, -1)

    # Sombreado lateral: un lado más claro (donde "pega la luz") y otro más
    # oscuro, para simular volumen sin necesitar un motor 3D de verdad.
    grosor = max(2, ancho // 7)
    cv2.rectangle(lienzo, (x0, y0 + radio), (x0 + grosor, y1 - radio), color_oscuro, -1)
    cv2.rectangle(lienzo, (x1 - grosor, y0 + radio), (x1, y1 - radio), color_claro, -1)

    # Cabina / techo
    cab_x0, cab_x1 = x0 + ancho // 5, x1 - ancho // 5
    cab_y0, cab_y1 = y0 + alto // 5, y1 - alto // 4
    cv2.rectangle(lienzo, (cab_x0, cab_y0), (cab_x1, cab_y1), color_oscuro, -1)

    # Parabrisas y luces (adelante según hacia dónde "mira" el carro)
    y_luces_frente = y0 + 5 if mirando_arriba else y1 - 5
    y_luces_atras = y1 - 5 if mirando_arriba else y0 + 5
    alto_parabrisas = max(4, alto // 6)
    if mirando_arriba:
        cv2.rectangle(lienzo, (cab_x0 + 3, cab_y0 + 3), (cab_x1 - 3, cab_y0 + alto_parabrisas),
                      (225, 240, 255), -1)
    else:
        cv2.rectangle(lienzo, (cab_x0 + 3, cab_y1 - alto_parabrisas), (cab_x1 - 3, cab_y1 - 3),
                      (225, 240, 255), -1)

    cv2.circle(lienzo, (x0 + 7, int(y_luces_frente)), max(2, ancho // 14), (210, 255, 255), -1)
    cv2.circle(lienzo, (x1 - 7, int(y_luces_frente)), max(2, ancho // 14), (210, 255, 255), -1)
    cv2.circle(lienzo, (x0 + 7, int(y_luces_atras)), max(2, ancho // 16), (0, 0, 200), -1)
    cv2.circle(lienzo, (x1 - 7, int(y_luces_atras)), max(2, ancho // 16), (0, 0, 200), -1)

    cv2.rectangle(lienzo, (x0, y0), (x1, y1), (15, 15, 15), 1)

    if chispas:
        for angulo in range(0, 360, 30):
            rad = math.radians(angulo)
            x2 = int(cx + math.cos(rad) * ancho * 0.95)
            y2 = int(cy + math.sin(rad) * ancho * 0.95)
            cv2.line(lienzo, (cx, cy), (x2, y2), (0, 220, 255), 2)


def _dibujar_simulador(carril_x, velocidad, scroll_offset, frames_flash_choque, npcs):
    """
    Dibuja la calle con el carro del jugador y los carros de tráfico (npcs).
    Los carros de tráfico se ven más chicos mientras más lejos están
    (efecto de profundidad/perspectiva simple) y se acercan a medida que el
    jugador avanza.
    """
    lienzo = np.full((SIM_ALTO, SIM_ANCHO, 3), (55, 135, 55), dtype=np.uint8)  # pasto

    x0 = (SIM_ANCHO - SIM_ANCHO_CALLE) // 2
    x1 = x0 + SIM_ANCHO_CALLE
    cv2.rectangle(lienzo, (x0, 0), (x1, SIM_ALTO), (58, 58, 58), -1)          # asfalto
    cv2.rectangle(lienzo, (x0 - 6, 0), (x0, SIM_ALTO), (235, 235, 235), -1)    # borde izq
    cv2.rectangle(lienzo, (x1, 0), (x1 + 6, SIM_ALTO), (235, 235, 235), -1)    # borde der

    # Carriles: dos líneas discontinuas (para 3 carriles) que se mueven con el scroll
    separacion, largo, grosor = 65, 32, 7
    for carril_rel in (-1, 1):
        linea_x = SIM_ANCHO // 2 + carril_rel * (SIM_ANCHO_CALLE // 3)
        y = int(scroll_offset) % separacion - separacion
        while y < SIM_ALTO:
            cv2.rectangle(lienzo, (linea_x - grosor // 2, y),
                          (linea_x + grosor // 2, y + largo), (225, 225, 60), -1)
            y += separacion

    centro_x = SIM_ANCHO // 2
    cy_jugador = int(SIM_ALTO * 0.78)

    # ----- Carros de tráfico (de más lejos a más cerca, para que se tapen bien) -----
    for npc in sorted(npcs, key=lambda n: -n["z"]):
        distancia = npc["z"] - scroll_offset
        if distancia < -150 or distancia > SIM_PROFUNDIDAD_MAX + 100:
            continue  # muy lejos o ya se pasó de largo; no hace falta dibujarlo
        factor = 1.0 - min(1.0, distancia / SIM_PROFUNDIDAD_MAX) * (1.0 - SIM_ESCALA_MIN_LEJOS)
        factor = max(SIM_ESCALA_MIN_LEJOS, min(1.0, factor))
        y_npc = int(cy_jugador - distancia * (cy_jugador / SIM_PROFUNDIDAD_MAX))
        x_npc = centro_x + npc["carril_px"]
        tiene_chispas = npc.get("frames_flash", 0) > 0
        color = (0, 0, 230) if tiene_chispas else npc["color"]
        _dibujar_carro(lienzo, x_npc, y_npc,
                       SIM_ANCHO_CARRO * factor, SIM_ALTO_CARRO * factor,
                       color, mirando_arriba=True, chispas=tiene_chispas)

    # ----- Carro del jugador (siempre al frente, tamaño completo) -----
    color_jugador = (0, 0, 230) if frames_flash_choque > 0 else (35, 130, 245)
    _dibujar_carro(lienzo, centro_x + int(carril_x), cy_jugador,
                   SIM_ANCHO_CARRO, SIM_ALTO_CARRO, color_jugador,
                   mirando_arriba=True, chispas=frames_flash_choque > 0)

    if frames_flash_choque > 0:
        cv2.rectangle(lienzo, (0, 0), (SIM_ANCHO - 1, SIM_ALTO - 1), (0, 0, 255), 10)
        cv2.putText(lienzo, "¡CHOQUE!", (SIM_ANCHO // 2 - 100, SIM_ALTO // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3, cv2.LINE_AA)

    cv2.putText(lienzo, f"Velocidad: {velocidad:+.1f}", (14, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    return lienzo


# ---------------------------------------------------------------------------
# Modo carro: detecta hacia dónde mueves la mano y mueve el carro en pantalla
# ---------------------------------------------------------------------------
def _bucle_modo_carro():
    """
    Corre en su propio hilo: abre la cámara, sigue la mano, mueve el carrito
    del simulador según el gesto (silencioso: solo se muestra en pantalla,
    no se anuncia por voz) y le manda la letra correspondiente (W/A/S/D) al
    ESP32 para que mueva los motores y prenda el LED de esa dirección. Se
    detiene cuando se activa detener_carro_evento, si presionas 'q' en
    cualquiera de las dos ventanas, o si sostienes DOS manos frente a la
    cámara varios frames seguidos.

    La velocidad es CONSTANTE (SIM_VELOCIDAD_CONSTANTE): el carro siempre
    avanza igual. El choque contra un carro de tráfico es AUTOMÁTICO.
    """
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    manos = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,             # 2 manos: para poder detectar "ambas manos = salir"
        model_complexity=0,          # modelo liviano = mucho más rápido
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    )

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # CAP_DSHOW abre más rápido en Windows
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        hablar("No pude abrir la cámara para el modo carro.")
        return

    # Buffer de 1: si no procesamos un frame a tiempo, la cámara no acumula
    # frames viejos en cola (eso era parte del retraso).
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    posicion_anterior = None
    frames_enfriamiento = 0
    frames_con_dos_manos = 0     # debounce: necesita varios frames SEGUIDOS
    ultima_direccion = ""
    salir_por_dos_manos = False

    # ----- Estado del carrito en el simulador -----
    carril_x = 0.0
    velocidad = SIM_VELOCIDAD_CONSTANTE   # siempre avanza a velocidad constante
    scroll_offset = 0.0
    frames_flash_choque = 0

    # ----- Tráfico: otros carros en la vía -----
    npcs = []
    for carril_rel, z_inicial, color in NPCS_INICIALES:
        npcs.append({
            "carril_px": carril_rel * SIM_DESPLAZAMIENTO_CARRIL_NPC,
            "z": float(z_inicial),
            "color": color,
            "frames_flash": 0,
            "enfriamiento_choque": 0,
        })

    while not detener_carro_evento.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        # Procesamos una copia reducida (más rápido); pero dibujamos y
        # mostramos el frame a tamaño normal para que se vea bien.
        alto_orig, ancho_orig = frame.shape[:2]
        escala = ANCHO_PROCESAMIENTO_CAMARA / ancho_orig
        frame_chico = cv2.resize(frame, (ANCHO_PROCESAMIENTO_CAMARA,
                                         int(alto_orig * escala)))
        frame_rgb = cv2.cvtColor(frame_chico, cv2.COLOR_BGR2RGB)
        resultado = manos.process(frame_rgb)

        manos_detectadas = resultado.multi_hand_landmarks or []

        # ----- Dos manos sostenidas varios frames seguidos -> salir -----
        if len(manos_detectadas) >= 2:
            frames_con_dos_manos += 1
        else:
            frames_con_dos_manos = 0

        if frames_con_dos_manos >= FRAMES_CONFIRMAR_DOS_MANOS:
            for lm in manos_detectadas:
                mp_drawing.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)
            cv2.putText(frame, "SALIENDO...", (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                        1.5, (0, 0, 255), 3, cv2.LINE_AA)
            cv2.imshow("Modo carro (q = salir)", frame)
            cv2.waitKey(1)
            salir_por_dos_manos = True
            break

        # Mientras solo estemos "confirmando" (1 a 9 frames de 2 manos), no
        # procesamos gestos de movimiento con esa mano para no hacer cosas raras.
        if len(manos_detectadas) == 1 and frames_con_dos_manos == 0:
            landmarks_mano = manos_detectadas[0]
            mp_drawing.draw_landmarks(frame, landmarks_mano, mp_hands.HAND_CONNECTIONS)

            punto_referencia = landmarks_mano.landmark[9]
            x_norm = punto_referencia.x
            y_norm = punto_referencia.y

            if frames_enfriamiento > 0:
                frames_enfriamiento -= 1

            if posicion_anterior is not None and frames_enfriamiento == 0:
                dx = x_norm - posicion_anterior[0]
                dy = y_norm - posicion_anterior[1]

                if abs(dx) > UMBRAL_MOVIMIENTO_MANO or abs(dy) > UMBRAL_MOVIMIENTO_MANO:
                    if abs(dx) > abs(dy):
                        direccion = "DERECHA" if dx > 0 else "IZQUIERDA"
                    else:
                        direccion = "ABAJO" if dy > 0 else "ARRIBA"

                    ultima_direccion = direccion
                    frames_enfriamiento = ENFRIAMIENTO_FRAMES_MANO
                    posicion_anterior = (x_norm, y_norm)

                    # Enviar la dirección al ESP32 (W/A/S/D) para mover los
                    # motores y encender el LED correspondiente
                    _enviar_a_esp32(direccion)

                    # Mover el carrito del simulador según el gesto.
                    # ARRIBA/ABAJO no cambian la velocidad (es constante);
                    # solo IZQUIERDA/DERECHA cambian de carril.
                    if direccion == "IZQUIERDA":
                        carril_x = max(carril_x - SIM_PASO_CARRIL, -SIM_LIMITE_CARRIL)
                    elif direccion == "DERECHA":
                        carril_x = min(carril_x + SIM_PASO_CARRIL, SIM_LIMITE_CARRIL)
            else:
                posicion_anterior = (x_norm, y_norm)
        elif len(manos_detectadas) == 0:
            posicion_anterior = None

        if ultima_direccion:
            color_texto = (0, 140, 255) if ultima_direccion == "CHOQUE" else (0, 255, 0)
            texto = "¡CHOQUE!" if ultima_direccion == "CHOQUE" else ultima_direccion
            cv2.putText(frame, texto, (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                        1.5, color_texto, 3, cv2.LINE_AA)

        # ----- Choque AUTOMÁTICO: si el carro del jugador toca a un NPC -----
        for npc in npcs:
            if npc["enfriamiento_choque"] > 0:
                npc["enfriamiento_choque"] -= 1
                continue
            distancia_npc = npc["z"] - scroll_offset
            mismo_carril = abs(npc["carril_px"] - carril_x) < SIM_TOLERANCIA_CARRIL_CHOQUE
            esta_tocando = 0 <= distancia_npc <= SIM_DISTANCIA_CHOQUE
            if mismo_carril and esta_tocando:
                npc["frames_flash"] = 15
                npc["enfriamiento_choque"] = SIM_ENFRIAMIENTO_CHOQUE_NPC
                npc["z"] += SIM_LARGO_MUNDO_NPC
                frames_flash_choque = 12
                ultima_direccion = "CHOQUE"
                threading.Thread(target=_reproducir_choque, daemon=True).start()

        # ----- Actualizar y dibujar el simulador (cada frame) -----
        scroll_offset += velocidad          # velocidad constante: siempre avanza igual
        if frames_flash_choque > 0:
            frames_flash_choque -= 1

        for npc in npcs:
            if npc["frames_flash"] > 0:
                npc["frames_flash"] -= 1
            # Si el jugador ya lo dejó bien atrás, lo reaparecemos más adelante
            # (así siempre hay tráfico, sin importar cuánto avances).
            if npc["z"] - scroll_offset < -150:
                npc["z"] += SIM_LARGO_MUNDO_NPC

        lienzo_sim = _dibujar_simulador(carril_x, velocidad, scroll_offset,
                                        frames_flash_choque, npcs)
        cv2.imshow("Simulador de carro", lienzo_sim)
        cv2.imshow("Modo carro (q = salir)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    _enviar_letra_esp32("X")            # al salir, frenar el carro real
    detener_carro_evento.clear()
    if salir_por_dos_manos:
        hablar("Saliste del modo carro.")
    else:
        _enviar("info", "Modo carro apagado.")


def activar_modo_carro():
    """Enciende el modo carro (si ya está encendido, no hace nada)."""
    global hilo_carro
    if not HAY_VISION:
        hablar("Para el modo carro necesito opencv y mediapipe. "
               "Instálalos con: pip install opencv-python mediapipe")
        return
    if hilo_carro and hilo_carro.is_alive():
        hablar("El modo carro ya está encendido.")
        return
    if hilo_control and hilo_control.is_alive():
        hablar("Primero apaga el modo control.")
        return
    if hilo_seguimiento and hilo_seguimiento.is_alive():
        hablar("Primero apaga el modo seguimiento.")
        return
    detener_carro_evento.clear()

    # El sonido de choque (no es voz, es un efecto) se deja listo de una vez.
    if not _ruta_choque_lista:
        threading.Thread(target=_preparar_sonido_choque, daemon=True).start()
    if HAY_ESP32:
        hablar("Modo carro activado. Mueve tu mano para controlarlo y prender los LEDs.")
    else:
        hablar("Modo carro activado. Mueve tu mano para controlarlo.")

    hilo_carro = threading.Thread(target=_bucle_modo_carro, daemon=True)
    hilo_carro.start()


def detener_modo_carro():
    """Apaga el modo carro si está encendido."""
    if hilo_carro and hilo_carro.is_alive():
        detener_carro_evento.set()
        hablar("Modo carro desactivado.")
    else:
        hablar("El modo carro no está encendido.")


# ---------------------------------------------------------------------------
# Modo control: manejas el carro con el TECLADO (W / A / S / D)
# ---------------------------------------------------------------------------
def _bucle_modo_control():
    """
    Corre en su propio hilo: muestra el simulador y lo mueve según las teclas
    que hay en 'teclas_control' (las llena la ventanita "Modo control" de
    Tkinter). Mientras mantengas una tecla, repite esa letra al ESP32 cada
    INTERVALO_ENVIO_CONTROL segundos; al soltar todo manda 'X' para frenar.

        W -> el carro avanza      S -> el carro retrocede
        A -> se mueve a la izq.   D -> se mueve a la der.

    Se detiene con detener_control_evento o presionando 'q' en el simulador.
    """
    carril_x = 0.0
    scroll_offset = 0.0
    frames_flash_choque = 0
    velocidad = 0.0
    ultimo_envio = 0.0
    estaba_moviendo = False

    npcs = []
    for carril_rel, z_inicial, color in NPCS_INICIALES:
        npcs.append({
            "carril_px": carril_rel * SIM_DESPLAZAMIENTO_CARRIL_NPC,
            "z": float(z_inicial),
            "color": color,
            "frames_flash": 0,
            "enfriamiento_choque": 0,
        })

    while not detener_control_evento.is_set():
        activa = teclas_control[-1] if teclas_control else None

        # ----- ESP32: repetir la letra mientras se mantenga la tecla -----
        ahora = time.time()
        if activa:
            if ahora - ultimo_envio >= INTERVALO_ENVIO_CONTROL:
                _enviar_letra_esp32(activa.upper())
                ultimo_envio = ahora
            estaba_moviendo = True
        elif estaba_moviendo:
            _enviar_letra_esp32("X")          # soltó todo -> frenar
            estaba_moviendo = False

        # ----- Simulador -----
        velocidad = 0.0
        if activa == "w":
            velocidad = SIM_VELOCIDAD_CONSTANTE
        elif activa == "s":
            velocidad = -SIM_VELOCIDAD_CONSTANTE
        elif activa == "a":
            carril_x = max(carril_x - PASO_LATERAL_CONTROL, -SIM_LIMITE_CARRIL)
        elif activa == "d":
            carril_x = min(carril_x + PASO_LATERAL_CONTROL, SIM_LIMITE_CARRIL)
        scroll_offset += velocidad

        # ----- Choque automático contra los carros de tráfico -----
        for npc in npcs:
            if npc["enfriamiento_choque"] > 0:
                npc["enfriamiento_choque"] -= 1
                continue
            distancia_npc = npc["z"] - scroll_offset
            mismo_carril = abs(npc["carril_px"] - carril_x) < SIM_TOLERANCIA_CARRIL_CHOQUE
            esta_tocando = 0 <= distancia_npc <= SIM_DISTANCIA_CHOQUE
            if mismo_carril and esta_tocando:
                npc["frames_flash"] = 15
                npc["enfriamiento_choque"] = SIM_ENFRIAMIENTO_CHOQUE_NPC
                npc["z"] += SIM_LARGO_MUNDO_NPC
                frames_flash_choque = 12
                _enviar_letra_esp32("X")      # el carro real también frena al chocar
                threading.Thread(target=_reproducir_choque, daemon=True).start()

        if frames_flash_choque > 0:
            frames_flash_choque -= 1
        for npc in npcs:
            if npc["frames_flash"] > 0:
                npc["frames_flash"] -= 1
            if npc["z"] - scroll_offset < -150:
                npc["z"] += SIM_LARGO_MUNDO_NPC

        lienzo = _dibujar_simulador(carril_x, velocidad, scroll_offset,
                                    frames_flash_choque, npcs)
        cv2.imshow("Simulador (modo control)", lienzo)
        if cv2.waitKey(16) & 0xFF == ord('q'):
            break

    _enviar_letra_esp32("X")                  # al salir, frenar el carro real
    cv2.destroyAllWindows()
    detener_control_evento.clear()
    _enviar("control", "cerrar")              # cerrar la ventanita de teclas
    _enviar("info", "Modo control apagado.")


def activar_modo_control():
    """Enciende el modo control (teclado). Si ya está encendido, no hace nada."""
    global hilo_control
    if not HAY_VISION:
        hablar("Para el modo control necesito opencv. "
               "Instálalo con: pip install opencv-python")
        return
    if hilo_control and hilo_control.is_alive():
        hablar("El modo control ya está encendido.")
        return
    if hilo_carro and hilo_carro.is_alive():
        hablar("Primero apaga el modo carro.")
        return
    if hilo_seguimiento and hilo_seguimiento.is_alive():
        hablar("Primero apaga el modo seguimiento.")
        return
    if not _ruta_choque_lista:
        threading.Thread(target=_preparar_sonido_choque, daemon=True).start()
    detener_control_evento.clear()
    teclas_control.clear()
    _enviar("control", "abrir")               # la ventanita de teclas la abre la GUI
    hablar("Modo control activado. Usa W, A, S y D.")
    hilo_control = threading.Thread(target=_bucle_modo_control, daemon=True)
    hilo_control.start()


def detener_modo_control():
    """Apaga el modo control si está encendido."""
    if hilo_control and hilo_control.is_alive():
        detener_control_evento.set()
        hablar("Modo control desactivado.")
    else:
        hablar("El modo control no está encendido.")


# ---------------------------------------------------------------------------
# Modo seguimiento: la cámara te detecta y el carro te SIGUE
# ---------------------------------------------------------------------------
def _detectar_persona(frame_rgb, pose, cara):
    """
    Devuelve (centro_x, tamano, puntos) o None si no ve a nadie.
      centro_x : 0.0 (borde izquierdo) a 1.0 (borde derecho)
      tamano   : ancho de hombros (fracción del ancho de la imagen)
    Usa los hombros; si no se ven, usa la cara como respaldo.
    """
    res = pose.process(frame_rgb)
    if res.pose_landmarks:
        lm = res.pose_landmarks.landmark
        hi, hd = lm[11], lm[12]      # hombro izquierdo / derecho
        if hi.visibility > 0.5 and hd.visibility > 0.5:
            centro_x = (hi.x + hd.x) / 2
            tamano = abs(hi.x - hd.x)
            return centro_x, tamano, ((hi.x, hi.y), (hd.x, hd.y))

    res = cara.process(frame_rgb)
    if res.detections:
        caja = res.detections[0].location_data.relative_bounding_box
        centro_x = caja.xmin + caja.width / 2
        tamano = caja.width * SEG_FACTOR_CARA_A_HOMBROS
        return centro_x, tamano, ((caja.xmin, caja.ymin),
                                  (caja.xmin + caja.width, caja.ymin + caja.height))
    return None


def _bucle_modo_seguimiento():
    """
    Corre en su propio hilo: abre la cámara, te detecta y manda letras al ESP32.

    El carro NO gira "hasta centrarte" (así se quedaba dando vueltas). Trabaja
    por PULSOS, en este ciclo:
        1) Mira dónde estás.
        2) Si estás de lado: gira un ratito (máx. ~20°) y se queda quieto un momento.
        3) Si estás lejos: AVANZA un tramo.
        4) Vuelve al paso 1.
    Si te acercas lo suficiente, se para. Si no te ve, se para.

    La imagen en pantalla se ve como espejo (SEG_ESPEJAR_VISTA), pero la lógica
    de giro usa la imagen real de la cámara.
    Teclas en la ventana:  C = calibrar la distancia ideal,  Q = salir.
    """
    NOMBRES = {"W": "AVANZANDO", "A": "GIRANDO A LA IZQUIERDA",
               "D": "GIRANDO A LA DERECHA", "X": "PARADO"}

    pose = mp.solutions.pose.Pose(
        static_image_mode=False, model_complexity=0,
        min_detection_confidence=0.5, min_tracking_confidence=0.5)
    cara = mp.solutions.face_detection.FaceDetection(
        model_selection=1, min_detection_confidence=0.6)

    cap = cv2.VideoCapture(SEG_INDICE_CAMARA, cv2.CAP_DSHOW)   # rápido en Windows
    if not cap.isOpened():
        cap = cv2.VideoCapture(SEG_INDICE_CAMARA)
    if not cap.isOpened():
        hablar("No pude abrir la cámara para el modo seguimiento.")
        detener_seguimiento_evento.clear()
        return
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    objetivo = SEG_TAMANO_OBJETIVO
    centro_suave = None
    tamano_suave = None
    frames_sin_persona = 0

    fase = "decidir"          # decidir | girando | esperando | avanzando
    fase_fin = 0.0            # cuándo termina la fase actual
    letra_fase = "X"
    giros_seguidos = 0
    ultimo_giro = 0.0
    grados_giro = 0.0         # solo para mostrar en pantalla
    ultimo_envio = 0.0

    while not detener_seguimiento_evento.is_set():
        ok, frame = cap.read()
        if not ok:
            break

        # La lógica usa la imagen REAL (sin espejo); el espejo es solo visual.
        alto, ancho = frame.shape[:2]
        chico = cv2.resize(frame, (SEG_ANCHO_PROCESAMIENTO,
                                   int(alto * SEG_ANCHO_PROCESAMIENTO / ancho)))
        deteccion = _detectar_persona(cv2.cvtColor(chico, cv2.COLOR_BGR2RGB), pose, cara)
        ahora = time.time()

        # ----------------- Medir (con suavizado) -----------------
        if deteccion is None:
            frames_sin_persona += 1
        else:
            frames_sin_persona = 0
            centro_x, tamano, puntos = deteccion
            if centro_suave is None:
                centro_suave, tamano_suave = centro_x, tamano
            else:
                centro_suave += SEG_SUAVIZADO * (centro_x - centro_suave)
                tamano_suave += SEG_SUAVIZADO * (tamano - tamano_suave)

            p1, p2 = puntos
            cv2.rectangle(frame, (int(p1[0] * ancho), int(p1[1] * alto)),
                          (int(p2[0] * ancho), int(p2[1] * alto)), (0, 255, 0), 2)
            cv2.circle(frame, (int(centro_suave * ancho), alto // 2), 8, (0, 255, 255), -1)

        perdido = frames_sin_persona >= SEG_FRAMES_PERDIDO

        # ----------------- Máquina de estados por pulsos -----------------
        if perdido:
            fase = "decidir"
            letra_fase = "X"
            centro_suave = tamano_suave = None
        else:
            # Terminar la fase actual si ya le tocó
            if fase == "girando" and ahora >= fase_fin:
                fase = "esperando"
                fase_fin = ahora + SEG_PAUSA_TRAS_GIRO
                centro_suave = tamano_suave = None     # volver a medir tras girar
            elif fase == "esperando" and ahora >= fase_fin:
                fase = "decidir"
            elif fase == "avanzando":
                llego = (tamano_suave is not None and
                         tamano_suave >= objetivo - SEG_TOLERANCIA_TAMANO_ALCANCE)
                if ahora >= fase_fin or llego:
                    fase = "decidir"

            # Decidir el siguiente pulso
            if fase == "decidir" and centro_suave is not None:
                if ahora - ultimo_giro > 1.5:
                    giros_seguidos = 0
                error_x = centro_suave - 0.5             # + = estás a la derecha de la imagen
                lejos = tamano_suave < objetivo - SEG_TOLERANCIA_TAMANO

                if abs(error_x) > SEG_TOLERANCIA_CENTRO and \
                        giros_seguidos < SEG_MAX_GIROS_SEGUIDOS:
                    # Girar un ratito (máx. ~20°), proporcional a qué tan de lado estés
                    grados_giro = min(abs(error_x) * SEG_FOV_HORIZONTAL,
                                      SEG_GRADOS_MAX_POR_GIRO)
                    duracion = max(SEG_GIRO_MIN_S, grados_giro / SEG_GRADOS_POR_SEGUNDO)
                    derecha = error_x > 0
                    if SEG_INVERTIR_GIRO:
                        derecha = not derecha
                    letra_fase = "D" if derecha else "A"
                    fase = "girando"
                    fase_fin = ahora + duracion
                    giros_seguidos += 1
                    ultimo_giro = ahora
                elif lejos:
                    # Ya giró (o estás centrado): avanzar un tramo hacia ti
                    letra_fase = "W"
                    fase = "avanzando"
                    fase_fin = ahora + SEG_AVANCE_S
                    giros_seguidos = 0
                else:
                    letra_fase = "X"                      # cerca / a buena distancia

        accion = letra_fase if fase in ("girando", "avanzando") else "X"

        # ----------------- Mandar al ESP32 (repetido) -----------------
        if ahora - ultimo_envio >= SEG_INTERVALO_ENVIO:
            _enviar_letra_esp32(accion)
            ultimo_envio = ahora

        # ----------------- Pantalla -----------------
        cx = ancho // 2
        zona = int(SEG_TOLERANCIA_CENTRO * ancho)
        cv2.line(frame, (cx - zona, 0), (cx - zona, alto), (255, 255, 255), 1)
        cv2.line(frame, (cx + zona, 0), (cx + zona, alto), (255, 255, 255), 1)

        if SEG_ESPEJAR_VISTA:
            frame = cv2.flip(frame, 1)     # solo visual; el texto se dibuja DESPUÉS

        color = (0, 255, 0) if accion == "X" else (0, 140, 255)
        texto = NOMBRES[accion]
        if fase == "girando":
            texto += f" (~{grados_giro:.0f} grados)"
        cv2.putText(frame, texto, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
        if tamano_suave is not None:
            cv2.putText(frame, f"tamano {tamano_suave:.2f} / objetivo {objetivo:.2f}",
                        (20, alto - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (255, 255, 255), 2, cv2.LINE_AA)
        elif perdido:
            cv2.putText(frame, "No te veo", (20, alto - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

        cv2.imshow("Modo seguimiento (C = calibrar, Q = salir)", frame)
        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord('q'):
            break
        if tecla == ord('c') and tamano_suave is not None:
            objetivo = tamano_suave
            fase = "decidir"
            print(f"[Distancia calibrada: objetivo = {objetivo:.2f}]")
            _enviar("info", "Distancia calibrada.")

    _enviar_letra_esp32("X")                  # al salir, frenar el carro real
    cap.release()
    cv2.destroyAllWindows()
    pose.close()
    cara.close()
    detener_seguimiento_evento.clear()
    _enviar("info", "Modo seguimiento apagado.")


def activar_modo_seguimiento():
    """Enciende el modo seguimiento. Si ya está encendido, no hace nada."""
    global hilo_seguimiento
    if not HAY_VISION:
        hablar("Para el modo seguimiento necesito opencv y mediapipe. "
               "Instálalos con: pip install opencv-python mediapipe")
        return
    if hilo_seguimiento and hilo_seguimiento.is_alive():
        hablar("El modo seguimiento ya está encendido.")
        return
    if hilo_carro and hilo_carro.is_alive():
        hablar("Primero apaga el modo carro.")
        return
    if hilo_control and hilo_control.is_alive():
        hablar("Primero apaga el modo control.")
        return
    detener_seguimiento_evento.clear()
    hablar("Modo seguimiento activado. Párate a la distancia que quieres y "
           "presiona C en la ventana para calibrar.")
    hilo_seguimiento = threading.Thread(target=_bucle_modo_seguimiento, daemon=True)
    hilo_seguimiento.start()


def detener_modo_seguimiento():
    """Apaga el modo seguimiento si está encendido."""
    if hilo_seguimiento and hilo_seguimiento.is_alive():
        detener_seguimiento_evento.set()
        hablar("Modo seguimiento desactivado.")
    else:
        hablar("El modo seguimiento no está encendido.")


# ---------------------------------------------------------------------------
# Cerebro: decide qué hacer según la orden
# ---------------------------------------------------------------------------
def procesar(comando):
    """
    Ejecuta la orden recibida. El orden de los 'if' importa:
    primero lo más específico, al final lo más general.
    Devuelve False si hay que apagar el asistente, True para seguir.
    """

    # ---- Salir (despedirse APAGA el programa) ----
    if tiene_frase(comando, ("adiós", "adios", "hasta luego", "hasta pronto",
                             "hasta mañana", "hasta manana", "nos vemos",
                             "me voy", "ya me voy", "apágate", "apagate")) or \
       tiene_palabra(comando, ("terminar", "termina", "ciérrate", "cierrate",
                               "chao", "chau", "chaucito", "bye")):
        return False

    # ---- Modo seguimiento: apagar (ANTES de pausar y de encender) ----
    elif tiene_frase(comando, ("para el seguimiento", "detén el seguimiento",
                               "deten el seguimiento", "apaga el seguimiento",
                               "desactiva el seguimiento", "deja de seguirme",
                               "salir del seguimiento", "sal del seguimiento")):
        detener_modo_seguimiento()

    # ---- Modo seguimiento: encender ("sígueme" va aquí, antes de la palabra
    # "sigue" del bloque de pausa) ----
    elif tiene_frase(comando, ("modo seguimiento", "activa el seguimiento",
                               "enciende el seguimiento", "prende el seguimiento",
                               "activar seguimiento", "sígueme", "sigueme",
                               "siguéme")):
        activar_modo_seguimiento()

    # ---- Modo control: apagar (ANTES de pausar, porque "detén" es palabra
    # de pausa, y ANTES de encender, para que "para el control" no dispare
    # la palabra "control" del comando de encendido) ----
    elif tiene_frase(comando, ("para el control", "detén el control", "deten el control",
                               "apaga el control", "desactiva el control",
                               "salir del control", "sal del control")):
        detener_modo_control()

    # ---- Modo control: encender ----
    elif tiene_frase(comando, ("modo control", "activa el control",
                               "enciende el control", "prende el control",
                               "activar control")):
        activar_modo_control()

    # ---- Modo carro: apagar (va ANTES de encender, para que "para el carro"
    # no dispare la palabra "carro" del comando de encendido) ----
    elif tiene_frase(comando, ("para el carro", "detén el carro", "deten el carro",
                               "apaga el carro", "desactiva el carro",
                               "detener carro", "para carro")):
        detener_modo_carro()

    # ---- Modo carro: encender ----
    elif tiene_frase(comando, ("activa el carro", "modo carro", "enciende el carro",
                               "prende el carro", "activar carro")):
        activar_modo_carro()

    # ---- Pausar / reanudar ----  (play y pausa son la misma tecla: alterna)
    elif tiene_palabra(comando, ("pausa", "pausar", "pausala", "pausalo",
                                 "páusala", "detente", "detén", "deten",
                                 "reanuda", "reanudar", "continúa", "continua",
                                 "sigue", "play", "alto", "stop")):
        if tecla_media("playpause"):
            hablar("Listo")

    # ---- Siguiente canción / video ----
    elif tiene_palabra(comando, ("siguiente", "próxima", "proxima", "salta",
                                 "sáltala", "saltala", "otra", "adelante")):
        if tecla_media("nexttrack"):
            hablar("Siguiente")

    # ---- Canción / video anterior ----
    elif tiene_palabra(comando, ("anterior", "regresa", "previa", "atrás",
                                 "atras")):
        if tecla_media("prevtrack"):
            hablar("Anterior")

    # ---- Silenciar ----
    elif tiene_palabra(comando, ("silencio", "silencia", "mutea", "mute")) or \
            tiene_frase(comando, ("quita el sonido", "sin sonido")):
        if tecla_media("volumemute"):
            hablar("Silencio")

    # ---- Subir volumen ----  (presiona varias veces para que se note)
    elif tiene_palabra(comando, ("sube", "súbele", "subele", "subir")) or \
            tiene_frase(comando, ("más fuerte", "mas fuerte", "más alto",
                                  "mas alto", "más volumen", "mas volumen")):
        if tecla_media("volumeup", veces=5):
            hablar("Subiendo el volumen")

    # ---- Bajar volumen ----
    elif tiene_palabra(comando, ("baja", "bájale", "bajale", "bajar")) or \
            tiene_frase(comando, ("más bajo", "mas bajo", "menos volumen",
                                  "más bajito", "mas bajito")):
        if tecla_media("volumedown", veces=5):
            hablar("Bajando el volumen")

    # ---- Abrir páginas ----  (va antes de reproducir/buscar)
    elif tiene_palabra(comando, ("abre", "abrir", "ábreme", "abreme", "abra")):
        objetivo = extraer(comando, ["abre", "abrir", "ábreme", "abreme", "abra",
                                     "la página de", "la pagina de", "la página",
                                     "la pagina", "página", "pagina", "el sitio de",
                                     "por favor", "la", "el"])
        if not objetivo:
            hablar("¿Qué quieres que abra?")
        elif objetivo in SITIOS:
            hablar(f"Abriendo {objetivo}")
            webbrowser.open(SITIOS[objetivo])
        elif "." in objetivo:
            url = objetivo if objetivo.startswith("http") else "https://" + objetivo
            hablar(f"Abriendo {objetivo}")
            webbrowser.open(url.replace(" ", ""))
        else:
            hablar(f"No conozco {objetivo}, lo busco en Google")
            buscar_en_google(objetivo)

    # ---- Reproducir en YouTube ----
    elif tiene_palabra(comando, ("reproduce", "reproducir", "pon", "ponme",
                                 "pónme", "música", "musica", "canción",
                                 "cancion", "video", "videos")) or \
            tiene_frase(comando, ("quiero escuchar", "quiero ver")):
        consulta = extraer(comando,
                           ["reproduce", "reproducir", "ponme", "pónme", "pon",
                            "música de", "musica de", "música", "musica",
                            "canción de", "cancion de", "canción", "cancion",
                            "el video de", "video de", "videos de", "video", "videos",
                            "quiero escuchar", "quiero ver", "en youtube", "youtube",
                            "una", "un", "el", "la", "de"])
        if consulta:
            hablar(f"Reproduciendo {consulta}")
            reproducir_youtube(consulta)
        else:
            hablar("¿Qué quieres que reproduzca?")

    # ---- Buscar en Google ----
    elif tiene_palabra(comando, ("busca", "buscar", "búscame", "buscame",
                                 "investiga", "googlea")) or \
            tiene_frase(comando, ("en google", "en internet")):
        consulta = extraer(comando,
                           ["búscame", "buscame", "buscar", "busca", "googlea",
                            "investiga", "en google", "en internet",
                            "información sobre", "informacion sobre", "por favor"])
        if consulta:
            hablar(f"Buscando {consulta}")
            buscar_en_google(consulta)
        else:
            hablar("¿Qué quieres que busque?")

    # ---- Hora ----
    elif tiene_palabra(comando, ("hora", "horas")):
        ahora = datetime.datetime.now().strftime("%I:%M %p").lstrip("0")
        hablar(f"Son las {ahora}")

    # ---- Fecha ----
    elif tiene_palabra(comando, ("fecha", "día", "dia", "días", "dias")) or \
            tiene_frase(comando, ("qué día", "que dia")):
        hoy = datetime.datetime.now().strftime("%A %d de %B de %Y")
        hablar(f"Hoy es {hoy}")

    # ---- Preguntas tipo enciclopedia ----
    elif tiene_frase(comando, ("quién es", "quien es", "quién fue", "quien fue",
                               "quién era", "quien era", "qué es", "que es",
                               "qué son", "que son", "qué significa",
                               "que significa", "información de", "informacion de",
                               "dime sobre", "háblame de", "hablame de",
                               "cuéntame de", "cuentame de")) or \
            tiene_palabra(comando, ("define",)):
        consulta = extraer(comando,
                           ["quién es", "quien es", "quién fue", "quien fue",
                            "quién era", "quien era", "qué es", "que es",
                            "qué son", "que son", "qué significa", "que significa",
                            "información de", "informacion de", "dime sobre",
                            "háblame de", "hablame de", "cuéntame de", "cuentame de",
                            "define"])
        # La IA responde mejor que Wikipedia; Wikipedia queda como respaldo
        responder_inteligente(comando, consulta_wiki=consulta)

    # ---- Charla básica ----
    elif tiene_frase(comando, ("cómo te llamas", "como te llamas", "tu nombre",
                               "quién eres", "quien eres")):
        hablar(f"Me llamo {NOMBRE}")
    elif tiene_frase(comando, ("cómo estás", "como estas", "qué tal", "que tal")):
        hablar("Muy bien, ¿en qué te ayudo?")
    elif tiene_palabra(comando, ("hola", "buenas", "hey")):
        hablar("Hola, ¿en qué te ayudo?")
    elif tiene_palabra(comando, ("gracias",)):
        hablar("Con gusto")

    # ---- Cualquier otra cosa: que responda la IA (conversación natural) ----
    else:
        responder_inteligente(comando)

    return True


# ---------------------------------------------------------------------------
# Bucle del asistente (corre en un hilo de fondo para no congelar la ventana)
# ---------------------------------------------------------------------------
def bucle_asistente(reconocedor, microfono):
    _enviar("info", "Calibrando micrófono (silencio por favor)...")
    _enviar("estado", "Calibrando")
    with microfono as fuente:
        reconocedor.adjust_for_ambient_noise(fuente, duration=1)
    if reconocedor.energy_threshold > SENSIBILIDAD:
        reconocedor.energy_threshold = SENSIBILIDAD

    ruta_intro = _ruta_intro()
    if ruta_intro:
        _enviar("siri", "🎵 (intro del meme)")
        _enviar("estado", "Hablando")
        if not _reproducir_audio(ruta_intro):
            hablar(SALUDO)          # si el audio falla, usa la voz
    else:
        hablar(SALUDO)

    while not detener_evento.is_set():

        # ----- ESTADO DORMIDO: espera la palabra de activación -----
        _enviar("estado", "Dormido")
        # espera=2 para revisar a menudo si pediste apagar o activar (botón)
        disparo = escuchar(reconocedor, microfono, espera=2, max_frase=4,
                           idioma=IDIOMA_ACTIVACION)

        desperto = False
        if activar_evento.is_set():        # clic en la bolita
            activar_evento.clear()
            desperto = True
        elif disparo and any(d in disparo for d in DISPARADORES):
            desperto = True
        if not desperto:
            continue

        # ----- ESTADO DESPIERTO: conversación de corrido -----
        hablar("Te escucho")
        while not detener_evento.is_set():
            _enviar("estado", "Escuchando")
            comando = escuchar_comando(reconocedor, microfono,
                                       espera=TIEMPO_INACTIVO)

            # Silencio prolongado -> volver a dormir
            if comando is None:
                hablar("Me voy a dormir. Llámame cuando me necesites.")
                break

            # Quitar un "hey siri" suelto por si lo repites dentro de la charla
            for d in DISPARADORES:
                comando = comando.replace(d, "")
            comando = comando.strip()

            if not comando:
                hablar("No te entendí, ¿puedes repetir?")
                continue

            _enviar("yo", comando)
            _enviar("estado", "Pensando")
            # procesar() devuelve False con palabras de salida (adiós/apágate)
            if not procesar(comando):
                detener_evento.set()
                break

    hablar("Adiós, que estés muy bien.")
    _enviar("estado", "Apagado")


# ---------------------------------------------------------------------------
# Ventana (interfaz gráfica con Tkinter)
# ---------------------------------------------------------------------------
COLORES_ESTADO = {
    "Dormido":   "#6e7681",
    "Calibrando": "#d29922",
    "Escuchando": "#3fb950",
    "Hablando":  "#58a6ff",
    "Pensando":  "#d29922",
    "Apagado":   "#f85149",
}


# Paleta de colores de la bolita (estilo Siri: rosados, morados, azules, cian)
PALETA_ORBE = ["#ff4f8b", "#b14bff", "#7a5cff", "#4f8bff", "#36e0ff"]
COLOR_TRANSP = "#010207"   # color que se vuelve transparente (en Windows)
COLOR_FONDO = "#0d1117"    # fondo si la transparencia no está disponible


def _mezcla(c1, c2, t):
    """Mezcla dos colores hex (#rrggbb) según t (0..1)."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    m = [round(a[i] + (b[i] - a[i]) * t) for i in range(3)]
    return f"#{m[0]:02x}{m[1]:02x}{m[2]:02x}"


class InterfazSiri:
    """Ventana de chat estilo ChatGPT: clara, con burbujas, micrófono y enviar."""

    BG = "#ffffff"
    BG_USUARIO = "#e8e8ea"
    TXT = "#0d0d0d"
    FUENTE = ("Segoe UI", 11)

    def __init__(self, root, reconocedor, microfono):
        self.root = root
        self.reconocedor = reconocedor
        self.microfono = microfono
        self.hilo = None
        self.wrap = 360
        self._chips_siri = None
        self.ventana_control = None       # ventanita del modo control (teclado)
        self._placeholder = "Escribe un mensaje o pulsa el micrófono…"

        root.title(NOMBRE)
        root.geometry("480x700")
        root.configure(bg=self.BG)
        root.minsize(360, 480)

        # --- Encabezado ---
        cab = tk.Frame(root, bg=self.BG, height=52)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text=NOMBRE, font=("Segoe UI", 16, "bold"),
                 fg=self.TXT, bg=self.BG).pack(side="left", padx=18)
        self.lbl_estado = tk.Label(cab, text="💤 Dormida", font=("Segoe UI", 10),
                                   fg="#8a8a8a", bg=self.BG)
        self.lbl_estado.pack(side="right", padx=18)
        tk.Frame(root, bg="#ececf0", height=1).pack(fill="x")

        # --- Área de chat (con scroll) ---
        cont = tk.Frame(root, bg=self.BG)
        cont.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(cont, bg=self.BG, highlightthickness=0)
        sb = tk.Scrollbar(cont, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=self.BG)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._ajustar_ancho)
        self.canvas.bind_all("<MouseWheel>", self._rueda)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        # --- Barra de entrada (abajo) ---
        tk.Frame(root, bg="#ececf0", height=1).pack(fill="x")
        barra = tk.Frame(root, bg=self.BG)
        barra.pack(fill="x", padx=12, pady=10)
        caja = tk.Frame(barra, bg="#f3f3f5")
        caja.pack(fill="x")
        self.entrada = tk.Entry(caja, font=self.FUENTE, bg="#f3f3f5", fg="#9a9a9a",
                                relief="flat", insertbackground=self.TXT)
        self.entrada.insert(0, self._placeholder)
        self.entrada.pack(side="left", fill="x", expand=True, ipady=10, padx=(14, 6))
        self.entrada.bind("<FocusIn>", self._quitar_placeholder)
        self.entrada.bind("<FocusOut>", self._poner_placeholder)
        self.entrada.bind("<Return>", self.enviar_texto)
        self.btn_mic = tk.Button(caja, text="🎤", command=self.pulsar_hablar,
                                 font=("Segoe UI", 13), bg="#f3f3f5", fg="#444",
                                 relief="flat", cursor="hand2", bd=0)
        self.btn_mic.pack(side="left", padx=(0, 4))
        tk.Button(caja, text="➤", command=self.enviar_texto,
                  font=("Segoe UI", 13, "bold"), bg="#10a37f", fg="white",
                  relief="flat", cursor="hand2", bd=0, padx=12, pady=4
                  ).pack(side="right", padx=4, pady=4)
        self.btn_voz = tk.Button(barra, text="Pausar escucha", command=self.alternar_voz,
                                 font=("Segoe UI", 9), bg=self.BG, fg="#8a8a8a",
                                 relief="flat", cursor="hand2", bd=0)
        self.btn_voz.pack(anchor="e", pady=(6, 0))

        root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.root.after(100, self.revisar_cola)
        self.iniciar_voz()

    # ----- scroll y ancho -----
    def _ajustar_ancho(self, e):
        self.canvas.itemconfig(self._win, width=e.width)
        self.wrap = max(180, e.width - 120)

    def _rueda(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def _scroll_fin(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(1.0)

    # ----- placeholder del cuadro de texto -----
    def _quitar_placeholder(self, e=None):
        if self.entrada.get() == self._placeholder:
            self.entrada.delete(0, "end")
            self.entrada.config(fg=self.TXT)

    def _poner_placeholder(self, e=None):
        if not self.entrada.get().strip():
            self.entrada.delete(0, "end")
            self.entrada.insert(0, self._placeholder)
            self.entrada.config(fg="#9a9a9a")

    # ----- cola de mensajes desde el asistente -----
    def revisar_cola(self):
        try:
            while True:
                tipo, dato = cola_gui.get_nowait()
                if tipo == "estado":
                    self.set_estado(dato)
                elif tipo == "siri":
                    self.agregar(dato, "siri")
                elif tipo == "yo":
                    self.agregar(dato, "user")
                elif tipo == "fuente":
                    self.agregar_fuente(dato)
                elif tipo == "info":
                    self.agregar_info(dato)
                elif tipo == "control":
                    if dato == "abrir":
                        self.abrir_control()
                    else:
                        self.cerrar_control()
        except queue.Empty:
            pass
        self.root.after(100, self.revisar_cola)

    def set_estado(self, estado):
        textos = {"Dormido": "💤 Dormida", "Calibrando": "⏳ Preparando…",
                  "Escuchando": "🎤 Te escucho…", "Hablando": "🔊 Hablando…",
                  "Pensando": "💭 Pensando…", "Apagado": "⏹ Apagada"}
        self.lbl_estado.config(text=textos.get(estado, estado),
                               fg=COLORES_ESTADO.get(estado, "#8a8a8a"))

    # ----- pintar mensajes -----
    def agregar(self, texto, who):
        fila = tk.Frame(self.inner, bg=self.BG)
        fila.pack(fill="x", padx=14, pady=(6, 2))
        if who == "user":
            tk.Label(fila, text=texto, bg=self.BG_USUARIO, fg=self.TXT,
                     wraplength=self.wrap, justify="left", font=self.FUENTE,
                     padx=14, pady=9).pack(side="right")
            self._chips_siri = None
        else:
            bloque = tk.Frame(fila, bg=self.BG)
            bloque.pack(side="left", fill="x")
            tk.Label(bloque, text=texto, bg=self.BG, fg=self.TXT,
                     wraplength=self.wrap, justify="left", font=self.FUENTE
                     ).pack(anchor="w")
            chips = tk.Frame(bloque, bg=self.BG)
            chips.pack(anchor="w", pady=(3, 0))
            self._chips_siri = chips
        self._scroll_fin()

    def agregar_info(self, texto):
        fila = tk.Frame(self.inner, bg=self.BG)
        fila.pack(fill="x", pady=4)
        tk.Label(fila, text=texto, bg=self.BG, fg="#9a9a9a",
                 font=("Segoe UI", 9, "italic"), wraplength=self.wrap).pack()
        self._scroll_fin()

    def agregar_fuente(self, url):
        if not self._chips_siri:
            return
        dom = urllib.parse.urlparse(url).netloc.replace("www.", "") or url[:30]
        chip = tk.Label(self._chips_siri, text=dom, bg="#eef0f2", fg="#3a6df0",
                        font=("Segoe UI", 8), padx=8, pady=2, cursor="hand2")
        chip.pack(side="left", padx=(0, 5))
        chip.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        self._scroll_fin()

    # ----- modo control: ventanita que captura W/A/S/D -----
    def abrir_control(self):
        if self.ventana_control and self.ventana_control.winfo_exists():
            self.ventana_control.lift()
            self.ventana_control.focus_force()
            return
        v = tk.Toplevel(self.root)
        v.title("Modo control")
        v.geometry("300x420")
        v.configure(bg=self.BG)
        tk.Label(v, text="W  adelante\nS  atrás\nA  izquierda\nD  derecha",
                 font=("Segoe UI", 12), bg=self.BG, fg=self.TXT,
                 justify="left").pack(pady=(18, 6))
        tk.Label(v, text="Deja ESTA ventana en primer plano\n"
                         "(si haces clic en otra, el carro frena)",
                 font=("Segoe UI", 9), bg=self.BG, fg="#8a8a8a").pack()

        def presionar(e):
            k = e.keysym.lower()
            if k in ("w", "a", "s", "d") and k not in teclas_control:
                teclas_control.append(k)

        def soltar(e):
            k = e.keysym.lower()
            if k in teclas_control:
                teclas_control.remove(k)

        # ----- Cruceta en pantalla (como los controles del celular) -----
        # Mantén presionado un botón = el carro se mueve; suelta = frena.
        # Funciona igual que las teclas W/A/S/D (y se pueden usar las dos).
        def press_btn(k):
            if k not in teclas_control:
                teclas_control.append(k)

        def release_btn(k):
            if k in teclas_control:
                teclas_control.remove(k)

        pad = tk.Frame(v, bg=self.BG)
        pad.pack(pady=(14, 10))
        botones = {
            "w": ("▲", 0, 1),
            "a": ("◀", 1, 0),
            "s": ("▼", 1, 1),
            "d": ("▶", 1, 2),
        }
        for k, (simbolo, fila, col) in botones.items():
            b = tk.Button(pad, text=simbolo, font=("Segoe UI", 22, "bold"),
                          width=3, height=1, bg="#e8e8ea", fg=self.TXT,
                          activebackground="#10a37f", activeforeground="white",
                          relief="raised", bd=2, cursor="hand2", takefocus=0)
            b.grid(row=fila, column=col, padx=5, pady=5)
            b.bind("<ButtonPress-1>", lambda e, k=k: press_btn(k))
            b.bind("<ButtonRelease-1>", lambda e, k=k: release_btn(k))
            b.bind("<Leave>", lambda e, k=k: release_btn(k))   # si arrastras fuera, frena

        v.bind("<KeyPress>", presionar)
        v.bind("<KeyRelease>", soltar)

        # Si la ventana pierde el foco (clic en otra ventana), soltar todo.
        # Se revisa un instante después para no soltar al pulsar los botones.
        def _perdio_foco(e):
            v.after(80, lambda: teclas_control.clear()
                    if v.winfo_exists() and v.focus_displayof() is None else None)
        v.bind("<FocusOut>", _perdio_foco)
        v.protocol("WM_DELETE_WINDOW", self.cerrar_control)
        v.focus_force()
        self.ventana_control = v

    def cerrar_control(self):
        detener_control_evento.set()
        teclas_control.clear()
        if self.ventana_control and self.ventana_control.winfo_exists():
            self.ventana_control.destroy()
        self.ventana_control = None

    # ----- acciones -----
    def enviar_texto(self, evento=None):
        texto = self.entrada.get().strip()
        if not texto or texto == self._placeholder:
            return
        self.entrada.delete(0, "end")
        _enviar("yo", texto)
        _enviar("estado", "Pensando")
        threading.Thread(target=self._procesar_escrito, args=(texto,),
                         daemon=True).start()

    def _procesar_escrito(self, texto):
        for d in DISPARADORES:
            texto = texto.replace(d, "")
        texto = texto.strip()
        if texto and not procesar(texto):
            detener_evento.set()

    def pulsar_hablar(self):
        """Micrófono: activa la escucha de inmediato (en simultáneo con la voz)."""
        if not (self.hilo and self.hilo.is_alive()):
            self.iniciar_voz()
        activar_evento.set()

    def iniciar_voz(self):
        if self.hilo and self.hilo.is_alive():
            return
        detener_evento.clear()
        self.hilo = threading.Thread(
            target=bucle_asistente, args=(self.reconocedor, self.microfono),
            daemon=True)
        self.hilo.start()
        self.btn_voz.config(text="Pausar escucha")

    def alternar_voz(self):
        if self.hilo and self.hilo.is_alive():
            detener_evento.set()
            self.btn_voz.config(text="Reanudar escucha")
            self.set_estado("Apagado")
        else:
            self.iniciar_voz()

    def cerrar(self):
        detener_evento.set()
        detener_carro_evento.set()
        detener_control_evento.set()
        detener_seguimiento_evento.set()
        _enviar_letra_esp32("X")          # frenar el carro real al cerrar
        self.root.after(200, self.root.destroy)


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main():
    global VOZ_ID

    reconocedor = sr.Recognizer()
    reconocedor.pause_threshold = PAUSA_FINAL     # espera este silencio antes de cortar
    reconocedor.dynamic_energy_threshold = True  # se adapta al ruido del ambiente
    reconocedor.energy_threshold = SENSIBILIDAD  # umbral base (menor = más sensible)

    microfono = sr.Microphone()
    VOZ_ID = elegir_voz()                        # detecta la voz en español una vez

    print("Abriendo la ventana del asistente...")
    if HAY_IA:
        print(f"Cerebro de IA (Groq): ACTIVO ({MODELO_IA})")
    else:
        print("Cerebro de IA (Groq): APAGADO (sin clave; solo comandos fijos)")
    if HAY_VISION:
        print("Modos carro (gestos), control (teclado) y seguimiento (te sigue): DISPONIBLES")
    else:
        print("Modos carro / control / seguimiento: APAGADOS (falta opencv-python y/o mediapipe)")
    if HAY_ESP32:
        print(f"LEDs del ESP32: ACTIVOS ({PUERTO_ESP32})")
    else:
        print("LEDs del ESP32: APAGADOS (revisa PUERTO_ESP32 o instala pyserial)")

    root = tk.Tk()
    InterfazSiri(root, reconocedor, microfono)
    root.mainloop()
    detener_evento.set()
    detener_carro_evento.set()
    detener_control_evento.set()
    detener_seguimiento_evento.set()
    if esp32:
        try:
            esp32.write(b"X")
            esp32.close()
        except Exception:
            pass
    print("\nAsistente apagado.")


if __name__ == "__main__":
    main()

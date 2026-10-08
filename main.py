"""
main.py
===================
Va en el ESP32 (guárdalo como 'main.py' para que corra solo al encender la
placa, o súbelo con Thonny y dale Run).

Escucha el puerto serie (el mismo cable USB) esperando UNA letra:

    'W' -> ADELANTE     -> motores adelante  + enciende LED de arriba
    'S' -> ATRÁS        -> motores en reversa + enciende LED de abajo
    'A' -> IZQUIERDA    -> gira sobre sí mismo + enciende LED izquierdo
    'D' -> DERECHA      -> gira sobre sí mismo + enciende LED derecho
    'X' -> STOP         -> detiene motores y apaga LEDs

Cualquier otra tecla no reconocida también detiene todo.

SEGURIDAD (timeout): si pasan TIMEOUT_MS milisegundos sin recibir NINGUNA
letra de movimiento, el carro se detiene solo. Así, si se cierra el programa
de la PC o se desconecta el cable, el carro no se queda andando.

  - Modo control (teclado): la PC repite la letra cada 100 ms mientras
    mantienes la tecla, así que el carro se mueve de corrido y frena al soltar.
  - Modo carro (cámara): manda UNA letra por gesto, así que cada gesto mueve
    el carro durante TIMEOUT_MS. Súbelo si quieres movimientos más largos.

IMPORTANTE: si usas Thonny para subir este archivo, luego CIERRA la
conexión de Thonny con la placa (botón de "Stop/desconectar" o cierra
Thonny) antes de correr el script de Python en tu PC. El puerto serie
solo lo puede usar UN programa a la vez.

Cambia los números de pin según cómo conectaste tus LEDs y el módulo L9110.
"""

from machine import Pin
import sys
import select
import utime

PAUSA_FRENADO_MS = 80   # cuánto dura el "stop" entre una acción y otra
TIMEOUT_MS = 350        # sin letras durante este tiempo -> frena solo

# ----- Pines de los 4 LEDs (AJUSTA a tu cableado) -----
leds = {
    "U": Pin(4, Pin.OUT),   # ARRIBA
    "L": Pin(18, Pin.OUT),  # IZQUIERDA
    "R": Pin(19, Pin.OUT),  # DERECHA
    "B": Pin(21, Pin.OUT),  # ABAJO
}

# ----- Pines del módulo L9110 (AJUSTA a tu cableado) -----
# Cada motor usa 2 pines: IA e IB. Un canal en HIGH y el otro en LOW
# hace girar el motor en un sentido; invertido, gira al revés.
# Los dos en LOW = motor detenido.
motor_izq_ia = Pin(25, Pin.OUT)  # A-IA
motor_izq_ib = Pin(26, Pin.OUT)  # A-IB
motor_der_ia = Pin(27, Pin.OUT)  # B-IA
motor_der_ib = Pin(14, Pin.OUT)  # B-IB


def motor_izquierdo(sentido):
    # sentido: 1 = adelante, -1 = atrás, 0 = detenido
    motor_izq_ia.value(1 if sentido == 1 else 0)
    motor_izq_ib.value(1 if sentido == -1 else 0)


def motor_derecho(sentido):
    motor_der_ia.value(1 if sentido == 1 else 0)
    motor_der_ib.value(1 if sentido == -1 else 0)


def detener_motores():
    motor_izquierdo(0)
    motor_derecho(0)


def apagar_leds():
    for led in leds.values():
        led.value(0)


def encender_led(clave):
    for k, led in leds.items():
        led.value(1 if k == clave else 0)


def parar_todo():
    detener_motores()
    apagar_leds()


# Cada letra de movimiento define (sentido_motor_izq, sentido_motor_der,
# clave_led_a_encender)
comandos_movimiento = {
    "W": (1, 1, "U"),    # adelante  -> motores adelante, LED de arriba
    "S": (-1, -1, "B"),  # atrás     -> motores en reversa, LED de abajo
    "A": (-1, 1, "L"),   # izquierda -> gira sobre sí mismo, LED izquierdo
    "D": (1, -1, "R"),   # derecha   -> gira sobre sí mismo, LED derecho
}

# Estado inicial: todo apagado / detenido
parar_todo()
estado_actual = None               # qué comando está activo ahora mismo (None = detenido)
ultimo_cmd = utime.ticks_ms()      # cuándo llegó la última letra de movimiento

# Para leer el puerto serie sin bloquear el programa (poll con timeout)
entrada = select.poll()
entrada.register(sys.stdin, select.POLLIN)

# (No se imprime nada por serie durante el funcionamiento: la PC no lee lo que
# manda el ESP32 y, con el tiempo, el búfer se podría llenar.)

while True:
    if entrada.poll(10):          # espera hasta 10 ms por datos
        caracter = sys.stdin.read(1).upper()

        if caracter in ("\n", "\r", ""):
            # ruido normal del puerto serie (Enter, línea vacía) -> ignorar,
            # NO apagar nada. Así una tecla sostenida no "parpadea".
            pass
        elif caracter in comandos_movimiento:
            ultimo_cmd = utime.ticks_ms()      # refresca el timeout (aunque sea la misma letra)
            if caracter != estado_actual:
                # cambio de acción real -> primero FRENAR por completo,
                # esperar un instante, y recién ahí aplicar la nueva acción.
                # Esto evita el pico de corriente de invertir el motor de golpe.
                parar_todo()
                utime.sleep_ms(PAUSA_FRENADO_MS)

                izq, der, led_clave = comandos_movimiento[caracter]
                motor_izquierdo(izq)
                motor_derecho(der)
                encender_led(led_clave)
                estado_actual = caracter
                ultimo_cmd = utime.ticks_ms()  # el sleep de arriba no debe gastar timeout
        else:
            # 'X' o cualquier otra tecla distinta -> detener todo
            parar_todo()
            estado_actual = None

    # ----- Seguridad: si dejaron de llegar letras, frenar solo -----
    if estado_actual is not None and \
            utime.ticks_diff(utime.ticks_ms(), ultimo_cmd) > TIMEOUT_MS:
        parar_todo()
        estado_actual = None

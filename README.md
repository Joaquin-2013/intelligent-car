# 🚗🎤 Siri Car: un asistente de voz que maneja un carro

> ¡Le hablas a tu compu y un carro de verdad se mueve! Sí, en serio. 😎

Hice un asistente de voz en español (le puse **Siri**) que:
- te escucha cuando dices **"just give me my money"** 💸
- te responde con voz (usa IA, así que no es tan tonto)
- abre YouTube, busca en Google, dice la hora, sube el volumen...
- y lo mejor: **controla un carrito con un ESP32** 🤖

---

## 🧠 ¿Cómo funciona?

```
 Tú (voz / teclado / mano / cámara)
            │
            ▼
   💻 Python en tu compu  (asistente.py)
            │   manda una letra por el cable USB
            ▼
   🔌 ESP32 con MicroPython (esp32/main.py)
            │
            ▼
   🚗 Motores (L9110) + 💡 LEDs
```

Las letras que entiende el carro:

| Letra | Qué hace |
|:-----:|----------|
| `W` | Adelante ⬆️ |
| `S` | Atrás ⬇️ |
| `A` | Izquierda ⬅️ |
| `D` | Derecha ➡️ |
| `X` | Pararse ✋ |

---

## 🎮 Los 3 modos del carro

1. **Modo carro** 🖐️: mueves la mano frente a la cámara y el carro se mueve.
   Di *"activa el carro"*. Para salir pon **las dos manos** o presiona `Q`.
2. **Modo control** ⌨️: lo manejas con las teclas **W A S D** (o con los botones en pantalla).
   Di *"modo control"*.
3. **Modo seguimiento** 🏃: la cámara te ve y el carro **te sigue**. Presiona `C` para calibrar la distancia.
   Di *"modo seguimiento"* o *"sígueme"*.

Hay un simulador con una calle y otros carros para chocar (tranqui, es virtual 💥).

---

## 🗣️ Cosas que le puedes decir

| Dices | Pasa |
|-------|------|
| "qué hora es" | te dice la hora |
| "qué día es" | te dice la fecha |
| "abre youtube" | abre la página |
| "busca gatos" | busca en Google |
| "pon música de queen" | la reproduce en YouTube |
| "pausa" / "siguiente" / "anterior" | controla la música |
| "sube el volumen" / "silencio" | controla el sonido |
| "quién es Einstein" | te responde con IA |
| "adiós" | se apaga |

También puedes escribirle en la ventana de chat 💬.

---

## 🛠️ Lo que necesitas

**Hardware:**
- Una placa **ESP32**
- Un módulo **L9110** + 2 motores
- 4 LEDs
- Un cable USB
- Una cámara web (para los modos de mano y seguimiento)

**Software:**
- Python 3.9 o más nuevo
- MicroPython en el ESP32
- Una clave gratis de **Groq** (la sacas en [console.groq.com](https://console.groq.com))

---

## 🚀 Cómo instalarlo (paso a paso)

### 1. Baja el proyecto
```bash
git clone https://github.com/TU_USUARIO/siri-car.git
cd siri-car
```

### 2. Instala las cosas de Python
```bash
pip install -r requirements.txt
```
Si `pyaudio` te da error:
- **Windows:** `pip install pipwin` y luego `pipwin install pyaudio`
- **Mac:** `brew install portaudio` y luego `pip install pyaudio`
- **Linux:** `sudo apt install portaudio19-dev python3-pyaudio espeak`

### 3. Sube el código al ESP32
Abre `esp32/main.py` con Thonny, guárdalo en la placa como **main.py**.
⚠️ Después **cierra Thonny**, porque el puerto USB solo lo puede usar un programa a la vez.

### 4. Pon tu clave de Groq (¡NUNCA en el código!)
- **Windows (PowerShell):** `setx GROQ_API_KEY "tu_clave_aqui"`
- **Mac / Linux:** `export GROQ_API_KEY="tu_clave_aqui"`

### 5. Cambia el puerto
En `asistente.py` busca esto y pon TU puerto:
```python
PUERTO_ESP32 = "COM8"
```
Para saber cuál es el tuyo: `python -m serial.tools.list_ports`

### 6. ¡A jugar!
```bash
python asistente.py
```

---

## 🔌 Conexiones (pines del ESP32)

| Cosa | Pin |
|------|-----|
| LED arriba | 4 |
| LED izquierda | 18 |
| LED derecha | 19 |
| LED abajo | 21 |
| Motor izq (IA / IB) | 25 / 26 |
| Motor der (IA / IB) | 27 / 14 |

Si conectaste distinto, cámbialos en `esp32/main.py`.

---

## 🛟 Seguridad

El ESP32 **frena solo** si pasan 350 ms sin recibir letras. Así, si se cierra el programa o se desconecta el cable, el carro no se va corriendo solo. 🙏

---

## 🐛 Problemas comunes

- **No conecta con el ESP32:** revisa `PUERTO_ESP32` y que Thonny esté cerrado.
- **No me escucha:** sube o baja `SENSIBILIDAD` en el código.
- **El carro gira al lado contrario:** pon `SEG_INVERTIR_GIRO = True`.
- **Gira de más o de menos en seguimiento:** ajusta `SEG_GRADOS_POR_SEGUNDO`.
- **No hay IA:** te falta la variable `GROQ_API_KEY`.

---

## 📁 Cómo está organizado

```
siri-car/
├── asistente.py        # el cerebro (Python, en tu compu)
├── esp32/
│   └── main.py         # el código del ESP32 (MicroPython)
├── requirements.txt    # las librerías
├── .gitignore
└── README.md           # este archivo
```

---

## 💡 Ideas para después

- [ ] Velocidad del carro con PWM
- [ ] Más comandos de voz
- [ ] Controlarlo desde el celular

---

Hecho con ❤️, mucho café y varios errores por **Joaquín**.
Si te gustó, ¡regálame una ⭐ en el repo!

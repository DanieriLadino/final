# Chef Manos Libres

Asistente multimodal de cocina: sigue una receta y vigila la cocina **sin tocar el celular**.
Une un ESP32 simulado en **Wokwi** con una app en **Streamlit** mediante **MQTT** (broker HiveMQ).

## 1. Correr la app

```bash
cd ~/Desktop/interfacess
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/streamlit run Inicio.py
```

Ábrela en **Google Chrome** (http://localhost:8501). Chrome es necesario para el micrófono.

## 2. Conectar el ESP32 de Wokwi

1. Entra a <https://wokwi.com> → *New project* → **ESP32**.
2. Reemplaza `sketch.ino` y `diagram.json` con los de la carpeta `wokwi/`.
3. Crea el archivo `libraries.txt` con el contenido de `wokwi/libraries.txt`.
4. Presiona ▶. El LCD dice "Conectando WiFi" y luego muestra el paso de la receta.
5. En la app, la barra lateral cambia a **ESP32 conectado**.

Deja la pestaña de Wokwi **visible**: si la escondes, el navegador la frena y la simulación
corre muy lento (los mensajes tardan en llegar).

En Wokwi: haz clic en el **DHT22** para cambiar la temperatura, gira la **perilla** (fogón)
y presiona los botones **SIGUIENTE** (verde) y **ATRÁS** (azul).

**Sin Wokwi:** activa **ESP32 simulado** en la barra lateral (o `./.venv/bin/python simulador_esp32.py`).
Imita al ESP32 por MQTT con LCD, LEDs, servo, botones y perilla. No lo uses a la vez que Wokwi.

## 3. Cómo se usa

| Modalidad | Cómo |
|---|---|
| Voz | Botón de micrófono, o **Manos libres** (escucha continua; se pausa sola mientras el chef habla) |
| Texto | Escribe el comando y presiona Enter |
| Botones en pantalla | Empezar, Atrás, Repetir, Siguiente, Temporizador |
| Botones físicos | SIGUIENTE / ATRÁS del ESP32 (llegan por MQTT) |
| Cámara | Foto del plato al terminar + calificación con estrellas (se guarda en `fotos/`) |

Salidas: voz (gTTS; si no hay internet usa la voz del navegador), paso en letra grande,
LCD 16x2, buzzer, LEDs, servo del extractor, métricas y gráficas en vivo.

Comandos de ejemplo: «quiero hacer arepas», «empezar», «siguiente», «atrás», «repite»,
«¿cuánta harina?», «pon el temporizador», «temporizador de un minuto y medio», «¿cuánto falta?»,
«cancela el temporizador», «enciende el extractor», «extractor en automático»,
«¿qué temperatura hay?», «umbral a 50 grados», «prueba el sonido», «ayuda».

## 4. MQTT

| Tópico | Sentido | JSON |
|---|---|---|
| `chefmanoslibres/grupo1/estado` | ESP32 → App, cada 2 s | temperatura, humedad, fogon, receta, paso, total, extractor, extractor_auto, alerta_temp, umbral, timer_restante |
| `chefmanoslibres/grupo1/evento` | ESP32 → App | tipo: siguiente, atras, timer_fin, alerta_temp, conectado |
| `chefmanoslibres/grupo1/cmd` | App → ESP32 | paso, total, texto, receta · timer (s, 0 cancela) · extractor · extractor_auto · umbral · buzzer · fin |

El broker es público: si otro grupo usa el mismo tópico, cámbialo en `config.py`
(o con la variable `CHEF_TOPICO`) **y** en `TOPICO_BASE` de `wokwi/sketch.ino`.

## 5. Archivos

| Archivo | Responsabilidad |
|---|---|
| `Inicio.py` | Página principal |
| `pages/1_🍳_Asistente_de_recetas.py` | Ambiente 1 |
| `pages/2_🌡️_Monitor_de_cocina.py` | Ambiente 2 |
| `mqtt_puente.py` | Cliente MQTT compartido, estado, historial (600) y eventos (100) |
| `cocina.py` | Lógica: receta, comandos, temporizador, eventos y alertas |
| `voz.py` | Intérprete de comandos y texto a voz |
| `ui.py` | Estética, barra lateral, voz de salida y micrófono |
| `componentes/microfono/` | Micrófono (Web Speech API, es-CO) |
| `recetas.py` | Recetas |
| `simulador_esp32.py` | Imita al ESP32 |
| `wokwi/` | Firmware, circuito y librerías |
| `test_interprete.py` | Pruebas del intérprete (`./.venv/bin/python test_interprete.py`) |

## 6. Fuentes

Poppins se carga de Google Fonts. El logo usa la **Nectarine** original extraída del PDF.
Si tienes el archivo de Nectarine, cópialo en `static/fonts/` y la app lo usa sola.

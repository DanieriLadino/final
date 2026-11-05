"""Chef Manos Libres — página de inicio.

Ejecutar:  streamlit run Inicio.py
"""
import streamlit as st

import config
import ui
from ui import icono, img_b64

ui.iniciar_pagina("inicio", "Inicio", "🐱")
ui.mostrar_voz()

# ---------------------------------------------------------------- portada
c1, c2 = st.columns([1, 1.6], vertical_alignment="center")
with c1:
    st.markdown('<img src="%s" style="width:100%%;max-width:330px;display:block;margin:auto">'
                % img_b64("static/img/gato.png"), unsafe_allow_html=True)
with c2:
    st.markdown('<img src="%s" style="width:100%%;max-width:560px" alt="Chef Manos Libres">'
                % img_b64("static/img/logo.png"), unsafe_allow_html=True)
    st.markdown('<p class="subtitulo" style="font-weight:500;font-size:1.35rem;margin-top:10px">'
                'Tus manos cocinan, tu voz guía</p>'
                '<p style="font-weight:200;font-size:1.1rem;max-width:520px">Sigue una receta y vigila la cocina '
                'sin tocar el celular: con tu voz, con texto, con botones en pantalla o con los botones '
                'físicos del ESP32.</p>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    b1.page_link("pages/1_🍳_Asistente_de_recetas.py", label="Asistente de recetas", icon="🍳",
                 use_container_width=True)
    b2.page_link("pages/2_🌡️_Monitor_de_cocina.py", label="Monitor de cocina", icon="🌡️",
                 use_container_width=True)

st.write("")

# ---------------------------------------------------------------- problema y objetivo
st.markdown("## Problema y objetivo")
c1, c2 = st.columns(2)
c1.markdown('<div class="blob-w"><div class="blob"><div class="h">El problema</div>'
            'Al cocinar con una receta en el celular las manos están sucias o mojadas. Hay que tocar '
            'la pantalla para avanzar, el celular se bloquea, se pierde el paso y se olvidan los tiempos.'
            '</div></div>', unsafe_allow_html=True)
c2.markdown('<div class="blob-w"><div class="blob"><div class="h">El objetivo</div>'
            'Una app multimodal que guía la receta y vigila la cocina sin tocar el celular, uniendo un '
            'ESP32 simulado en Wokwi con Streamlit mediante MQTT.</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- así se usa
st.markdown("## Así se usa")
pasos = [("libro", "1. Elige la receta", "Di «quiero hacer arepas» o toca una tarjeta."),
         ("play", "2. Di «siguiente»", "O presiona el botón verde del ESP32, hasta con el codo."),
         ("reloj", "3. Pon el temporizador", "«Pon el temporizador» y el LCD cuenta el tiempo."),
         ("gato_feliz", "4. Foto del plato final", "Toma la foto y califica la receta con estrellas.")]
cols = st.columns(4)
for col, (ic, t, d) in zip(cols, pasos):
    col.markdown('<div class="blob-w peq"><div class="blob" style="min-height:215px">%s'
                 '<div class="h" style="margin-top:10px">%s</div>%s</div></div>' % (icono(ic, 64), t, d),
                 unsafe_allow_html=True)

# ---------------------------------------------------------------- dos ambientes
st.markdown("## Dos ambientes")
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="blob-w"><div class="blob"><div class="fila">%s<div><div class="h">Asistente de recetas</div>'
                'Guía paso a paso con voz, texto, botones en pantalla y botones físicos. Lee cada paso '
                'en voz alta.</div></div></div></div>' % icono("gorro", 70), unsafe_allow_html=True)
    st.page_link("pages/1_🍳_Asistente_de_recetas.py", label="Abrir el asistente", icon="🍳")
with c2:
    st.markdown('<div class="blob-w"><div class="blob"><div class="fila">%s<div><div class="h">Monitor de cocina</div>'
                'Temperatura, humedad y fogón en vivo. Controla el extractor, la alarma y el buzzer con '
                'clics o con la voz.</div></div></div></div>' % icono("olla", 70), unsafe_allow_html=True)
    st.page_link("pages/2_🌡️_Monitor_de_cocina.py", label="Abrir el monitor", icon="🌡️")

# ---------------------------------------------------------------- modalidades
st.markdown("## Modalidades de interacción")
c1, c2 = st.columns(2)
c1.markdown('<div class="blob-w"><div class="blob"><div class="h">Entradas</div><ul>'
            '<li><b>Voz</b> en español (micrófono y modo manos libres)</li>'
            '<li><b>Texto</b>: escribe el mismo tipo de comandos</li>'
            '<li><b>Botones en pantalla</b></li>'
            '<li><b>Botones físicos</b> del ESP32 y la <b>perilla</b> del fogón</li>'
            '<li><b>Cámara</b> para la foto del plato</li></ul></div></div>', unsafe_allow_html=True)
c2.markdown('<div class="blob-w"><div class="blob"><div class="h">Salidas</div><ul>'
            '<li><b>Voz sintetizada</b> que lee cada paso y responde</li>'
            '<li><b>Pantalla</b>: paso en letra grande, métricas y gráficas</li>'
            '<li><b>LCD 16x2</b> con el paso y el temporizador</li>'
            '<li><b>Buzzer y LEDs</b> para confirmaciones y alertas</li>'
            '<li><b>Servo</b> que abre el extractor de humo</li></ul></div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- comandos
st.markdown("## Qué puedes decir")
comandos = [
    ("Navegar", "«empezar» · «siguiente» · «atrás» · «repite» · «ve al paso 3»"),
    ("Receta", "«quiero hacer arepas» · «¿qué ingredientes necesito?» · «¿cuánta harina?»"),
    ("Tiempo", "«pon el temporizador» · «temporizador de un minuto y medio» · «¿cuánto falta?» · «cancela el temporizador»"),
    ("Cocina", "«enciende el extractor» · «extractor en automático» · «¿qué temperatura hay?» · «umbral a 50 grados» · «prueba el sonido»"),
]
st.markdown('<div class="blob-w"><div class="blob"><table class="tabla-modal">%s</table></div></div>'
            % "".join("<tr><td><b>%s</b></td><td>%s</td></tr>" % c for c in comandos), unsafe_allow_html=True)

# ---------------------------------------------------------------- arquitectura
st.markdown("## Arquitectura: comunicación MQTT")
c1, c2 = st.columns(2)
c1.markdown('<div class="blob-w"><div class="blob"><div class="h">ESP32 → App</div>'
            'Publica <b>/estado</b> cada 2 s (temperatura, humedad, fogón, paso, extractor, temporizador) '
            'y <b>/evento</b> al presionar los botones o terminar el temporizador.</div></div>',
            unsafe_allow_html=True)
c2.markdown('<div class="blob-w"><div class="blob"><div class="h">App → ESP32</div>'
            'Streamlit publica <b>/cmd</b> con el paso de la receta, el temporizador, el extractor, '
            'el umbral y el buzzer. Todo pasa por el broker <b>%s</b>.</div></div>' % config.BROKER,
            unsafe_allow_html=True)
st.caption("Tópicos: `%s` · `%s` · `%s`" % (config.TOPICO_ESTADO, config.TOPICO_EVENTO, config.TOPICO_CMD))
st.markdown('<p style="text-align:center;font-weight:800;font-size:2rem;letter-spacing:-.04em;margin-top:30px">'
            '¡A COCINAR!</p>', unsafe_allow_html=True)

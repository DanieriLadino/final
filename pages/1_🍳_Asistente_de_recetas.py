"""Ambiente 1: Asistente de recetas (voz, texto, botones en pantalla y botones físicos)."""
import json
import os
import re
import time
from datetime import datetime

import streamlit as st

import cocina
import ui
from recetas import RECETAS
from ui import esc, icono

ui.iniciar_pagina("asistente", "Asistente de recetas", "🍳")
cocina.iniciar_estado()
ss = st.session_state
ss.setdefault("manos_libres", False)

# ---- voz: se procesa ANTES de dibujar la página para que la respuesta salga ya
frase = ui.frase_nueva("mic_asistente")
if frase:
    cocina.ejecutar(frase, "Voz")


def _texto_enviado():
    t = ss.get("txt_asistente", "")
    ss.txt_asistente = ""
    cocina.ejecutar(t, "Texto")


def _cambiar_ml():
    ss.manos_libres = ss.w_manos_libres


# ---------------------------------------------------------------- encabezado
st.markdown("# Asistente de recetas")
st.markdown('<p class="subtitulo">Habla, escribe o usa los botones: la receta avanza sin que toques el celular.</p>',
            unsafe_allow_html=True)

c_mic, c_txt = st.columns([1.15, 1.6], vertical_alignment="center")
with c_mic:
    ui.microfono("mic_asistente", continuo=ss.manos_libres)
    ss.w_manos_libres = ss.manos_libres
    st.toggle("Manos libres (escucha continua)", key="w_manos_libres", on_change=_cambiar_ml,
              help="El micrófono queda abierto y se pausa solo mientras el chef habla.")
with c_txt:
    st.text_input("Escribe un comando", key="txt_asistente", on_change=_texto_enviado,
                  placeholder="Ej.: siguiente · ¿cuánta sal? · pon un temporizador de 2 minutos",
                  label_visibility="collapsed")
    st.caption("Escribe y presiona Enter. Di o escribe «ayuda» para ver todos los comandos.")

ui.mostrar_voz()


# ---------------------------------------------------------------- zona en vivo (eventos + temporizador)
@st.fragment(run_every=1)
def en_vivo():
    if cocina.procesar_eventos():
        st.rerun()
    cocina.tarjeta_timer()
    cocina.tarjeta_alerta()


r = cocina.receta()

# ================================================================ 1. elegir receta
if not r:
    en_vivo()
    st.markdown("## Elige la receta")
    cols = st.columns(2)
    for i, rec in enumerate(RECETAS):
        with cols[i % 2]:
            st.markdown(
                '<div class="blob-w"><div class="blob"><div class="fila">%s<div>'
                '<div class="h" style="font-size:1.35rem">%s</div>%s<br>'
                '<span style="font-weight:500">%s · %d porciones · %d pasos · %s</span></div></div></div></div>'
                % (icono(rec["icono"], 84), esc(rec["nombre"]), esc(rec["descripcion"]), rec["tiempo"],
                   rec["porciones"], len(rec["pasos"]), rec["dificultad"]), unsafe_allow_html=True)
            st.button("Elegir " + rec["nombre"].lower(), key="elegir_" + rec["id"], type="primary",
                      use_container_width=True, on_click=cocina.accion_boton,
                      args=("Elegir " + rec["nombre"], cocina.elegir_receta, rec["id"]))
            st.write("")
    st.caption("También puedes decir: «quiero hacer pasta» o «empezar receta de arepas».")

# ================================================================ 2. ingredientes
elif ss.paso == 0:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown('<div class="fila" style="margin:8px 0 14px 0">%s<div><h2 style="margin:0">%s</h2>'
                    '<div class="subtitulo">%s · %d porciones · %s</div></div></div>'
                    % (icono(r["icono"], 76), esc(r["nombre"]), r["tiempo"], r["porciones"], r["dificultad"]),
                    unsafe_allow_html=True)
        filas = "".join('<li style="margin:6px 0"><b>%s</b> — %s</li>' % (esc(i["cantidad"]), esc(i["nombre"]))
                        for i in r["ingredientes"])
        st.markdown('<div class="blob-w"><div class="blob" style="font-size:1.25rem">'
                    '<div class="h" style="font-size:1.35rem">Ingredientes</div><ul>%s</ul></div></div>' % filas,
                    unsafe_allow_html=True)
        with st.container(key="grande_empezar"):
            st.button("▶  Empezar receta", key="btn_empezar", type="primary", use_container_width=True,
                      on_click=cocina.accion_boton, args=("Empezar receta", cocina.ir_a, 1))
        b1, b2 = st.columns(2)
        b1.button("🔊  Leer ingredientes", key="btn_leer_ing", use_container_width=True,
                  on_click=cocina.accion_boton, args=("Leer ingredientes", cocina.texto_ingredientes))
        b2.button("↩  Cambiar receta", key="btn_menu0", use_container_width=True,
                  on_click=cocina.ejecutar, args=("otra receta", "Botón en pantalla"))
    with c2:
        en_vivo()
        st.markdown('<div class="blob-w peq"><div class="blob crema"><div class="h">Prueba decir</div>'
                    '«¿cuánta %s?»<br>«empezar»<br>«siguiente»</div></div>'
                    % esc(r["ingredientes"][0]["claves"][0]), unsafe_allow_html=True)

# ================================================================ 3. pasos
elif not cocina.terminada():
    n = len(r["pasos"])
    p = cocina.paso_actual()
    c1, c2 = st.columns([2.15, 1])
    with c1:
        st.markdown('<div class="fila" style="margin:4px 0 10px 0">%s<h3 style="margin:0">%s</h3></div>'
                    % (icono(r["icono"], 44), esc(r["nombre"])), unsafe_allow_html=True)
        pista = ""
        if p.get("timer"):
            pista = '<div class="paso-pista">⏱ Este paso lleva %s. Di «pon el temporizador».</div>' % \
                    esc(cocina.voz.formato_duracion(p["timer"]))
        st.markdown('<div class="blob-w"><div class="blob" style="padding:30px 34px">'
                    '<div class="paso-num">Paso %d de %d</div><div class="paso-texto">%s</div>%s</div></div>'
                    % (ss.paso, n, esc(p["texto"]), pista), unsafe_allow_html=True)
        st.progress(ss.paso / n, text="Progreso: %d de %d pasos" % (ss.paso, n))
        with st.container(key="grande_nav"):
            b1, b2, b3 = st.columns([1, 1, 1.4])
            b1.button("◀  Atrás", key="btn_atras", use_container_width=True,
                      on_click=cocina.accion_boton, args=("Atrás", cocina.atras))
            b2.button("🔁  Repetir", key="btn_repetir", use_container_width=True,
                      on_click=cocina.accion_boton, args=("Repetir", cocina.repetir))
            b3.button("Siguiente  ▶" if ss.paso < n else "Terminar  ✔", key="btn_siguiente", type="primary",
                      use_container_width=True, on_click=cocina.accion_boton, args=("Siguiente", cocina.siguiente))
        t1, t2, t3 = st.columns([1.3, 1, 1])
        if p.get("timer"):
            t1.button("⏱  Iniciar temporizador (%s)" % cocina.voz.formato_duracion(p["timer"]), key="btn_timer",
                      use_container_width=True, on_click=cocina.accion_boton,
                      args=("Iniciar temporizador", cocina.iniciar_timer, p["timer"]))
        with t2.popover("⏱  Otro tiempo", use_container_width=True):
            mins = st.number_input("Minutos", 0.5, 240.0, 1.0, 0.5, key="min_custom")
            st.button("Iniciar", key="btn_timer_custom", type="primary", use_container_width=True,
                      on_click=cocina.accion_boton,
                      args=("Temporizador %g min" % mins, cocina.iniciar_timer, int(mins * 60)))
        t3.button("↩  Cambiar receta", key="btn_menu", use_container_width=True,
                  on_click=cocina.ejecutar, args=("otra receta", "Botón en pantalla"))
    with c2:
        en_vivo()
        filas = "".join("<li><b>%s</b> %s</li>" % (esc(i["cantidad"]), esc(i["nombre"].lower()))
                        for i in r["ingredientes"])
        st.markdown('<div class="blob-w peq"><div class="blob crema" style="font-size:.95rem">'
                    '<div class="h">Ingredientes</div><ul style="padding-left:1rem">%s</ul></div></div>' % filas,
                    unsafe_allow_html=True)

# ================================================================ 4. terminado: foto y calificación
else:
    en_vivo()
    c1, c2 = st.columns([1, 2], vertical_alignment="center")
    c1.markdown('<img src="%s" style="width:100%%;max-width:260px">' % ui.img_b64("static/img/gato.png"),
                unsafe_allow_html=True)
    with c2:
        st.markdown("# ¡Buen provecho!")
        st.markdown('<p class="subtitulo" style="font-size:1.3rem">Terminaste <b style="font-weight:600">%s</b>. '
                    'Toma una foto de tu plato y califica la receta.</p>' % esc(r["nombre"]), unsafe_allow_html=True)

    FOTOS = os.path.join(ui.RAIZ, "fotos")
    c1, c2 = st.columns([1.3, 1])
    with c1:
        foto = st.camera_input("Foto del plato final", key="camara_plato")
    with c2:
        st.markdown('<div class="blob-w peq"><div class="blob"><div class="h">¿Cómo te quedó?</div>'
                    'Califica la receta con estrellas.</div></div>', unsafe_allow_html=True)
        estrellas = st.feedback("stars", key="estrellas")
        if st.button("💾  Guardar foto y calificación", type="primary", use_container_width=True,
                     disabled=foto is None and estrellas is None):
            os.makedirs(FOTOS, exist_ok=True)
            marca = datetime.now().strftime("%Y%m%d-%H%M%S")
            n_est = (estrellas + 1) if estrellas is not None else 0
            if foto is not None:
                with open(os.path.join(FOTOS, "%s_%s_%d.jpg" % (marca, r["id"], n_est)), "wb") as f:
                    f.write(foto.getvalue())
            with open(os.path.join(FOTOS, "calificaciones.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"fecha": marca, "receta": r["nombre"], "estrellas": n_est},
                                   ensure_ascii=False) + "\n")
            msg = "¡Guardado! Le diste %d estrella%s a %s." % (n_est, "" if n_est == 1 else "s", r["nombre"].lower()) \
                if n_est else "¡Foto guardada!"
            cocina.registrar("Cámara", "Foto y calificación", msg)
            ui.decir(msg)
            ss.calificado = True
            st.rerun()
        if ss.calificado:
            st.success("Foto y calificación guardadas.")
        b1, b2 = st.columns(2)
        b1.button("🔁  Repetir receta", use_container_width=True,
                  on_click=cocina.accion_boton, args=("Repetir receta", cocina.ir_a, 0))
        b2.button("📖  Otra receta", use_container_width=True,
                  on_click=cocina.ejecutar, args=("otra receta", "Botón en pantalla"))

    if os.path.isdir(FOTOS):
        fotos = sorted([f for f in os.listdir(FOTOS) if f.endswith(".jpg")], reverse=True)[:4]
        if fotos:
            st.markdown("### Tus platos")
            cols = st.columns(4)
            for col, f in zip(cols, fotos):
                m = re.match(r"(\d{8})-\d{6}_(\w+)_(\d)\.jpg", f)
                pie = ""
                if m:
                    rr = next((x for x in RECETAS if x["id"] == m.group(2)), None)
                    pie = "%s %s" % (rr["nombre"] if rr else m.group(2), "★" * int(m.group(3)))
                col.image(os.path.join(FOTOS, f), caption=pie, use_container_width=True)

# ---------------------------------------------------------------- historial
st.write("")
with st.expander("Historial de interacciones (qué modalidad se usó)"):
    if ss.historial:
        st.dataframe(ss.historial, use_container_width=True, hide_index=True)
    else:
        st.caption("Aún no hay interacciones.")

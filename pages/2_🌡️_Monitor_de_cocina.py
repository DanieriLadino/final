"""Ambiente 2: Monitor de cocina (sensores en vivo, controles y voz)."""
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import cocina
import ui
from mqtt_puente import obtener_puente
from ui import esc, icono

ui.iniciar_pagina("monitor", "Monitor de cocina", "🌡️")
cocina.iniciar_estado()
ss = st.session_state
puente = obtener_puente()

frase = ui.frase_nueva("mic_monitor")
if frase:
    cocina.ejecutar(frase, "Voz")


def _texto_enviado():
    t = ss.get("txt_monitor", "")
    ss.txt_monitor = ""
    cocina.ejecutar(t, "Texto")


# ---- callbacks de los controles (clics)
def _cb_modo():
    if ss.w_ext_modo == "Automático":
        cocina.accion_boton("Extractor automático", cocina.poner_extractor, None, True)
    else:
        cocina.accion_boton("Extractor manual", cocina.poner_extractor, ss.ext_on)


def _cb_ext_on():
    cocina.accion_boton("Extractor " + ("abierto" if ss.w_ext_on else "cerrado"),
                        cocina.poner_extractor, ss.w_ext_on)


def _cb_umbral():
    cocina.accion_boton("Umbral %d °C" % ss.w_umbral, cocina.poner_umbral, ss.w_umbral)


# ---------------------------------------------------------------- encabezado y voz
st.markdown("# Monitor de cocina")
st.markdown('<p class="subtitulo">Temperatura, humedad y fogón en vivo. Controla el extractor, la alarma y el '
            'buzzer con clics o con la voz.</p>', unsafe_allow_html=True)
c_mic, c_txt = st.columns([1.15, 1.6], vertical_alignment="center")
with c_mic:
    ui.microfono("mic_monitor")
with c_txt:
    st.text_input("Escribe un comando", key="txt_monitor", on_change=_texto_enviado,
                  placeholder="Ej.: enciende el extractor · ¿qué temperatura hay? · umbral a 50 grados",
                  label_visibility="collapsed")
    st.caption("Escribe y presiona Enter.")

ui.mostrar_voz()

ETIQUETAS = {"siguiente": "Botón SIGUIENTE", "atras": "Botón ATRÁS", "timer_fin": "Fin del temporizador",
             "alerta_temp": "Alerta de temperatura", "conectado": "ESP32 conectado"}
AXIS = dict(labelFont="Poppins", titleFont="Poppins", labelColor="#004AAD", titleColor="#004AAD",
            gridColor="#E9DFC4", domainColor="#004AAD", tickColor="#004AAD")


def _datos(df):
    """Datos en línea (no como dataset con nombre) para que las recargas en vivo no den errores."""
    d = df.copy()
    d["hora"] = d["hora"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return alt.Data(values=d.to_dict("records"))


def _grafica(df, campo, titulo, color, regla=None, dominio=None):
    base = alt.Chart(_datos(df)).encode(x=alt.X("hora:T", title=None, axis=alt.Axis(format="%H:%M:%S", **AXIS)))
    escala = alt.Scale(domain=dominio) if dominio else alt.Scale(zero=False)
    area = base.mark_area(color="#DCE5F4", opacity=1, line=False).encode(
        y=alt.Y(campo + ":Q", title=titulo, scale=escala, axis=alt.Axis(**AXIS)))
    linea = base.mark_line(color=color, strokeWidth=3, interpolate="monotone").encode(
        y=alt.Y(campo + ":Q", scale=escala), tooltip=[alt.Tooltip("hora:T", format="%H:%M:%S"), campo + ":Q"])
    capas = [area, linea]
    if regla is not None:
        capas.append(alt.Chart(alt.Data(values=[{"u": float(regla)}])).mark_rule(
            color="#C8102E", strokeDash=[6, 5], strokeWidth=2).encode(y="u:Q"))
    return alt.layer(*capas).properties(height=210).configure_view(stroke=None).configure(background="#FCF8ED")


@st.fragment(run_every=2)
def en_vivo():
    if cocina.procesar_eventos():
        st.rerun()
    e = puente.ultimo_estado()
    vivo = puente.esp32_conectado()
    cocina.tarjeta_alerta()
    cocina.tarjeta_timer()

    if not e:
        st.markdown('<div class="blob-w"><div class="blob crema"><div class="fila">%s<div><div class="h">'
                    'Esperando datos del ESP32…</div>Inicia la simulación en Wokwi o activa el '
                    '<b>ESP32 simulado</b> en la barra lateral. Los datos llegan cada 2 segundos.</div></div>'
                    '</div></div>' % icono("gato_normal", 70), unsafe_allow_html=True)
        return
    if not vivo:
        st.warning("El ESP32 dejó de enviar datos. Se muestran los últimos valores recibidos.")

    def met(col, ic, valor, etiqueta):
        col.markdown('<div class="blob-w peq"><div class="blob" style="padding:16px 18px"><div class="metrica">%s'
                     '<div><div class="v">%s</div><div class="l">%s</div></div></div></div></div>'
                     % (icono(ic, 50), valor, etiqueta), unsafe_allow_html=True)

    c = st.columns(2) + st.columns(2)
    temp = e.get("temperatura")
    met(c[0], "olla", "%s °C" % (temp if temp is not None else "—"), "Temperatura")
    met(c[1], "taza", "%s %%" % e.get("humedad", "—"), "Humedad")
    met(c[2], "sarten", "%s %%" % e.get("fogon", "—"), "Fogón")
    met(c[3], "licuadora", "Abierto" if e.get("extractor") else "Cerrado",
        "Extractor · " + ("auto" if e.get("extractor_auto", True) else "manual"))

    hist = puente.lista_historial()
    if len(hist) >= 2:
        df = pd.DataFrame(hist[-150:])
        df["hora"] = pd.to_datetime([datetime.fromtimestamp(h) for h in df["hora"]])
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Temperatura** · línea roja = umbral (%s °C)" % e.get("umbral", ss.umbral))
            st.altair_chart(_grafica(df, "temperatura", "°C", "#004AAD", regla=e.get("umbral", ss.umbral)),
                            use_container_width=True)
        with g2:
            st.markdown("**Humedad y fogón** (%)")
            largo = df.melt(id_vars="hora", value_vars=["humedad", "fogon"], var_name="serie", value_name="valor")
            graf = alt.Chart(_datos(largo)).mark_line(strokeWidth=3, interpolate="monotone").encode(
                x=alt.X("hora:T", title=None, axis=alt.Axis(format="%H:%M:%S", **AXIS)),
                y=alt.Y("valor:Q", title="%", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(**AXIS)),
                color=alt.Color("serie:N", scale=alt.Scale(domain=["humedad", "fogon"], range=["#004AAD", "#E07A00"]),
                                legend=alt.Legend(orient="top", title=None, labelFont="Poppins", labelColor="#004AAD")),
                tooltip=[alt.Tooltip("hora:T", format="%H:%M:%S"), "serie:N", "valor:Q"],
            ).properties(height=210).configure_view(stroke=None).configure(background="#FCF8ED")
            st.altair_chart(graf, use_container_width=True)
    else:
        st.caption("Las gráficas aparecen en cuanto lleguen dos lecturas.")

    eventos = puente.lista_eventos()[-12:][::-1]
    st.markdown("**Eventos del ESP32**")
    if eventos:
        st.dataframe(
            [{"Hora": datetime.fromtimestamp(ev["hora"]).strftime("%H:%M:%S"),
              "Evento": ETIQUETAS.get(ev.get("tipo"), ev.get("tipo"))} for ev in eventos],
            use_container_width=True, hide_index=True, height=min(36 * (len(eventos) + 1) + 4, 300))
    else:
        st.caption("Sin eventos todavía. Presiona un botón físico del ESP32.")


col_vivo, col_ctrl = st.columns([2.3, 1], gap="large")
with col_vivo:
    en_vivo()

with col_ctrl:
    st.markdown("### Controles")
    # los widgets reflejan el estado guardado (también lo cambia la voz)
    ss.w_ext_modo = ss.ext_modo
    ss.w_ext_on = ss.ext_on
    ss.w_umbral = int(ss.umbral)
    st.markdown('<div class="fila">%s<b>Extractor de humo</b></div>' % icono("licuadora", 36), unsafe_allow_html=True)
    st.radio("Modo del extractor", ["Automático", "Manual"], key="w_ext_modo", horizontal=True,
             on_change=_cb_modo, label_visibility="collapsed")
    st.toggle("Extractor abierto (servo a 90°)", key="w_ext_on", on_change=_cb_ext_on,
              disabled=ss.ext_modo == "Automático")
    st.caption("En automático se abre si la temperatura supera el umbral o el fogón pasa de 70 %.")
    st.divider()
    st.markdown('<div class="fila">%s<b>Alarma de temperatura</b></div>' % icono("olla", 36), unsafe_allow_html=True)
    st.slider("Umbral (°C)", 20, 90, key="w_umbral", on_change=_cb_umbral)
    st.button("🔔  Probar buzzer", use_container_width=True,
              on_click=cocina.accion_boton, args=("Probar buzzer", cocina.probar_buzzer))
    st.divider()
    st.markdown('<div class="fila">%s<b>Temporizador</b></div>' % icono("reloj", 36), unsafe_allow_html=True)
    mins = st.number_input("Minutos", 0.5, 240.0, 5.0, 0.5, key="min_monitor")
    a, b = st.columns(2)
    a.button("Iniciar", type="primary", use_container_width=True, on_click=cocina.accion_boton,
             args=("Temporizador %g min" % mins, cocina.iniciar_timer, int(mins * 60)))
    b.button("Cancelar", use_container_width=True, on_click=cocina.accion_boton,
             args=("Cancelar temporizador", cocina.cancelar_timer))
    st.divider()
    st.markdown('<div class="blob-w peq"><div class="blob crema" style="font-size:.95rem"><div class="h">Prueba decir</div>'
                '«enciende el extractor»<br>«extractor en automático»<br>«¿qué temperatura hay?»<br>'
                '«umbral a 50 grados»<br>«prueba el sonido»</div></div>', unsafe_allow_html=True)

st.write("")
with st.expander("Historial de interacciones (qué modalidad se usó)"):
    if ss.historial:
        st.dataframe(ss.historial, use_container_width=True, hide_index=True)
    else:
        st.caption("Aún no hay interacciones.")

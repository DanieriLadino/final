"""Estética (la misma del PDF), barra lateral, voz de salida y micrófono."""
import base64
import html
import os
import time
from functools import lru_cache

import streamlit as st
import streamlit.components.v1 as components

import config
from mqtt_puente import obtener_puente
from simulador_esp32 import obtener_simulador
import voz

RAIZ = os.path.dirname(os.path.abspath(__file__))
AZUL = "#004AAD"
CREMA = "#FCF8ED"

_microfono = components.declare_component("microfono", path=os.path.join(RAIZ, "componentes", "microfono"))


# ------------------------------------------------------------------ imágenes

@lru_cache(maxsize=64)
def img_b64(ruta_relativa):
    with open(os.path.join(RAIZ, ruta_relativa), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def icono(nombre, tam=56, clase="icono"):
    return '<img class="%s" src="%s" width="%d" height="%d" alt="">' % (
        clase, img_b64("static/img/iconos/%s.png" % nombre), tam, tam)


def esc(t):
    return html.escape(str(t))


# ------------------------------------------------------------------ estilos

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@200;300;400;500;600;700;800&display=swap');
/* Nectarine: se usa si está instalada en el equipo o si se copia el archivo en static/fonts/ */
__FONT_FACE__
:root { --azul:#004AAD; --crema:#FCF8ED; --crema2:#F3EAD3; --rojo:#C8102E; }

html, body, .stApp, [data-testid="stAppViewContainer"], .stMarkdown, p, li, label, input, textarea, button, td, th {
  font-family: 'Poppins', sans-serif !important;
}
/* Los íconos de Streamlit usan su propia fuente: no tocarlos */
[data-testid="stIconMaterial"], .material-symbols-rounded, span[class*="material"] {
  font-family: 'Material Symbols Rounded' !important;
}
.stApp { background: var(--crema); color: var(--azul); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }
p, li, label, .stMarkdown { color: var(--azul); }

/* Títulos como en las diapositivas: Poppins Bold, mayúsculas y apretados */
h1, h2, h3, .titulo {
  font-family: 'Poppins', sans-serif !important; font-weight: 800 !important; color: var(--azul) !important;
  text-transform: uppercase; letter-spacing: -0.045em; line-height: 1.02 !important;
}
h1 { font-size: clamp(2.1rem, 4.6vw, 3.6rem) !important; }
h2 { font-size: clamp(1.6rem, 3vw, 2.3rem) !important; }
h3 { font-size: 1.3rem !important; }
.nectarine { font-family: 'Nectarine', 'Poppins', sans-serif; font-weight: 800; letter-spacing: -0.01em; }
.subtitulo { font-weight: 200; font-size: 1.15rem; margin-top: -.2rem; }
.anchor-link, [data-testid="stHeaderActionElements"] { display: none !important; }

/* ---------- tarjeta azul con sombra rayada (la "mancha" del PDF) ---------- */
.blob-w { position: relative; isolation: isolate; margin: 4px 16px 26px 0; }
.blob-w::before {
  content: ""; position: absolute; z-index: -1; left: 10px; right: -12px; top: 12px; bottom: -14px;
  border: 3px solid var(--azul);
  border-radius: 22px 30px 18px 34px / 26px 18px 30px 22px;
  background: repeating-linear-gradient(118deg, var(--azul) 0 10px, var(--crema) 10px 14px);
}
.blob {
  position: relative; background: var(--azul); color: var(--crema);
  border-radius: 22px 30px 18px 34px / 26px 18px 30px 22px;
  padding: 22px 28px; font-weight: 200; font-size: 1.05rem; line-height: 1.55;
}
.blob b, .blob strong, .blob .t { font-weight: 500; }
.blob h3, .blob .h { color: var(--crema) !important; font-weight: 700; text-transform: none; letter-spacing: -0.01em;
  font-size: 1.15rem; margin: 0 0 4px 0; }
.blob ul { margin: 6px 0 0 0; padding-left: 1.1rem; }
.blob li { color: var(--crema); }
.blob.crema { background: var(--crema); color: var(--azul); border: 3px solid var(--azul); }
.blob.crema li, .blob.crema .h { color: var(--azul) !important; }
.blob.alerta { background: var(--rojo); }
.blob-w.alerta::before { border-color: var(--rojo);
  background: repeating-linear-gradient(118deg, var(--rojo) 0 10px, var(--crema) 10px 14px); }
.blob-w.peq::before { left: 7px; right: -8px; top: 8px; bottom: -9px; }
.blob-w.peq { margin-bottom: 18px; }

.icono { border-radius: 18px; flex: none; }
.fila { display: flex; gap: 16px; align-items: center; }

/* ---------- paso de la receta: letra grande para leer a distancia (RNF3) ---------- */
.paso-num { font-weight: 700; font-size: 1rem; letter-spacing: .08em; text-transform: uppercase; opacity: .85; }
.paso-texto { font-weight: 300; font-size: clamp(2rem, 3.3vw, 2.75rem); line-height: 1.25; margin-top: 6px; }
.paso-pista { font-weight: 200; font-size: 1.05rem; margin-top: 14px; opacity: .9; }

/* ---------- métricas ---------- */
.metrica { display: flex; gap: 14px; align-items: center; }
.metrica .v { font-weight: 700; font-size: 2rem; line-height: 1; letter-spacing: -0.03em; }
.metrica .l { font-weight: 200; font-size: .95rem; }

/* ---------- botones ---------- */
.stButton > button, .stFormSubmitButton > button, [data-testid="stPageLink"] a, .stDownloadButton > button {
  font-family: 'Poppins', sans-serif !important; font-weight: 600 !important;
  border: 2.5px solid var(--azul) !important;
  border-radius: 18px 24px 16px 26px / 20px 16px 24px 18px !important;
  box-shadow: 4px 5px 0 0 rgba(0,74,173,.22);
  transition: transform .12s ease, box-shadow .12s ease;
  min-height: 3rem;
}
.stButton > button:disabled, .stButton > button[disabled] { opacity: .45; cursor: not-allowed; transform: none; }
.st-key-estrellas { transform: scale(1.9); transform-origin: left center; margin: 14px 0 22px 0; }
.stButton > button:hover, .stFormSubmitButton > button:hover { transform: translateY(-2px); box-shadow: 5px 7px 0 0 rgba(0,74,173,.25); }
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(2px); box-shadow: 2px 2px 0 0 rgba(0,74,173,.25); }
button[kind="primary"], [data-testid="stBaseButton-primary"] { background: var(--azul) !important; color: var(--crema) !important; }
button[kind="secondary"], [data-testid="stBaseButton-secondary"],
button[kind="secondaryFormSubmit"], [data-testid="stBaseButton-secondaryFormSubmit"] {
  background: var(--crema) !important; color: var(--azul) !important; }
.stButton > button p, .stFormSubmitButton > button p { font-weight: 600 !important; font-size: 1.02rem; color: inherit !important; }
[class*="st-key-grande"] .stButton > button { min-height: 4.4rem; }
[class*="st-key-grande"] .stButton > button p { font-size: 1.3rem !important; }
[data-testid="stPageLink"] a { background: var(--azul); padding: .5rem 1rem; justify-content: center; }
[data-testid="stPageLink"] a p { white-space: normal !important; text-align: center; line-height: 1.2; }
.stButton > button p { white-space: normal; line-height: 1.2; }
[data-testid="stPageLink"] a p, [data-testid="stPageLink"] a span { color: var(--crema) !important; font-weight: 600 !important; }

/* entradas */
.stTextInput input, .stNumberInput input {
  border-radius: 14px !important; background: #fff !important; color: var(--azul) !important; font-weight: 400; }
.stTextInput > div > div, .stNumberInput > div > div { border-color: var(--azul) !important; border-radius: 14px !important; }
[data-testid="stForm"] { border: none; padding: 0; }
.stProgress > div > div > div > div { background-color: var(--azul); }
.stProgress > div > div > div { background-color: var(--crema2); height: 12px; border-radius: 8px; }
[data-testid="stExpander"] details { border: 2px solid var(--azul); border-radius: 16px; background: var(--crema); }
[data-testid="stExpander"] summary p { font-weight: 600; }
[data-testid="stAlert"] { border-radius: 16px; }
hr { border-color: rgba(0,74,173,.2); }

/* ---------- barra lateral azul con letra crema ---------- */
[data-testid="stSidebar"] { background: var(--azul); }
[data-testid="stSidebar"] * { color: var(--crema); }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a { border-radius: 12px; }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(252,248,237,.16); }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] span { color: var(--crema) !important; font-weight: 500; }
[data-testid="stSidebar"] .stButton > button { box-shadow: 3px 4px 0 0 rgba(0,0,0,.25); border-color: var(--crema) !important; }
[data-testid="stSidebar"] button[kind="secondary"], [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
  background: var(--azul) !important; color: var(--crema) !important; }
[data-testid="stSidebar"] button[kind="primary"], [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
  background: var(--crema) !important; color: var(--azul) !important; }
[data-testid="stSidebar"] button[kind="primary"] p { color: var(--azul) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(252,248,237,.3); }
[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] { background: var(--crema); }
[data-testid="stSidebar"] code { background: rgba(252,248,237,.16) !important; color: var(--crema) !important; }
[data-testid="stSidebar"] [data-testid="stCheckbox"] label > div:first-child,
[data-testid="stSidebar"] label[data-baseweb="checkbox"] > div:first-child { background: rgba(252,248,237,.35) !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: rgba(252,248,237,.85) !important; }
[data-testid="stSidebarCollapseButton"] * , [data-testid="stSidebarHeader"] * { color: var(--crema) !important; }

.pill { display: inline-flex; align-items: center; gap: 8px; font-weight: 500; font-size: .9rem;
  padding: 4px 12px; border-radius: 999px; border: 2px solid currentColor; margin: 2px 0; }
.punto { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.on { background: #3DDC84; box-shadow: 0 0 8px #3DDC84; }
.off { background: #FF6B6B; }

/* LCD 16x2 del ESP32 */
.lcd { background: #3B6E14; border: 6px solid #1d3a08; border-radius: 8px; padding: 8px 10px;
  font-family: 'Courier New', monospace !important; color: #D9F99D !important; font-size: 15px; line-height: 1.3;
  letter-spacing: 1px; white-space: pre; box-shadow: inset 0 0 12px rgba(0,0,0,.4); overflow: hidden; }
.lcd * { font-family: 'Courier New', monospace !important; color: #D9F99D !important; }
.leds { display: flex; gap: 12px; align-items: center; font-size: .82rem; margin-top: 8px; flex-wrap: wrap; }
.led { width: 14px; height: 14px; border-radius: 50%; display: inline-block; border: 2px solid rgba(255,255,255,.4); vertical-align: middle; }
.led.verde.on { background: #3DDC84; box-shadow: 0 0 10px #3DDC84; }
.led.rojo.on { background: #FF4D4D; box-shadow: 0 0 10px #FF4D4D; }
.led.apagado { background: rgba(0,0,0,.25); box-shadow: none; }

/* burbuja del chef (lo que dice en voz alta) */
.chef-dice { display: flex; gap: 12px; align-items: center; background: #fff; border: 2.5px solid var(--azul);
  border-radius: 20px 26px 20px 6px; padding: 10px 16px; margin-bottom: 8px; font-weight: 400; }
.chef-dice img { border-radius: 12px; }
.chef-dice .q { font-weight: 300; }
[data-testid="stAudio"] { margin: -2px 0 6px 0 !important; }
[data-testid="stAudio"] audio { height: 38px; width: 100%; max-width: 520px; }

/* temporizador */
.timer { font-weight: 800; font-size: 3.3rem; letter-spacing: -0.04em; line-height: 1; }
.timer.fin { animation: parpadeo .6s steps(2) infinite; font-size: 2.2rem; }
.blob .fila > div { min-width: 0; }
@keyframes parpadeo { 50% { opacity: .25; } }

.tabla-modal td, .tabla-modal th { padding: 6px 10px; border-bottom: 1px solid rgba(252,248,237,.25); text-align: left; }
.tabla-modal { border-collapse: collapse; width: 100%; color: var(--crema); }

@media (max-width: 640px) {
  .blob { padding: 18px 18px; }
  .paso-texto { font-size: 1.75rem; }
  .block-container { padding-left: 1rem; padding-right: 1rem; }
}
</style>
"""


def _font_face():
    """Nectarine: se usa si está instalada o si se copia el archivo en static/fonts/."""
    fuentes = ["local('Nectarine')", "local('Nectarine Regular')", "local('Nectarine-Regular')"]
    carpeta = os.path.join(RAIZ, "static", "fonts")
    if os.path.isdir(carpeta):
        for f in sorted(os.listdir(carpeta)):
            if f.lower().startswith("nectarine") and f.lower().endswith((".otf", ".ttf", ".woff", ".woff2")):
                fmt = {"otf": "opentype", "ttf": "truetype", "woff": "woff", "woff2": "woff2"}[f.rsplit(".", 1)[1].lower()]
                fuentes.append("url('/app/static/fonts/%s') format('%s')" % (f, fmt))
    return "@font-face { font-family: 'Nectarine'; src: %s; font-display: swap; }" % ", ".join(fuentes)


_CSS = _CSS.replace("__FONT_FACE__", _font_face())

# Markdown corta los bloques HTML en las líneas vacías: se quitan.
_CSS_COMPACTO = "\n".join(l.strip() for l in _CSS.splitlines() if l.strip())


def iniciar_pagina(nombre, titulo, icono_pagina="🍳"):
    """Configura la página, aplica estilos, prepara la voz y la barra lateral."""
    st.set_page_config(page_title=titulo + " · Chef Manos Libres", page_icon=icono_pagina,
                       layout="wide", initial_sidebar_state="expanded")
    st.html(_CSS_COMPACTO)
    ss = st.session_state
    ss.setdefault("voz", None)
    ss.setdefault("voz_n", 0)
    if ss.get("pagina_actual") != nombre:
        ss["pagina_actual"] = nombre
        ss["voz"] = None            # al cambiar de página no se repite lo último dicho
    ss["_slot_voz"] = st.container()  # posición fija: el audio no se reinicia en cada recarga
    barra_lateral()


# ------------------------------------------------------------------ voz de salida

def decir(texto):
    ss = st.session_state
    ss["voz_n"] = ss.get("voz_n", 0) + 1
    ss["voz"] = {"id": ss["voz_n"], "texto": texto, "t": time.time()}


def mostrar_voz():
    """Muestra lo que dice el chef y lo reproduce (gTTS; si falla, la voz del navegador).

    Si el navegador bloquea la reproducción automática, aparece un botón
    «Toca para escuchar» y el reproductor queda visible para darle play.
    """
    ss = st.session_state
    v = ss.get("voz")
    slot = ss.get("_slot_voz") or st.container()
    if not v:
        return
    with slot:
        st.markdown(
            '<div class="chef-dice">%s<div><b>Chef:</b> <span class="q">%s</span></div></div>'
            % (icono("gato_feliz", 40), esc(v["texto"])), unsafe_allow_html=True)
        mp3 = voz.sintetizar(v["texto"], v["id"])
        if mp3:
            st.audio(mp3, format="audio/mp3", autoplay=True)
        components.html(_JS_VOZ % (v["id"], _js_str(v["texto"]), "true" if mp3 else "false"), height=0)


# Se ejecuta una vez por cada frase nueva (el número cambia y el iframe se recrea).
_JS_VOZ = """<script>
(function () {
  var ID = %d, TEXTO = %s, HAY_MP3 = %s;
  var P = window.parent, D = P.document;
  function quitar() { var b = D.getElementById("chef-voz-btn"); if (b) b.remove(); }
  function boton(accion) {
    var b = D.getElementById("chef-voz-btn");
    if (!b) {
      b = D.createElement("button");
      b.id = "chef-voz-btn";
      b.textContent = "🔊 Toca para escuchar al chef";
      b.style.cssText = "position:fixed;right:22px;bottom:22px;z-index:999999;background:#004AAD;color:#FCF8ED;" +
        "border:3px solid #FCF8ED;border-radius:22px 28px 18px 30px;padding:14px 22px;font:600 17px Poppins,sans-serif;" +
        "box-shadow:5px 6px 0 rgba(0,74,173,.35);cursor:pointer";
      D.body.appendChild(b);
    }
    b.onclick = function () { quitar(); accion(); };
  }
  function vozNavegador() {
    try {
      var s = P.speechSynthesis; s.cancel();
      var u = new P.SpeechSynthesisUtterance(TEXTO); u.lang = "es-ES";
      var es = s.getVoices().filter(function (x) { return x.lang && x.lang.indexOf("es") === 0; });
      if (es.length) u.voice = es[0];
      s.speak(u);
    } catch (e) {}
  }
  if (!HAY_MP3) {             // sin internet para gTTS: voz del navegador
    vozNavegador();
    setTimeout(function () {
      var s = P.speechSynthesis;
      if (s && !s.speaking && !s.pending) boton(vozNavegador);
    }, 900);
    return;
  }
  var intentos = 0;
  (function reproducir() {
    var a = D.querySelector('[data-testid="stAudio"] audio') || D.querySelector("audio");
    if (!a || !a.src) { if (intentos++ < 40) setTimeout(reproducir, 150); return; }
    if (!a.paused) { quitar(); return; }          // la reproducción automática funcionó
    var p = a.play();
    if (p && p.then) {
      p.then(quitar).catch(function (e) {
        if (e && e.name === "NotAllowedError") boton(function () { a.currentTime = 0; a.play(); });
        else if (intentos++ < 40) setTimeout(reproducir, 200);
      });
    }
  })();
})();
</script>"""


def _js_str(t):
    import json
    return json.dumps(t)


# ------------------------------------------------------------------ micrófono

def microfono(clave, continuo=False):
    """Botón de micrófono. Devuelve {"texto", "id"} con la última frase reconocida o None."""
    return _microfono(continuo=continuo, idioma="es-CO", max_palabras=12, autoiniciar=True,
                      key=clave, default=None)


def frase_nueva(clave):
    """Lee la última frase del micrófono una sola vez (antes de dibujar los widgets)."""
    v = st.session_state.get(clave)
    if isinstance(v, dict) and v.get("id") and v.get("id") != st.session_state.get("_ult_" + clave):
        st.session_state["_ult_" + clave] = v["id"]
        return v.get("texto", "")
    return None


# ------------------------------------------------------------------ barra lateral

def barra_lateral():
    with st.sidebar:
        st.markdown('<img src="%s" style="width:100%%;max-width:230px;margin:2px 0 6px 0">'
                    % img_b64("static/img/logo_crema.png"), unsafe_allow_html=True)
        _panel_conexion()


@st.fragment(run_every=1)
def _panel_conexion():
    puente = obtener_puente()
    sim = obtener_simulador()
    esp = puente.esp32_conectado()
    estado = puente.ultimo_estado()
    simulado = bool(estado.get("simulado")) and esp
    st.markdown(
        '<div class="pill"><span class="punto %s"></span>Broker MQTT %s</div><br>'
        '<div class="pill"><span class="punto %s"></span>ESP32 %s</div>'
        % ("on" if puente.conectado else "off", "conectado" if puente.conectado else "sin conexión",
           "on" if esp else "off", ("simulado conectado" if simulado else "conectado") if esp else "desconectado"),
        unsafe_allow_html=True)
    if not esp:
        st.caption("La app funciona igual. Inicia el circuito en Wokwi o activa el ESP32 simulado.")
    st.caption("Tópico: `%s`" % config.TOPICO_BASE)

    st.divider()
    activo = st.toggle("ESP32 simulado", value=sim.corriendo, key="sim_toggle",
                       help="Imita al ESP32 de Wokwi para probar sin la simulación. No lo actives a la vez que Wokwi.")
    if activo and not sim.corriendo:
        sim.iniciar()
    elif not activo and sim.corriendo:
        sim.detener()
    if sim.corriendo:
        _panel_simulador(sim)


def _panel_simulador(sim):
    st.markdown('<div class="lcd">%s\n%s</div>' % (esc(sim.lcd[0] or " " * 16), esc(sim.lcd[1] or " " * 16)),
                unsafe_allow_html=True)
    pitando = time.time() - sim.ultimo_pitido < 1.5
    st.markdown(
        '<div class="leds"><span><span class="led verde %s"></span> Verde</span>'
        '<span><span class="led rojo %s"></span> Rojo</span>'
        '<span>Servo %d°</span><span>%s</span></div>'
        % ("on" if sim.led_verde else "apagado", "on" if sim.led_rojo else "apagado", sim.servo,
           ("🔊 " + esc(sim.ultimo_pitido_desc)) if pitando else "🔈 Buzzer"),
        unsafe_allow_html=True)
    st.write("")
    st.caption("Botones físicos del ESP32")
    st.button("SIGUIENTE  ▶", key="sim_sig", type="primary", use_container_width=True,
              on_click=sim.presionar, args=("siguiente",))
    st.button("◀  ATRÁS", key="sim_atras", use_container_width=True, on_click=sim.presionar, args=("atras",))
    sim.fogon = st.slider("Perilla del fogón (%)", 0, 100, int(sim.fogon), 5, key="sim_fogon")

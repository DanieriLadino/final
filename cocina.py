"""Lógica compartida de la cocina: estado de la receta, comandos, temporizador y eventos.

Todas las modalidades (voz, texto, botones en pantalla, botones físicos) terminan
llamando a ejecutar(), que actualiza el estado, envía el comando al ESP32 por MQTT,
responde por voz y deja registro de qué modalidad se usó.
"""
import time
from datetime import datetime

import streamlit as st

import config
import voz
from mqtt_puente import obtener_puente
from recetas import RECETAS, por_id
from ui import decir

# ------------------------------------------------------------------ estado

def iniciar_estado():
    ss = st.session_state
    puente = obtener_puente()
    ss.setdefault("receta_id", None)
    ss.setdefault("paso", 0)            # 0 = ingredientes, 1..N = pasos, N+1 = terminado
    ss.setdefault("timer", None)        # {"fin", "total", "etiqueta"}
    ss.setdefault("historial", [])
    ss.setdefault("alerta_activa", False)
    ss.setdefault("alarma_hasta", 0.0)
    ss.setdefault("ultimo_seq", puente.ultimo_seq())   # no reprocesar eventos viejos
    ss.setdefault("ext_modo", "Automático")
    ss.setdefault("ext_on", False)
    ss.setdefault("umbral", float(puente.ultimo_estado().get("umbral") or config.UMBRAL_TEMPERATURA))
    ss.setdefault("calificado", False)


def receta():
    return por_id(st.session_state.get("receta_id"))


def total_pasos():
    r = receta()
    return len(r["pasos"]) if r else 0


def terminada():
    return receta() is not None and st.session_state.paso > total_pasos()


def paso_actual():
    r = receta()
    p = st.session_state.paso
    if r and 1 <= p <= len(r["pasos"]):
        return r["pasos"][p - 1]
    return None


def registrar(modalidad, comando, respuesta):
    st.session_state.historial.insert(0, {
        "Hora": datetime.now().strftime("%H:%M:%S"),
        "Modalidad": modalidad,
        "Comando": comando,
        "Respuesta": respuesta,
    })
    del st.session_state.historial[60:]


# ------------------------------------------------------------------ envío al ESP32

def enviar_paso():
    r = receta()
    ss = st.session_state
    puente = obtener_puente()
    if not r:
        puente.publicar(receta="", paso=0, total=0, texto="Elige una receta")
        return
    n = len(r["pasos"])
    if ss.paso == 0:
        puente.publicar(receta=r["nombre"], paso=0, total=n, texto=r["nombre"] + ": revisa los ingredientes")
    elif ss.paso <= n:
        puente.publicar(receta=r["nombre"], paso=ss.paso, total=n, texto=r["pasos"][ss.paso - 1]["texto"])
    else:
        puente.publicar(receta=r["nombre"], paso=n, total=n, texto="Receta terminada", fin=True)


def texto_paso():
    r = receta()
    p = paso_actual()
    if not p:
        return ""
    t = "Paso %d de %d. %s" % (st.session_state.paso, len(r["pasos"]), p["texto"])
    if p.get("timer"):
        t += " Si quieres, di: pon el temporizador."
    return t


def texto_ingredientes():
    r = receta()
    partes = ["%s de %s" % (i["cantidad"], i["nombre"].lower()) for i in r["ingredientes"]]
    return "Para %s necesitas: %s." % (r["nombre"].lower(), "; ".join(partes))


# ------------------------------------------------------------------ acciones

def elegir_receta(rid, empezar=False):
    ss = st.session_state
    r = por_id(rid)
    if not r:
        return "No encontré esa receta."
    ss.receta_id = rid
    ss.paso = 1 if empezar else 0
    ss.calificado = False
    cancelar_timer(silencioso=True)
    enviar_paso()
    if empezar:
        return texto_paso()
    return "Elegiste %s. %s Cuando estés lista, di: empezar." % (r["nombre"], texto_ingredientes())


def ir_a(paso):
    ss = st.session_state
    r = receta()
    if not r:
        return "Primero elige una receta."
    n = len(r["pasos"])
    paso = max(0, min(n + 1, paso))
    ss.paso = paso
    enviar_paso()
    if paso == 0:
        return texto_ingredientes()
    if paso > n:
        cancelar_timer(silencioso=True)
        return "¡Terminaste! Buen provecho. Toma una foto de tu plato y califica la receta."
    return texto_paso()


def siguiente():
    if not receta():
        return "Primero elige una receta."
    if terminada():
        return "Ya terminaste la receta. ¡Buen provecho!"
    return ir_a(st.session_state.paso + 1)


def atras():
    if not receta():
        return "Primero elige una receta."
    if st.session_state.paso == 0:
        return "Ya estás en los ingredientes."
    return ir_a(st.session_state.paso - 1)


def repetir():
    if not receta():
        return "Elige una receta para empezar. " + nombres_recetas()
    if st.session_state.paso == 0:
        return texto_ingredientes()
    if terminada():
        return "Terminaste la receta. ¡Buen provecho!"
    return texto_paso()


def nombres_recetas():
    return "Tengo: " + ", ".join(r["nombre"].lower() for r in RECETAS) + "."


def iniciar_timer(segundos=None):
    ss = st.session_state
    if not segundos:
        p = paso_actual()
        segundos = p.get("timer") if p else None
    if not segundos:
        return "¿De cuánto tiempo? Por ejemplo: pon un temporizador de cinco minutos."
    segundos = int(max(1, min(segundos, 4 * 3600)))
    ss.timer = {"fin": time.time() + segundos, "total": segundos, "etiqueta": voz.formato_duracion(segundos)}
    ss.alarma_hasta = 0.0
    obtener_puente().publicar(timer=segundos)
    return "Listo, temporizador de %s. Te aviso cuando termine." % voz.formato_duracion(segundos)


def cancelar_timer(silencioso=False):
    ss = st.session_state
    habia = ss.get("timer") is not None
    ss.timer = None
    ss.alarma_hasta = 0.0
    if habia or not silencioso:
        obtener_puente().publicar(timer=0)
    return "Temporizador cancelado." if habia else "No hay ningún temporizador activo."


def timer_restante():
    t = st.session_state.get("timer")
    if not t:
        return None
    return max(0, t["fin"] - time.time())


def terminar_timer(origen):
    ss = st.session_state
    t = ss.timer
    if not t:
        return False
    ss.timer = None
    ss.alarma_hasta = time.time() + 8
    msg = "¡Tiempo! Terminó el temporizador de %s." % t["etiqueta"]
    decir(msg)
    st.toast("⏰ " + msg)
    registrar(origen, "Fin del temporizador", msg)
    return True


def poner_extractor(encendido=None, auto=False):
    ss = st.session_state
    puente = obtener_puente()
    if auto:
        ss.ext_modo = "Automático"
        puente.publicar(extractor_auto=True)
        return "Extractor en modo automático: se abre si hace mucho calor o el fogón está alto."
    ss.ext_modo = "Manual"
    ss.ext_on = bool(encendido)
    puente.publicar(extractor=bool(encendido))
    return "Extractor encendido." if encendido else "Extractor apagado."


def poner_umbral(valor):
    ss = st.session_state
    valor = float(max(20, min(90, valor)))
    ss.umbral = valor
    obtener_puente().publicar(umbral=valor)
    return "Umbral de temperatura en %d grados." % valor


def probar_buzzer():
    ok = obtener_puente().publicar(buzzer=True)
    return "Probando el buzzer." if ok else "No pude enviar la orden: el broker no está conectado."


def _consulta_sensor(clave, formato):
    puente = obtener_puente()
    if not puente.esp32_conectado():
        return "No tengo datos: el ESP32 está desconectado."
    v = puente.ultimo_estado().get(clave)
    return formato % v if v is not None else "No tengo ese dato todavía."


# ------------------------------------------------------------------ intérprete -> acción

def ejecutar(frase, modalidad):
    """Interpreta una frase (voz o texto), la ejecuta y responde por voz."""
    frase = (frase or "").strip()
    if not frase:
        return
    cmd = voz.interpretar(frase, receta())
    acc = cmd["accion"]
    ss = st.session_state

    if acc == "elegir_receta":
        resp = elegir_receta(cmd["receta"], cmd.get("empezar"))
    elif acc == "menu":
        ss.receta_id = None
        ss.paso = 0
        cancelar_timer(silencioso=True)
        enviar_paso()
        resp = "Elige una receta. " + nombres_recetas()
    elif acc == "empezar":
        if not receta():
            resp = "Primero elige una receta. " + nombres_recetas()
        elif ss.paso == 0 or terminada():
            resp = ir_a(1)
        else:
            resp = "Ya empezaste. " + texto_paso()
    elif acc == "siguiente":
        resp = siguiente()
    elif acc == "atras":
        resp = atras()
    elif acc == "repetir":
        resp = repetir()
    elif acc == "ir_paso":
        resp = ir_a(cmd["paso"]) if receta() else "Primero elige una receta."
    elif acc == "terminar":
        resp = ir_a(total_pasos() + 1) if receta() else "No hay receta en curso."
    elif acc == "ingredientes":
        resp = texto_ingredientes() if receta() else "Primero elige una receta. " + nombres_recetas()
    elif acc == "cantidad":
        ing = cmd.get("ingrediente")
        if not receta():
            resp = "Primero elige una receta."
        elif ing:
            resp = "Necesitas %s de %s." % (ing["cantidad"], ing["nombre"].lower())
        else:
            resp = "Ese ingrediente no está en esta receta. " + texto_ingredientes()
    elif acc == "timer":
        resp = iniciar_timer(cmd.get("segundos"))
    elif acc == "cancelar_timer":
        resp = cancelar_timer()
    elif acc == "consultar_timer":
        r = timer_restante()
        resp = ("Faltan %s." % voz.formato_duracion(int(r) + 1)) if r is not None else "No hay temporizador activo."
    elif acc == "extractor":
        resp = poner_extractor(encendido=cmd["encendido"])
    elif acc == "extractor_auto":
        resp = poner_extractor(auto=True)
    elif acc == "consultar_extractor":
        e = obtener_puente().ultimo_estado()
        resp = ("El extractor está %s, en modo %s." % ("abierto" if e.get("extractor") else "cerrado",
                                                       "automático" if e.get("extractor_auto", True) else "manual")
                if obtener_puente().esp32_conectado() else "No sé: el ESP32 está desconectado.")
    elif acc == "umbral":
        resp = poner_umbral(cmd["valor"])
    elif acc == "consultar_temperatura":
        resp = _consulta_sensor("temperatura", "La cocina está a %s grados.")
    elif acc == "consultar_humedad":
        resp = _consulta_sensor("humedad", "La humedad es de %s por ciento.")
    elif acc == "consultar_fogon":
        resp = _consulta_sensor("fogon", "El fogón está al %s por ciento.")
    elif acc == "buzzer":
        resp = probar_buzzer()
    elif acc == "ayuda":
        resp = voz.AYUDA
    else:
        resp = "No entendí «%s». Di «ayuda» para ver qué puedes decir." % frase

    registrar(modalidad, frase, resp)
    decir(resp)


def accion_boton(nombre, funcion, *args):
    """Para los botones en pantalla (callbacks on_click)."""
    resp = funcion(*args)
    registrar("Botón en pantalla", nombre, resp)
    decir(resp)


# ------------------------------------------------------------------ eventos del ESP32

def procesar_eventos():
    """Revisa eventos nuevos y temporizadores. Devuelve True si hay que redibujar la página."""
    ss = st.session_state
    puente = obtener_puente()
    cambio = False
    for ev in puente.eventos_desde(ss.ultimo_seq):
        ss.ultimo_seq = ev["seq"]
        tipo = ev.get("tipo")
        if tipo in ("siguiente", "atras"):
            if not receta():
                st.toast("Botón físico: primero elige una receta.")
                continue
            if tipo == "siguiente":
                resp = ir_a(1) if ss.paso == 0 else siguiente()
            else:
                resp = atras()
            registrar("Botón físico", "SIGUIENTE" if tipo == "siguiente" else "ATRÁS", resp)
            decir(resp)
            cambio = True
        elif tipo == "timer_fin":
            r = timer_restante()
            if r is not None and r <= 3:
                cambio = terminar_timer("ESP32") or cambio
        elif tipo == "alerta_temp":
            cambio = _avisar_alerta(ev.get("temperatura")) or cambio
        elif tipo == "conectado":
            enviar_paso()   # el ESP32 se (re)conectó: le mandamos el paso actual
            st.toast("ESP32 conectado")

    # temporizador local: funciona aunque el ESP32 esté desconectado (RNF5)
    r = timer_restante()
    if r is not None and r <= 0:
        espera = 2.5 if puente.esp32_conectado() else 0
        if r <= 0 and time.time() - ss.timer["fin"] >= espera:
            cambio = terminar_timer("Temporizador de la app") or cambio

    # alerta por el estado (por si el evento se perdió)
    e = puente.ultimo_estado()
    alerta = bool(e.get("alerta_temp")) and puente.esp32_conectado()
    if alerta and not ss.alerta_activa:
        cambio = _avisar_alerta(e.get("temperatura")) or cambio
    if not alerta and ss.alerta_activa:
        ss.alerta_activa = False
        cambio = True
    return cambio


def _avisar_alerta(temp):
    ss = st.session_state
    if ss.alerta_activa:
        return False
    ss.alerta_activa = True
    umbral = obtener_puente().ultimo_estado().get("umbral", ss.umbral)
    msg = "¡Atención! La temperatura llegó a %s grados y supera el umbral de %s." % (
        temp if temp is not None else "más", int(float(umbral)) if umbral is not None else "")
    decir(msg)
    st.toast("🔥 " + msg)
    registrar("ESP32", "Alerta de temperatura", msg)
    return True


# ------------------------------------------------------------------ tarjetas en vivo (dentro de fragmentos)

def tarjeta_timer():
    from ui import esc, icono
    ss = st.session_state
    r = timer_restante()
    if r is not None:
        t = ss.timer
        m, s = divmod(int(r + 0.999), 60)
        h, m = divmod(m, 60)
        reloj = ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))
        avance = 1 - (r / t["total"]) if t["total"] else 1
        st.markdown('<div class="blob-w peq"><div class="blob"><div class="fila">%s<div>'
                    '<div class="paso-num">Temporizador · %s</div><div class="timer">%s</div></div></div>'
                    '</div></div>' % (icono("reloj", 58), esc(t["etiqueta"]), reloj), unsafe_allow_html=True)
        st.progress(min(1.0, max(0.0, avance)))
        st.button("✖ Cancelar temporizador", key="btn_cancel_timer", use_container_width=True,
                  on_click=accion_boton, args=("Cancelar temporizador", cancelar_timer))
    elif time.time() < ss.alarma_hasta:
        st.markdown('<div class="blob-w peq alerta"><div class="blob alerta"><div class="fila">%s<div>'
                    '<div class="paso-num">Temporizador</div><div class="timer fin">¡TIEMPO!</div></div></div>'
                    '</div></div>' % icono("reloj", 58), unsafe_allow_html=True)
        if st.button("Apagar aviso", key="btn_apagar_aviso", use_container_width=True):
            ss.alarma_hasta = 0
            st.rerun()


def tarjeta_alerta():
    from ui import esc
    if not st.session_state.alerta_activa:
        return
    e = obtener_puente().ultimo_estado()
    st.markdown('<div class="blob-w peq alerta"><div class="blob alerta"><div class="h">🔥 Temperatura alta</div>'
                'La cocina está a <b>%s °C</b> y supera el umbral de %s °C. Revisa el fogón.'
                '</div></div>' % (esc(e.get("temperatura", "—")), esc(e.get("umbral", "—"))),
                unsafe_allow_html=True)

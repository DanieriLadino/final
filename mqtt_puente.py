"""Puente MQTT entre Streamlit y el ESP32.

Un único cliente MQTT corre en un hilo aparte (loop_start de paho) y se comparte
entre todas las páginas y sesiones con st.cache_resource. Guarda:
  - el último estado del ESP32,
  - un historial de las últimas 600 lecturas (para las gráficas),
  - los últimos 100 eventos con un número de secuencia, para que cada página
    procese solo los eventos nuevos.
"""
import json
import threading
import time
import uuid
from collections import deque

import paho.mqtt.client as mqtt
import streamlit as st

import config


class PuenteMQTT:
    def __init__(self):
        self._lock = threading.Lock()
        self.estado = {}
        self.t_estado = 0.0
        self.historial = deque(maxlen=600)
        self.eventos = deque(maxlen=100)
        self.comandos = deque(maxlen=50)
        self.seq = 0
        self.conectado = False
        self.error = ""

        self.cliente = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="chefml-app-" + uuid.uuid4().hex[:8],
        )
        self.cliente.on_connect = self._al_conectar
        self.cliente.on_disconnect = self._al_desconectar
        self.cliente.on_message = self._al_recibir
        self.cliente.reconnect_delay_set(min_delay=1, max_delay=5)
        try:
            self.cliente.connect_async(config.BROKER, config.PUERTO, keepalive=30)
            self.cliente.loop_start()
        except Exception as e:  # sin red: la app sigue funcionando (RNF5)
            self.error = str(e)

    # ---------- callbacks (hilo de paho) ----------
    def _al_conectar(self, cliente, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.conectado = False
            self.error = str(reason_code)
            return
        self.conectado = True
        self.error = ""
        cliente.subscribe([(config.TOPICO_ESTADO, 0), (config.TOPICO_EVENTO, 0)])

    def _al_desconectar(self, cliente, userdata, flags, reason_code, properties):
        self.conectado = False

    def _al_recibir(self, cliente, userdata, msg):
        try:
            datos = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        if not isinstance(datos, dict):
            return
        ahora = time.time()
        with self._lock:
            if msg.topic == config.TOPICO_ESTADO:
                self.estado = datos
                self.t_estado = ahora
                self.historial.append({
                    "hora": ahora,
                    "temperatura": _num(datos.get("temperatura")),
                    "humedad": _num(datos.get("humedad")),
                    "fogon": _num(datos.get("fogon")),
                })
            elif msg.topic == config.TOPICO_EVENTO:
                self.seq += 1
                datos["seq"] = self.seq
                datos["hora"] = ahora
                self.eventos.append(datos)

    # ---------- API para las páginas ----------
    def publicar(self, **cmd):
        """Publica un comando en /cmd. Devuelve True si salió hacia el broker."""
        cmd = {k: v for k, v in cmd.items() if v is not None}
        with self._lock:
            self.comandos.append({"hora": time.time(), **cmd})
        if not self.conectado:
            return False
        try:
            r = self.cliente.publish(config.TOPICO_CMD, json.dumps(cmd, ensure_ascii=False), qos=0)
            return r.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            return False

    def esp32_conectado(self):
        return self.t_estado > 0 and (time.time() - self.t_estado) < config.SEGUNDOS_ESP32_VIVO

    def ultimo_estado(self):
        with self._lock:
            return dict(self.estado)

    def ultimo_seq(self):
        with self._lock:
            return self.seq

    def eventos_desde(self, seq):
        with self._lock:
            return [e for e in self.eventos if e["seq"] > seq]

    def lista_eventos(self):
        with self._lock:
            return list(self.eventos)

    def lista_historial(self):
        with self._lock:
            return list(self.historial)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@st.cache_resource(show_spinner=False)
def obtener_puente():
    return PuenteMQTT()

"""Imita al ESP32 de Wokwi para probar la app sin la simulación.

Habla por MQTT exactamente igual que el firmware (mismos tópicos y JSON):
  - publica /estado cada 2 s y /evento cuando "presionas" un botón o termina el timer,
  - obedece los comandos de /cmd (paso, timer, extractor, umbral, buzzer, fin).

Uso desde la terminal:   python simulador_esp32.py
   n = botón SIGUIENTE   a = botón ATRÁS   + / - = perilla del fogón   q = salir
También se puede encender desde la barra lateral de la app ("ESP32 simulado").
No lo uses al mismo tiempo que Wokwi con el mismo tópico.
"""
import json
import random
import threading
import time
import unicodedata
import uuid

import paho.mqtt.client as mqtt

import config


def _sin_tildes(texto):
    texto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in texto if unicodedata.category(c) != "Mn" and ord(c) < 128)


class SimuladorESP32:
    def __init__(self):
        self.fogon = 0
        self.temperatura = 22.0
        self.humedad = 52.0
        self.receta = ""
        self.paso = 0
        self.total = 0
        self.texto = ""
        self.umbral = config.UMBRAL_TEMPERATURA
        self.extractor = False
        self.extractor_auto = True
        self.alerta = False
        self.timer_fin = 0.0
        self.led_rojo_hasta = 0.0
        self.ultimo_pitido = 0.0
        self.ultimo_pitido_desc = ""
        self.fin = False
        self.lcd = ["", ""]
        self._scroll = 0
        self._corriendo = False
        self._hilo = None
        self.cliente = None
        self.conectado = False

    # ------------------------------------------------------------ ciclo
    def iniciar(self):
        if self._corriendo:
            return
        self._corriendo = True
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                   client_id="chefml-sim-" + uuid.uuid4().hex[:8])
        self.cliente.on_connect = self._al_conectar
        self.cliente.on_disconnect = lambda *a: setattr(self, "conectado", False)
        self.cliente.on_message = self._al_recibir
        self.cliente.reconnect_delay_set(1, 5)
        self.cliente.connect_async(config.BROKER, config.PUERTO, 30)
        self.cliente.loop_start()
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def detener(self):
        self._corriendo = False
        if self.cliente:
            try:
                self.cliente.loop_stop()
                self.cliente.disconnect()
            except Exception:
                pass
        self.conectado = False

    @property
    def corriendo(self):
        return self._corriendo

    def _al_conectar(self, cliente, userdata, flags, rc, props):
        if rc.is_failure:
            return
        self.conectado = True
        cliente.subscribe(config.TOPICO_CMD)
        self._evento("conectado")

    def _bucle(self):
        ultimo_estado = 0.0
        ultimo_scroll = 0.0
        while self._corriendo:
            ahora = time.time()
            # temporizador sin bloquear
            if self.timer_fin and ahora >= self.timer_fin:
                self.timer_fin = 0.0
                self.led_rojo_hasta = ahora + 5
                self._pitar("timer terminado")
                self._evento("timer_fin")
            if ahora - ultimo_scroll >= 0.4:
                ultimo_scroll = ahora
                self._scroll += 1
                self._actualizar_lcd()
            if ahora - ultimo_estado >= 2:
                ultimo_estado = ahora
                self._leer_sensores()
                self._publicar_estado()
            time.sleep(0.1)

    # ------------------------------------------------------------ sensores
    def _leer_sensores(self):
        objetivo_t = 22 + self.fogon * 0.38 - (4 if self.extractor else 0)
        self.temperatura += (objetivo_t - self.temperatura) * 0.25 + random.uniform(-0.25, 0.25)
        objetivo_h = 50 + self.fogon * 0.22 - (8 if self.extractor else 0)
        self.humedad += (objetivo_h - self.humedad) * 0.2 + random.uniform(-0.5, 0.5)
        self.humedad = max(0, min(100, self.humedad))

        alerta = self.temperatura > self.umbral
        if alerta and not self.alerta:
            self._pitar("alerta de temperatura")
            self._evento("alerta_temp", temperatura=round(self.temperatura, 1))
        self.alerta = alerta
        if self.extractor_auto:
            self.extractor = alerta or self.fogon > 70

    def _publicar_estado(self):
        if not self.conectado:
            return
        restante = max(0, int(round(self.timer_fin - time.time()))) if self.timer_fin else 0
        estado = {
            "temperatura": round(self.temperatura, 1),
            "humedad": round(self.humedad, 1),
            "fogon": int(self.fogon),
            "receta": self.receta,
            "paso": self.paso,
            "total": self.total,
            "extractor": self.extractor,
            "extractor_auto": self.extractor_auto,
            "alerta_temp": self.alerta,
            "umbral": self.umbral,
            "timer_restante": restante,
            "simulado": True,
        }
        self.cliente.publish(config.TOPICO_ESTADO, json.dumps(estado))

    def _evento(self, tipo, **extra):
        if self.conectado:
            self.cliente.publish(config.TOPICO_EVENTO, json.dumps({"tipo": tipo, **extra}))

    # ------------------------------------------------------------ actuadores
    def _pitar(self, desc):
        self.ultimo_pitido = time.time()
        self.ultimo_pitido_desc = desc

    @property
    def led_verde(self):
        return self.conectado and not self.alerta

    @property
    def led_rojo(self):
        return self.alerta or time.time() < self.led_rojo_hasta

    @property
    def servo(self):
        return 90 if self.extractor else 0

    def _actualizar_lcd(self):
        if self.fin:
            l1 = "Buen provecho!"
        elif self.total:
            l1 = _sin_tildes("P%d/%d %s" % (self.paso, self.total, self.texto)) if self.paso else _sin_tildes(self.texto)
        else:
            l1 = "Chef Manos Libre"
        if len(l1) > 16:
            l1p = l1 + "   "
            i = self._scroll % len(l1p)
            l1 = (l1p + l1p)[i:i + 16]
        if self.alerta:
            l2 = "ALERTA %4.1fC" % self.temperatura
        elif self.timer_fin:
            r = max(0, int(self.timer_fin - time.time()))
            l2 = "Timer %02d:%02d" % divmod(r, 60)
        else:
            l2 = "T:%4.1fC F:%3d%%" % (self.temperatura, self.fogon)
        self.lcd = [l1[:16].ljust(16), l2[:16].ljust(16)]

    # ------------------------------------------------------------ comandos
    def _al_recibir(self, cliente, userdata, msg):
        try:
            cmd = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        if "texto" in cmd:
            self.texto = cmd.get("texto", "")
            self.paso = int(cmd.get("paso", self.paso))
            self.total = int(cmd.get("total", self.total))
            self.receta = cmd.get("receta", self.receta)
            self.fin = False
            self._pitar("confirmacion")
        if "timer" in cmd:
            s = int(cmd["timer"])
            self.timer_fin = time.time() + s if s > 0 else 0.0
            self._pitar("timer iniciado" if s > 0 else "timer cancelado")
        if "extractor_auto" in cmd:
            self.extractor_auto = bool(cmd["extractor_auto"])
        if "extractor" in cmd:
            self.extractor_auto = False
            self.extractor = bool(cmd["extractor"])
        if "umbral" in cmd:
            self.umbral = float(cmd["umbral"])
        if cmd.get("buzzer"):
            self._pitar("prueba de buzzer")
        if cmd.get("fin"):
            self.fin = True
            self.timer_fin = 0.0
            self._pitar("melodia final")
        self._actualizar_lcd()
        self._publicar_estado()

    # ------------------------------------------------------------ botones físicos
    def presionar(self, tipo):
        """tipo: 'siguiente' o 'atras' (como los pulsadores verde y azul)."""
        self._pitar("boton " + tipo)
        self._evento(tipo)


def _obtener_para_streamlit():
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def _sim():
        return SimuladorESP32()
    return _sim()


obtener_simulador = _obtener_para_streamlit


if __name__ == "__main__":
    sim = SimuladorESP32()
    sim.iniciar()
    print("ESP32 simulado en", config.BROKER, "tópico", config.TOPICO_BASE)
    print("n = siguiente, a = atrás, + / - = fogón, q = salir (Enter después de cada tecla)")
    try:
        while True:
            k = input("> ").strip().lower()
            if k == "q":
                break
            if k == "n":
                sim.presionar("siguiente")
            elif k == "a":
                sim.presionar("atras")
            elif k in ("+", "-"):
                sim.fogon = max(0, min(100, sim.fogon + (10 if k == "+" else -10)))
            print("LCD |%s|\n    |%s|  fogón %d%%  temp %.1f°C  extractor %s" % (
                sim.lcd[0], sim.lcd[1], sim.fogon, sim.temperatura, "abierto" if sim.extractor else "cerrado"))
    finally:
        sim.detener()

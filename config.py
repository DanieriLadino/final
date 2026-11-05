"""Configuración compartida de Chef Manos Libres.

Los valores se pueden cambiar con variables de entorno sin tocar el código.
El tópico base debe ser EXACTAMENTE el mismo que en el firmware del ESP32.
"""
import os

BROKER = os.getenv("CHEF_BROKER", "broker.hivemq.com")
PUERTO = int(os.getenv("CHEF_PUERTO", "1883"))
TOPICO_BASE = os.getenv("CHEF_TOPICO", "chefmanoslibres/grupo1")

TOPICO_ESTADO = TOPICO_BASE + "/estado"   # ESP32 -> App, cada 2 s
TOPICO_EVENTO = TOPICO_BASE + "/evento"   # ESP32 -> App, al ocurrir
TOPICO_CMD = TOPICO_BASE + "/cmd"         # App -> ESP32

# Si no llega un estado en este tiempo, el ESP32 se considera desconectado.
SEGUNDOS_ESP32_VIVO = 6

UMBRAL_TEMPERATURA = 45.0  # °C, valor inicial

"""Pruebas del intérprete de comandos: python test_interprete.py"""
from recetas import por_id
from voz import interpretar, duracion_en_segundos

arepas = por_id("arepas")
CASOS = [
    ("Siguiente", {"accion": "siguiente"}),
    ("listo, ¿qué sigue?", {"accion": "siguiente"}),
    ("vuelve al paso anterior", {"accion": "atras"}),
    ("¿Me lo repites otra vez?", {"accion": "repetir"}),
    ("¿Qué ingredientes necesito?", {"accion": "ingredientes"}),
    ("¿Cuánta harina?", {"accion": "cantidad"}),
    ("¿cuánta sal le echo?", {"accion": "cantidad"}),
    ("pon el temporizador", {"accion": "timer", "segundos": None}),
    ("temporizador de un minuto", {"accion": "timer", "segundos": 60}),
    ("pon una alarma para 5 minutos", {"accion": "timer", "segundos": 300}),
    ("avísame en minuto y medio", {"accion": "timer", "segundos": 90}),
    ("temporizador de dos minutos y treinta segundos", {"accion": "timer", "segundos": 150}),
    ("pon un temporizador de media hora", {"accion": "timer", "segundos": 1800}),
    ("cancela el temporizador", {"accion": "cancelar_timer"}),
    ("enciende el extractor", {"accion": "extractor", "encendido": True}),
    ("apaga el ventilador", {"accion": "extractor", "encendido": False}),
    ("pon el extractor en automático", {"accion": "extractor_auto"}),
    ("¿Qué temperatura hay?", {"accion": "consultar_temperatura"}),
    ("¿cómo está la humedad?", {"accion": "consultar_humedad"}),
    ("sube el umbral a cincuenta grados", {"accion": "umbral", "valor": 50}),
    ("prueba el sonido", {"accion": "buzzer"}),
    ("quiero hacer arepas", {"accion": "elegir_receta", "receta": "arepas"}),
    ("empezar", {"accion": "empezar"}),
    ("ve al paso 3", {"accion": "ir_paso", "paso": 3}),
    ("bla bla", {"accion": "desconocido"}),
]

ok = 0
for frase, esperado in CASOS:
    r = interpretar(frase, arepas)
    bien = all(r.get(k) == v for k, v in esperado.items())
    ok += bien
    print("OK " if bien else "MAL", frase, "->", {k: (v["nombre"] if isinstance(v, dict) else v) for k, v in r.items()})
print("\n%d de %d frases correctas" % (ok, len(CASOS)))
assert duracion_en_segundos("3 minutos") == 180
raise SystemExit(0 if ok == len(CASOS) else 1)

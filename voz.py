"""Intérprete de comandos en español y texto a voz (gTTS).

interpretar(frase, receta) normaliza la frase (minúsculas, sin tildes ni signos)
y busca palabras clave. Devuelve un diccionario {"accion": ..., ...}.
Sirve igual para la voz y para el texto escrito.
"""
import io
import re
import unicodedata

import streamlit as st

from recetas import RECETAS

# ---------------------------------------------------------------- normalizar

def normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9ñ ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _tiene(texto, *frases):
    """True si alguna frase aparece como palabra(s) completa(s)."""
    for f in frases:
        if re.search(r"\b" + re.escape(f) + r"\b", texto):
            return True
    return False


def _empieza(tokens, *prefijos):
    return any(t.startswith(p) for t in tokens for p in prefijos)


# ---------------------------------------------------------------- números

_NUMEROS = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiun": 21, "veintiuno": 21, "veintiuna": 21,
    "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100, "ciento": 100,
}
_UNIDADES = {
    "segundo": 1, "segundos": 1, "seg": 1,
    "minuto": 60, "minutos": 60, "min": 60, "minutitos": 60, "minutito": 60,
    "hora": 3600, "horas": 3600,
}


def duracion_en_segundos(texto):
    """'un minuto y medio' -> 90, 'temporizador de 5' -> 300, sin número -> None."""
    tokens = normalizar(texto).split()
    total = 0.0
    actual = None
    ultima_unidad = None
    hubo_numero = False
    for i, t in enumerate(tokens):
        siguiente = tokens[i + 1] if i + 1 < len(tokens) else ""
        if t in ("un", "una", "uno") and siguiente not in _UNIDADES:
            continue  # artículo ("una alarma"), no número
        if t.isdigit():
            actual = (actual or 0) + int(t)
            hubo_numero = True
        elif t in _NUMEROS:
            actual = (actual or 0) + _NUMEROS[t]
            hubo_numero = True
        elif t in ("medio", "media"):
            if actual is None and ultima_unidad is None:
                actual = 0.5          # "media hora", "medio minuto"
            elif ultima_unidad:
                total += ultima_unidad / 2   # "un minuto y medio"
            hubo_numero = True
        elif t in _UNIDADES:
            u = _UNIDADES[t]
            total += (actual if actual is not None else 1) * u
            ultima_unidad = u
            actual = None
            hubo_numero = True
    if actual is not None:            # número sin unidad: se asume minutos
        total += actual * 60
    if not hubo_numero or total <= 0:
        return None
    return int(round(total))


def formato_duracion(segundos):
    segundos = int(segundos)
    m, s = divmod(segundos, 60)
    h, m = divmod(m, 60)
    partes = []
    if h:
        partes.append("%d hora%s" % (h, "" if h == 1 else "s"))
    if m:
        partes.append("%d minuto%s" % (m, "" if m == 1 else "s"))
    if s:
        partes.append("%d segundo%s" % (s, "" if s == 1 else "s"))
    if not partes:
        return "0 segundos"
    return " y ".join([", ".join(partes[:-1]), partes[-1]]) if len(partes) > 1 else partes[0]


# ---------------------------------------------------------------- intérprete

_PAL_TIMER = ("temporizador", "temporizadores", "alarma", "timer", "cronometro", "cuenta regresiva", "avisame", "reloj")
_PAL_CANCELAR = ("cancela", "cancelar", "parar", "deten", "detener", "quita", "quitar", "apaga",
                 "apagar", "borra", "anula", "stop", "elimina", "silencia", "desactiva")
_PAL_EXTRACTOR = ("extractor", "ventilador", "campana", "ventilacion", "humo")
_PAL_ENCENDER = ("enciende", "encender", "prende", "prender", "abre", "abrir", "activa", "activar",
                 "arranca", "pon", "poner", "enciendeme", "prendeme")
_PAL_APAGAR = ("apaga", "apagar", "cierra", "cerrar", "desactiva", "desactivar", "deten", "detener",
               "quita", "quitar", "parar")
_PAL_CANTIDAD = ("cuanto", "cuanta", "cuantos", "cuantas", "cantidad", "que tanto", "que tanta")

_NOMBRES_RECETA = {
    "arepas": ("arepa", "arepas"),
    "pericos": ("perico", "pericos", "huevos pericos", "revueltos"),
    "panqueques": ("panqueque", "panqueques", "pancake", "pancakes", "tortitas"),
    "pasta": ("pasta", "espagueti", "espaguetis", "pomodoro", "spaghetti"),
}


def _primer_numero(tokens):
    actual = None
    for t in tokens:
        if t.isdigit():
            return int(t)
        if t in _NUMEROS and t not in ("un", "una"):
            actual = (actual or 0) + _NUMEROS[t]
        elif actual is not None and t != "y":
            break
    return actual


def _buscar_ingrediente(texto, receta):
    if not receta:
        return None
    tokens = texto.split()
    for ing in receta["ingredientes"]:
        for clave in ing["claves"]:
            if clave in tokens or (clave + "s") in tokens:
                return ing
    return None


def _buscar_receta(texto):
    for rid, nombres in _NOMBRES_RECETA.items():
        if _tiene(texto, *nombres):
            return rid
    return None


def interpretar(frase, receta=None):
    t = normalizar(frase)
    tokens = t.split()
    if not t:
        return {"accion": "nada"}

    if _tiene(t, "ayuda", "que puedo decir", "comandos", "que puedes hacer"):
        return {"accion": "ayuda"}

    # ---- temporizador
    if _tiene(t, *_PAL_TIMER) or (_tiene(t, "avisa", "avisame") and duracion_en_segundos(t)):
        if _tiene(t, *_PAL_CANCELAR):
            return {"accion": "cancelar_timer"}
        if _tiene(t, "cuanto falta", "cuanto queda", "cuanto tiempo"):
            return {"accion": "consultar_timer"}
        return {"accion": "timer", "segundos": duracion_en_segundos(t)}

    # ---- extractor
    if _tiene(t, *_PAL_EXTRACTOR):
        if _empieza(tokens, "automatic", "auto"):
            return {"accion": "extractor_auto"}
        if _tiene(t, *_PAL_APAGAR):
            return {"accion": "extractor", "encendido": False}
        if _tiene(t, *_PAL_ENCENDER):
            return {"accion": "extractor", "encendido": True}
        return {"accion": "consultar_extractor"}

    # ---- cantidad de un ingrediente
    if _tiene(t, *_PAL_CANTIDAD):
        ing = _buscar_ingrediente(t, receta)
        if ing:
            return {"accion": "cantidad", "ingrediente": ing}

    # ---- umbral de temperatura
    if _tiene(t, "umbral", "limite", "temperatura maxima", "maximo"):
        n = _primer_numero(tokens)
        if n is not None:
            return {"accion": "umbral", "valor": n}

    # ---- sensores
    if _tiene(t, "temperatura", "calor", "caliente", "grados"):
        return {"accion": "consultar_temperatura"}
    if _tiene(t, "humedad", "humeda"):
        return {"accion": "consultar_humedad"}
    if _tiene(t, "fogon", "estufa", "perilla", "llama"):
        return {"accion": "consultar_fogon"}

    # ---- buzzer
    if _tiene(t, "buzzer", "pitido", "pita", "suena", "sonar", "prueba el sonido", "prueba la alarma", "bocina"):
        return {"accion": "buzzer"}

    # ---- cantidad sin ingrediente reconocido
    if _tiene(t, *_PAL_CANTIDAD) and receta:
        return {"accion": "cantidad", "ingrediente": None}

    # ---- elegir receta / menú
    rid = _buscar_receta(t)
    if rid and (_tiene(t, "hacer", "preparar", "cocinar", "receta", "elige", "elegir", "quiero",
                       "cocinemos", "hagamos", "abre", "abrir", "empezar", "empecemos", "vamos") or len(tokens) <= 3):
        return {"accion": "elegir_receta", "receta": rid,
                "empezar": _empieza(tokens, "empez", "empec", "comenz", "inici")}
    if _tiene(t, "menu", "otra receta", "cambiar receta", "cambia la receta", "lista de recetas", "ver recetas",
              "volver al inicio"):
        return {"accion": "menu"}

    if _tiene(t, "ingrediente", "ingredientes", "que necesito", "que lleva", "que se necesita"):
        return {"accion": "ingredientes"}

    m = re.search(r"\bpaso (\d+|" + "|".join(_NUMEROS) + r")\b", t)
    if m and _tiene(t, "ve al", "ir al", "vete al", "salta al", "llevame al", "muestrame el", "pasa al"):
        v = m.group(1)
        return {"accion": "ir_paso", "paso": int(v) if v.isdigit() else _NUMEROS[v]}

    # ---- navegación
    if _empieza(tokens, "empez", "empec", "comenz", "comienz", "inici") or _tiene(t, "arranca", "vamos", "dale"):
        return {"accion": "empezar"}
    if _tiene(t, "terminar", "finalizar", "termine la receta", "acabe", "fin"):
        return {"accion": "terminar"}
    if _tiene(t, "siguiente", "sigue", "seguir", "avanza", "avanzar", "adelante", "proximo", "listo", "lista",
              "ya esta", "ya termine", "continua", "continuar", "next", "hecho", "ok"):
        return {"accion": "siguiente"}
    if _tiene(t, "atras", "anterior", "regresa", "regresar", "devuelve", "devuelvete", "volver", "vuelve",
              "retrocede", "retroceder"):
        return {"accion": "atras"}
    if _tiene(t, "repite", "repetir", "repiteme", "otra vez", "de nuevo", "no escuche", "que dijiste",
              "no entendi", "como dijiste", "lee", "leer"):
        return {"accion": "repetir"}

    return {"accion": "desconocido", "frase": frase}


AYUDA = ("Puedes decir: siguiente, atrás, repetir, ingredientes, "
         "cuánta sal, pon un temporizador de cinco minutos, cancela el temporizador, "
         "enciende el extractor o qué temperatura hay.")


# ---------------------------------------------------------------- texto a voz

@st.cache_data(show_spinner=False, max_entries=300)
def _mp3(texto):
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(texto, lang="es", tld="com.mx").write_to_fp(buf)
    return buf.getvalue()


def sintetizar(texto, nonce=0):
    """Devuelve el MP3 del texto (o None si no hay internet).

    Se le agrega una etiqueta ID3v1 con un número único para que cada frase
    sea un archivo distinto y el navegador la reproduzca aunque se repita.
    """
    try:
        datos = _mp3(texto)
    except Exception:
        return None
    titulo = ("chefml-%d" % nonce).encode("ascii")[:30].ljust(30, b"\0")
    etiqueta = b"TAG" + titulo + b"\0" * 30 + b"\0" * 30 + b"2026" + b"\0" * 30 + b"\xff"
    return datos + etiqueta

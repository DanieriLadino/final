"""Datos de las recetas.

Cada ingrediente tiene "claves": palabras (sin tildes, en minúscula) con las que
el usuario lo puede nombrar al preguntar "¿cuánta sal?".
Cada paso puede tener "timer" en segundos; el comando "pon el temporizador"
sin número usa ese valor.
"""

RECETAS = [
    {
        "id": "arepas",
        "nombre": "Arepas con queso",
        "icono": "queso",
        "porciones": 4,
        "tiempo": "30 min",
        "dificultad": "Fácil",
        "descripcion": "Arepas de maíz rellenas de queso, doradas en sartén.",
        "ingredientes": [
            {"nombre": "Harina de maíz precocida", "cantidad": "2 tazas", "claves": ["harina", "maiz", "masa"]},
            {"nombre": "Agua tibia", "cantidad": "2 tazas y media", "claves": ["agua"]},
            {"nombre": "Sal", "cantidad": "1 cucharadita", "claves": ["sal"]},
            {"nombre": "Queso mozzarella rallado", "cantidad": "1 taza", "claves": ["queso", "mozzarella"]},
            {"nombre": "Mantequilla", "cantidad": "2 cucharadas", "claves": ["mantequilla", "margarina"]},
        ],
        "pasos": [
            {"texto": "En un tazón mezcla la harina de maíz con la sal."},
            {"texto": "Agrega el agua tibia poco a poco y amasa hasta tener una masa suave."},
            {"texto": "Deja reposar la masa tapada durante 5 minutos.", "timer": 300},
            {"texto": "Agrega el queso rallado a la masa y amasa otra vez para repartirlo."},
            {"texto": "Forma 8 bolitas y aplánalas hasta que tengan un centímetro de grosor."},
            {"texto": "Calienta la sartén a fuego medio con un poco de mantequilla."},
            {"texto": "Cocina las arepas 6 minutos por cada lado hasta que estén doradas.", "timer": 360},
            {"texto": "Sirve calientes con un poco de mantequilla encima."},
        ],
    },
    {
        "id": "pericos",
        "nombre": "Huevos pericos",
        "icono": "huevo",
        "porciones": 2,
        "tiempo": "15 min",
        "dificultad": "Fácil",
        "descripcion": "El desayuno colombiano: huevos revueltos con tomate y cebolla.",
        "ingredientes": [
            {"nombre": "Huevos", "cantidad": "4 huevos", "claves": ["huevo", "huevos"]},
            {"nombre": "Tomate maduro picado", "cantidad": "1 tomate", "claves": ["tomate", "tomates"]},
            {"nombre": "Cebolla larga picada", "cantidad": "2 tallos", "claves": ["cebolla", "cebollas"]},
            {"nombre": "Aceite", "cantidad": "1 cucharada", "claves": ["aceite"]},
            {"nombre": "Sal", "cantidad": "media cucharadita", "claves": ["sal"]},
        ],
        "pasos": [
            {"texto": "Pica finamente el tomate y la cebolla larga."},
            {"texto": "Calienta el aceite en una sartén a fuego medio."},
            {"texto": "Sofríe la cebolla y el tomate durante 3 minutos.", "timer": 180},
            {"texto": "Bate los huevos con la sal en un tazón."},
            {"texto": "Vierte los huevos en la sartén y revuelve suavemente durante 2 minutos.", "timer": 120},
            {"texto": "Sirve de inmediato, acompañados de arepa o pan."},
        ],
    },
    {
        "id": "panqueques",
        "nombre": "Panqueques esponjosos",
        "icono": "bowl",
        "porciones": 3,
        "tiempo": "25 min",
        "dificultad": "Fácil",
        "descripcion": "Panqueques suaves para el desayuno, con miel o frutas.",
        "ingredientes": [
            {"nombre": "Harina de trigo", "cantidad": "1 taza y media", "claves": ["harina", "trigo"]},
            {"nombre": "Leche", "cantidad": "1 taza y cuarto", "claves": ["leche"]},
            {"nombre": "Huevo", "cantidad": "1 huevo", "claves": ["huevo", "huevos"]},
            {"nombre": "Azúcar", "cantidad": "2 cucharadas", "claves": ["azucar"]},
            {"nombre": "Polvo de hornear", "cantidad": "1 cucharada", "claves": ["polvo", "hornear", "levadura"]},
            {"nombre": "Sal", "cantidad": "una pizca", "claves": ["sal"]},
            {"nombre": "Mantequilla derretida", "cantidad": "3 cucharadas", "claves": ["mantequilla"]},
        ],
        "pasos": [
            {"texto": "Mezcla la harina, el azúcar, el polvo de hornear y la sal en un tazón."},
            {"texto": "En otro tazón bate la leche, el huevo y la mantequilla derretida."},
            {"texto": "Une las dos mezclas y revuelve solo hasta integrar. Quedan grumitos y está bien."},
            {"texto": "Deja reposar la mezcla durante 5 minutos.", "timer": 300},
            {"texto": "Calienta la sartén a fuego medio bajo y engrásala un poco."},
            {"texto": "Vierte un cuarto de taza de mezcla y cocina 2 minutos hasta ver burbujas.", "timer": 120},
            {"texto": "Voltea el panqueque y cocina 1 minuto más.", "timer": 60},
            {"texto": "Sirve con miel, frutas o lo que más te guste."},
        ],
    },
    {
        "id": "pasta",
        "nombre": "Pasta al pomodoro",
        "icono": "tomate",
        "porciones": 2,
        "tiempo": "25 min",
        "dificultad": "Media",
        "descripcion": "Pasta con salsa casera de tomate, ajo y albahaca.",
        "ingredientes": [
            {"nombre": "Espagueti", "cantidad": "200 gramos", "claves": ["pasta", "espagueti", "espaguetis", "spaghetti"]},
            {"nombre": "Tomates maduros", "cantidad": "4 tomates", "claves": ["tomate", "tomates"]},
            {"nombre": "Ajo", "cantidad": "2 dientes", "claves": ["ajo", "ajos"]},
            {"nombre": "Aceite de oliva", "cantidad": "3 cucharadas", "claves": ["aceite", "oliva"]},
            {"nombre": "Albahaca fresca", "cantidad": "6 hojas", "claves": ["albahaca"]},
            {"nombre": "Sal", "cantidad": "1 cucharada para el agua y una pizca para la salsa", "claves": ["sal"]},
            {"nombre": "Queso parmesano", "cantidad": "al gusto", "claves": ["queso", "parmesano"]},
        ],
        "pasos": [
            {"texto": "Pon a hervir 2 litros de agua con una cucharada de sal."},
            {"texto": "Pica los tomates en cubos y lamina el ajo."},
            {"texto": "Sofríe el ajo en el aceite de oliva durante 1 minuto, sin que se queme.", "timer": 60},
            {"texto": "Agrega los tomates con una pizca de sal y cocina 10 minutos.", "timer": 600},
            {"texto": "Cocina la pasta en el agua hirviendo durante 9 minutos.", "timer": 540},
            {"texto": "Escurre la pasta y mézclala con la salsa y la albahaca."},
            {"texto": "Sirve con queso parmesano rallado por encima."},
        ],
    },
]


def por_id(receta_id):
    for r in RECETAS:
        if r["id"] == receta_id:
            return r
    return None

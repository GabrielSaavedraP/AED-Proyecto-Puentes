from manim import *
import csv
import math
import os
from collections import namedtuple
from pathlib import Path

import numpy as np

# Misma identidad visual que la animación de Skip List: fondo negro, paleta de
# Manim (BLUE_B, TEAL, YELLOW, GREEN, RED, GRAY_B) y tipografía serif.
FUENTE = "Times New Roman"

COLUMNAS = [
    "Iteracion", "Accion", "Nodo_Actual", "Nodo_Vecino",
    "Orden_Visita", "Low", "Tipo_Arista", "Resultado",
]

Evento = namedtuple("Evento", "iteracion accion nodo vecino tin low tipo resultado")

# Colores con significado
COLOR_TIN = BLUE_B
COLOR_LOW = GREEN
COLOR_ARBOL = BLUE_B
COLOR_RETROCESO = ORANGE
COLOR_PUENTE = RED

NODO_R = 0.34
ANILLO_R = 0.44
AREA_GRAFO = (-6.9, 3.85, -2.3, 2.2)  # xmin, xmax, ymin, ymax donde viven nodos y etiquetas
CENTRO_PANEL = np.array([5.45, 0.0, 0.0])


def Texto(contenido, **kwargs):
    """Text con la tipografía del proyecto (la misma del video de Skip List).

    Pango coloca mal los glifos a cuerpos pequeños ("quedaaislado"): se genera a
    10x y se reduce, lo que da el mismo tamaño visual con el espaciado correcto.
    Mientras se crea, se anula el ancho de página que Manim pasa a Pango; de lo
    contrario el texto a 10x se parte en varias líneas según la resolución."""
    kwargs.setdefault("font", FUENTE)
    tam = kwargs.pop("font_size", 48)
    ancho_pagina = config["pixel_width"]
    config["pixel_width"] = 100000
    try:
        texto = Text(contenido, font_size=tam * 10, **kwargs)
    finally:
        config["pixel_width"] = ancho_pagina
    texto.scale(0.1)
    return texto


# ======================================================================
# LECTURA Y VALIDACIÓN DEL CSV (única fuente de la animación)
# ======================================================================

def buscar_csv(nombre, variable):
    """Busca el CSV: 1) variable de entorno, 2) junto a este script,
    3) ../output/ (estructura del repositorio)."""
    aqui = Path(__file__).resolve().parent
    candidatos = []
    if os.environ.get(variable):
        candidatos.append(Path(os.environ[variable]))
    candidatos += [aqui / nombre, aqui.parent / "output" / nombre]
    for ruta in candidatos:
        if ruta.exists():
            return ruta
    raise FileNotFoundError(
        f"No se encontró {nombre}. Ejecuta primero el programa C++ (ver README) "
        f"o define {variable} con la ruta del archivo."
    )


def _entero(texto):
    return None if texto == "NULL" else int(texto)


class Corrida:
    """Ejecución del algoritmo leída del CSV. No recalcula nada: solo
    comprueba que los eventos sean coherentes entre sí."""

    def __init__(self, ruta):
        with open(ruta, newline="", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            if lector.fieldnames != COLUMNAS:
                raise ValueError(f"{ruta}: columnas inesperadas {lector.fieldnames}")
            self.eventos = [
                Evento(
                    int(f["Iteracion"]), f["Accion"], int(f["Nodo_Actual"]),
                    int(f["Nodo_Vecino"]), _entero(f["Orden_Visita"]),
                    _entero(f["Low"]), f["Tipo_Arista"], f["Resultado"],
                )
                for f in lector
            ]
        if not self.eventos:
            raise ValueError(f"{ruta}: el archivo está vacío.")
        self.ruta = ruta
        self._validar()

    def _validar(self):
        ev = self.eventos
        if ev[-1].accion != "FIN":
            raise ValueError("El CSV no termina con FIN.")
        self.nodos = [e.nodo for e in ev if e.accion == "CREAR_NODO"]
        self.aristas = [(e.nodo, e.vecino) for e in ev if e.accion == "CREAR_ARISTA"]
        self.puentes = [(e.nodo, e.vecino) for e in ev if e.accion == "MARCAR_PUENTE"]

        tin, low, pila = {}, {}, []
        self.profundidad = 0
        self.evaluaciones = []  # (u, v, tin[u], low[v], es_puente) al volver de cada hijo
        marcados = []
        for e in ev:
            if e.accion == "VISITAR":
                if e.nodo in tin:
                    raise ValueError(f"Nodo {e.nodo} visitado dos veces.")
                esperado = pila[-1] if pila else -1
                if e.vecino != esperado:
                    raise ValueError(f"VISITAR {e.nodo}: padre {e.vecino}, se esperaba {esperado}.")
                tin[e.nodo], low[e.nodo] = e.tin, e.low
                pila.append(e.nodo)
                self.profundidad = max(self.profundidad, len(pila))
            elif e.accion == "ACTUALIZAR_LOW":
                if e.low is None or e.low >= low[e.nodo]:
                    raise ValueError(f"ACTUALIZAR_LOW {e.nodo} no reduce low.")
                low[e.nodo] = e.low
            elif e.accion == "RETROCEDER":
                if not pila or pila[-1] != e.nodo or low[e.nodo] != e.low:
                    raise ValueError(f"RETROCEDER {e.nodo} inconsistente con la pila o con low.")
                pila.pop()
                if e.vecino >= 0:
                    self.evaluaciones.append(
                        (e.vecino, e.nodo, tin[e.vecino], e.low, e.low > tin[e.vecino])
                    )
            elif e.accion == "MARCAR_PUENTE":
                if not (e.low > tin[e.nodo]):
                    raise ValueError(f"MARCAR_PUENTE ({e.nodo},{e.vecino}) no cumple low[v] > tin[u].")
                marcados.append((e.nodo, e.vecino))
        if pila:
            raise ValueError("El CSV termina con nodos sin cerrar en la pila de DFS.")
        esperados = [(u, v) for u, v, _, _, es in self.evaluaciones if es]
        if marcados != esperados:
            raise ValueError("Los MARCAR_PUENTE no coinciden con la condición low[v] > tin[u].")
        if sorted(tin) != sorted(self.nodos):
            raise ValueError("No todos los nodos creados fueron visitados.")
        self.tin_final = tin
        self.low_final = low


# ======================================================================
# GEOMETRÍA: DISPOSICIÓN DEL GRAFO Y COLOCACIÓN DE ETIQUETAS
# ======================================================================

# Disposiciones hechas a mano para los grafos de la demostración. Se eligen por
# la estructura del grafo leído del CSV; cualquier otro grafo usa una disposición
# circular automática.
_DISPOSICIONES = [
    (5, [(0, 1), (1, 2), (2, 0), (2, 3)],
     {0: (-4.5, 1.0), 1: (-4.5, -1.1), 2: (-1.9, -0.05), 3: (0.55, -0.05), 4: (2.75, 0.0)}),
    (5, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)],
     {0: (-1.4, 1.65), 1: (0.22, 0.48), 2: (-0.4, -1.43), 3: (-2.4, -1.43), 4: (-3.02, 0.48)}),
    (6, [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5)],
     {0: (-1.3, 1.35), 1: (-3.6, 0.1), 2: (1.0, 0.1), 3: (-4.9, -1.4), 4: (-2.3, -1.4), 5: (2.2, -1.4)}),
]


def disponer_grafo(nodos, aristas):
    clave = frozenset(frozenset(a) for a in aristas)
    for n, lista, posiciones in _DISPOSICIONES:
        if n == len(nodos) and frozenset(frozenset(a) for a in lista) == clave:
            return {u: np.array([x, y, 0.0]) for u, (x, y) in posiciones.items()}

    # Disposición automática: cada componente en una circunferencia, en fila.
    vecinos = {u: set() for u in nodos}
    for a, b in aristas:
        vecinos[a].add(b)
        vecinos[b].add(a)
    vistos, comps = set(), []
    for u in nodos:
        if u in vistos:
            continue
        comp, cola = [], [u]
        vistos.add(u)
        while cola:
            x = cola.pop(0)
            comp.append(x)
            for y in sorted(vecinos[x]):
                if y not in vistos:
                    vistos.add(y)
                    cola.append(y)
        comps.append(comp)
    ancho_total = sum(1.2 + 0.5 * len(c) for c in comps)
    x0 = (AREA_GRAFO[0] + AREA_GRAFO[1]) / 2 - ancho_total / 2
    posiciones = {}
    for comp in comps:
        radio = 0.4 + 0.45 * (len(comp) > 1) * len(comp) / 2
        cx = x0 + radio + 0.3
        for i, u in enumerate(comp):
            ang = math.pi / 2 - 2 * math.pi * i / len(comp)
            posiciones[u] = np.array([cx + (radio * math.cos(ang) if len(comp) > 1 else 0),
                                      radio * math.sin(ang) if len(comp) > 1 else 0, 0.0])
        x0 += 2 * radio + 0.9
    return posiciones


_ORDEN_ANGULOS = [90, 270, 0, 180, 45, 135, 225, 315, 60, 120, 240, 300, 30, 150, 210, 330,
                  75, 105, 255, 285, 15, 165, 195, 345]


def _toca_segmento(cx, cy, hw, hh, p, q, pad):
    for i in range(41):
        t = i / 40
        x = p[0] + (q[0] - p[0]) * t
        y = p[1] + (q[1] - p[1]) * t
        if abs(x - cx) <= hw + pad and abs(y - cy) <= hh + pad:
            return True
    return False


def _toca_circulo(cx, cy, hw, hh, c, r, pad):
    dx = max(abs(c[0] - cx) - hw, 0)
    dy = max(abs(c[1] - cy) - hh, 0)
    return math.hypot(dx, dy) < r + pad


def mejor_posicion(ancla, ancho, alto, posiciones, segmentos, rects, area=AREA_GRAFO,
                   radio_ancla=ANILLO_R, hueco=0.14):
    """Centro del rectángulo (ancho x alto) junto a `ancla` que no toca nodos,
    aristas ni otros rectángulos y queda dentro del área. Devuelve (x, y)."""
    hw, hh = ancho / 2, alto / 2
    mejor, mejor_costo = None, None
    for extra in (0.0, 0.15, 0.3, 0.5, 0.8, 1.1):
        for i, grados in enumerate(_ORDEN_ANGULOS):
            c, s = math.cos(math.radians(grados)), math.sin(math.radians(grados))
            sobresale = min(hw / abs(c) if abs(c) > 1e-9 else 1e9, hh / abs(s) if abs(s) > 1e-9 else 1e9)
            d = radio_ancla + hueco + sobresale + extra
            cx, cy = ancla[0] + d * c, ancla[1] + d * s
            costo = i * 0.02 + extra * 0.3
            if cx - hw < area[0] or cx + hw > area[1] or cy - hh < area[2] or cy + hh > area[3]:
                costo += 1000
            for p, q in segmentos:
                if _toca_segmento(cx, cy, hw, hh, p, q, 0.07):
                    costo += 100
            for pos in posiciones:
                if _toca_circulo(cx, cy, hw, hh, pos, ANILLO_R, 0.04):
                    costo += 100
            for (rx, ry, rw, rh) in rects:
                if abs(cx - rx) < hw + rw + 0.06 and abs(cy - ry) < hh + rh + 0.06:
                    costo += 100
            if mejor_costo is None or costo < mejor_costo:
                mejor, mejor_costo = (cx, cy), costo
        if mejor_costo is not None and mejor_costo < 50:
            break  # ya hay una posición limpia: no alejarse más de lo necesario
    return mejor


def colocar_etiquetas(posiciones, aristas, ancho, alto, area=AREA_GRAFO):
    """Posición de la etiqueta tin/low de cada nodo (evita aristas y nodos)."""
    segmentos = [(posiciones[a], posiciones[b]) for a, b in aristas if a != b]
    grado = {u: 0 for u in posiciones}
    for a, b in aristas:
        grado[a] += 1
        grado[b] += 1
    colocadas, rects = {}, []
    for u in sorted(posiciones, key=lambda x: (-grado[x], x)):
        cx, cy = mejor_posicion(posiciones[u], ancho, alto, list(posiciones.values()),
                                segmentos, rects, area)
        colocadas[u] = np.array([cx, cy, 0.0])
        rects.append((cx, cy, ancho / 2, alto / 2))
    return colocadas, rects


# ======================================================================
# PIEZAS VISUALES COMUNES
# ======================================================================

def hacer_nodo(u, pos):
    circulo = Circle(radius=NODO_R, color=BLUE, stroke_width=4)
    circulo.set_fill(BLACK, opacity=1)
    numero = Texto(str(u), font_size=24)
    numero.move_to(circulo)
    nodo = VGroup(circulo, numero)
    nodo.move_to(pos)
    nodo.set_z_index(1)
    return nodo


def _dir(a, b):
    d = np.array(b, dtype=float) - np.array(a, dtype=float)
    return d / np.linalg.norm(d)


def hacer_arista(a, b, color=GRAY_B, ancho=3.5):
    d = _dir(a, b)
    linea = Line(a + d * NODO_R, b - d * NODO_R, color=color, stroke_width=ancho)
    linea.set_z_index(-1)
    return linea


def hacer_flecha(a, b, color, ancho=5):
    d = _dir(a, b)
    flecha = Arrow(a + d * NODO_R, b - d * NODO_R, buff=0, color=color, stroke_width=ancho,
                   tip_length=0.26, max_tip_length_to_length_ratio=0.3)
    flecha.set_z_index(-0.5)
    return flecha


def hacer_retroceso(a, b, color=COLOR_RETROCESO):
    """Arista de retroceso: línea punteada con punta hacia el ancestro."""
    d = _dir(a, b)
    fin = b - d * NODO_R
    linea = DashedLine(a + d * NODO_R, fin - d * 0.18, color=color, stroke_width=4,
                       dash_length=0.13, dashed_ratio=0.6)
    punta = Triangle(fill_opacity=1, stroke_width=0, color=color).scale(0.13)
    punta.rotate(math.atan2(d[1], d[0]) - PI / 2)
    punta.move_to(fin - d * 0.1)
    grupo = VGroup(linea, punta)
    grupo.set_z_index(-0.5)
    return grupo


def marca_x(color=RED, escala=0.2):
    cruz = VGroup(Line([-0.5, -0.5, 0], [0.5, 0.5, 0]), Line([-0.5, 0.5, 0], [0.5, -0.5, 0]))
    cruz.set_color(color).set_stroke(width=5)
    return cruz.scale(escala)


def fila_etiqueta(nombre, valor, color, centro, tam=20):
    fila = Texto(f"{nombre} = {valor}", font_size=tam, color=color)
    fila.move_to(centro)
    fila.set_z_index(2)
    return fila


def medir_etiqueta():
    muestra = VGroup(Texto("tin = 88", font_size=20), Texto("low = 88", font_size=20))
    muestra.arrange(DOWN, buff=0.07)
    return muestra.width + 0.04, muestra.height + 0.04


def componentes(nodos, aristas, quitar=None):
    padre = {u: u for u in nodos}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for a, b in aristas:
        if quitar is not None and frozenset((a, b)) == frozenset(quitar):
            continue
        padre[raiz(a)] = raiz(b)
    grupos = {}
    for u in nodos:
        grupos.setdefault(raiz(u), []).append(u)
    return list(grupos.values())


# ======================================================================
# REPRODUCTOR DE EVENTOS: convierte cada fila del CSV en una animación
# ======================================================================

class Reproductor:

    def __init__(self, escena, corrida, rapido=False):
        self.s = escena
        self.c = corrida
        self.rapido = rapido
        self.k = 0.6 if rapido else 1.0

        self.pos = disponer_grafo(corrida.nodos, corrida.aristas)
        ancho, alto = medir_etiqueta()
        self.pos_etiqueta, rects = colocar_etiquetas(self.pos, corrida.aristas, ancho, alto)
        self.pos_tag = self._colocar_tags(rects)

        self.nodos = {}
        self.aristas = {}
        self.sup = {}          # flechas de árbol / aristas de retroceso encima de la arista base
        self.tags = {}
        self.etq_tin = {}
        self.etq_low = {}
        self.valor_tin = {}
        self.valor_low = {}
        self.pila = []
        self.paso_pila = min(0.52, 3.2 / max(1, corrida.profundidad))

        self.indicador = None
        self.estado = None
        self.fase = None
        self.contador = None
        self.cab_pila = None
        self.tarjeta = None
        self.pendiente = None
        self.largo_estado = 0
        self.t_desde_estado = 0.0
        self.hay_recorrido = False
        self.total = len(corrida.eventos)

    # ---------------------------------------------------------------- util

    def t(self, segundos):
        return max(0.15, segundos * self.k)

    def jugar(self, animaciones, segundos):
        animaciones = [a for a in animaciones if a is not None]
        if animaciones:
            self.t_desde_estado += self.t(segundos)
            self.s.play(*animaciones, run_time=self.t(segundos))

    def esperar(self, segundos):
        self.t_desde_estado += self.t(segundos)
        self.s.wait(self.t(segundos))

    def esperar_lectura(self, minimo=0.0):
        """Deja el mensaje inferior en pantalla el tiempo suficiente para leerlo."""
        caracteres_por_segundo = 24 if self.rapido else 19
        falta = max(self.largo_estado / caracteres_por_segundo - self.t_desde_estado, minimo)
        if falta > 0.01:
            self.s.wait(min(falta, 3.0))
            self.t_desde_estado += min(falta, 3.0)

    def _colocar_tags(self, rects):
        tags = {}
        segmentos = [(self.pos[a], self.pos[b]) for a, b in self.c.aristas if a != b]
        usados = list(rects)
        for u, v in self.c.puentes:
            medio = (self.pos[u] + self.pos[v]) / 2
            cx, cy = mejor_posicion(medio, 1.0, 0.36, list(self.pos.values()), segmentos, usados,
                                    radio_ancla=0.0, hueco=0.1)
            tags[frozenset((u, v))] = np.array([cx, cy, 0.0])
            usados.append((cx, cy, 0.5, 0.18))
        return tags

    def estado_anim(self, texto, color=WHITE):
        nuevo = Texto(texto, font_size=19, color=color)
        if nuevo.width > 12:
            nuevo.scale_to_fit_width(12)
        nuevo.move_to([0, -2.95, 0])
        viejo, self.estado = self.estado, nuevo
        self.largo_estado = len(texto)
        self.t_desde_estado = 0.0
        if viejo is None:
            return FadeIn(nuevo)
        return AnimationGroup(FadeOut(viejo), FadeIn(nuevo))

    def _texto_contador(self, ev):
        texto = Texto(f"Evento {ev.iteracion} de {self.total}", font_size=16, color=GRAY_B)
        texto.move_to([0, 2.32, 0])
        return texto

    def fase_anim(self, nombre, ev):
        texto = Texto(nombre, font_size=25, color=BLUE_B)
        texto.move_to([0, 2.65, 0])
        if self.fase is None:
            self.fase = texto
            self.contador = self._texto_contador(ev)
            return [FadeIn(self.fase), FadeIn(self.contador)]
        return [Transform(self.fase, texto)]

    def actualizar_contador(self, ev):
        if self.contador is not None:
            self.contador.become(self._texto_contador(ev))

    # ---------------------------------------------------------- indicador

    def indicador_anim(self, u):
        nuevo = Circle(radius=ANILLO_R, color=YELLOW, stroke_width=4)
        nuevo.move_to(self.pos[u])
        nuevo.set_z_index(3)
        if self.indicador is None:
            self.indicador = nuevo
            return Create(self.indicador)
        return Transform(self.indicador, nuevo)

    # -------------------------------------------------------------- pila

    def _posicion_pila(self, indice):
        return CENTRO_PANEL + np.array([0, -1.95 + indice * self.paso_pila, 0])

    def _caja_pila(self, u, indice):
        caja = RoundedRectangle(width=1.5, height=0.44, corner_radius=0.1, color=YELLOW)
        texto = Texto(f"DFS({u})", font_size=19)
        texto.move_to(caja)
        grupo = VGroup(caja, texto)
        grupo.move_to(self._posicion_pila(indice))
        return grupo

    def apilar(self, u):
        anims = []
        if self.pila:
            anims.append(self.pila[-1][1][0].animate.set_color(TEAL))
        caja = self._caja_pila(u, len(self.pila))
        self.pila.append((u, caja))
        anims.append(FadeIn(caja, shift=UP * 0.2))
        return anims

    def desapilar(self, u):
        anims = []
        if self.pila and self.pila[-1][0] == u:
            _, caja = self.pila.pop()
            anims.append(FadeOut(caja, shift=DOWN * 0.2))
            if self.pila:
                anims.append(self.pila[-1][1][0].animate.set_color(YELLOW))
        return anims

    # ------------------------------------------------------- etiquetas

    def crear_etiquetas(self, u, tin, low):
        centro = self.pos_etiqueta[u]
        fila_tin = fila_etiqueta("tin", tin, COLOR_TIN, centro + UP * 0.15)
        fila_low = fila_etiqueta("low", low, COLOR_LOW, centro + DOWN * 0.15)
        self.etq_tin[u], self.etq_low[u] = fila_tin, fila_low
        self.valor_tin[u], self.valor_low[u] = tin, low
        return fila_tin, fila_low

    def cambiar_low(self, u, valor):
        nuevo = fila_etiqueta("low", valor, COLOR_LOW, self.etq_low[u].get_center())
        self.valor_low[u] = valor
        return nuevo

    # ------------------------------------------------------- despacho

    def ejecutar(self):
        for ev in self.c.eventos:
            self.actualizar_contador(ev)
            self.antes(ev)
            getattr(self, "ev_" + ev.accion.lower())(ev)
            self.esperar_lectura(minimo=self.t(0.25))

    def antes(self, ev):
        """El C++ evalúa low[v] > tin[u] tras propagar low: si el evento siguiente no es
        parte de esa evaluación, la condición era falsa y se muestra aquí."""
        if self.pendiente is None:
            return
        _, hijo, _ = self.pendiente
        propaga = ev.accion == "ACTUALIZAR_LOW" and ev.tipo == "TREE_EDGE" and ev.vecino == hijo
        if ev.accion != "MARCAR_PUENTE" and not propaga:
            self.resolver_chequeo(False)

    # --------------------------------------------------------- eventos

    def ev_crear_nodo(self, ev):
        u = ev.nodo
        nodo = hacer_nodo(u, self.pos[u])
        self.nodos[u] = nodo
        anims = [self.estado_anim(f"Creamos el nodo {u}", BLUE_B), FadeIn(nodo, shift=UP * 0.18)]
        if self.fase is None:
            anims += self.fase_anim("Construcción del grafo", ev)
        self.jugar(anims, 0.4)

    def ev_crear_arista(self, ev):
        u, v = ev.nodo, ev.vecino
        clave = frozenset((u, v))
        if clave in self.aristas or u == v:
            self.jugar([self.estado_anim(f"Arista repetida o bucle ({u}, {v}): no se dibuja", GRAY_B)], 0.3)
            return
        linea = hacer_arista(self.pos[u], self.pos[v])
        self.aristas[clave] = linea
        self.jugar([self.estado_anim(f"Conectamos {u} y {v}", BLUE_A), Create(linea)], 0.5)

    def ev_visitar(self, ev):
        u, padre = ev.nodo, ev.vecino
        anims = []
        if not self.hay_recorrido:
            self.hay_recorrido = True
            anims += self.fase_anim("Recorrido DFS", ev)
            self.cab_pila = Texto("Pila DFS", font_size=18, color=GRAY_B)
            self.cab_pila.move_to(CENTRO_PANEL + np.array([0, -2.4, 0]))
            anims.append(FadeIn(self.cab_pila))
        circulo = self.nodos[u][0]
        anims.append(circulo.animate.set_stroke(TEAL).set_fill(TEAL, opacity=0.3))
        anims.append(self.indicador_anim(u))
        if padre >= 0 and frozenset((u, padre)) in self.sup:
            anims.append(self.sup[frozenset((u, padre))].animate.set_color(COLOR_ARBOL))
        anims += self.apilar(u)
        fila_tin, fila_low = self.crear_etiquetas(u, ev.tin, ev.low)
        anims += [FadeIn(fila_tin, scale=0.6), FadeIn(fila_low, scale=0.6)]
        if padre < 0:
            texto = f"Nueva raíz: DFS comienza en {u}   →   tin = low = {ev.tin}"
        else:
            texto = f"DFS descubre {u}   →   tin = low = {ev.tin}"
        anims.append(self.estado_anim(texto, TEAL))
        self.jugar(anims, 0.7)

        sig = self.c.eventos[self.c.eventos.index(ev) + 1]
        if padre < 0 and sig.accion == "RETROCEDER" and sig.nodo == u:
            self.caso_borde(f"Nodo {u} aislado: sin vecinos, es una componente de un solo nodo")

    def caso_borde(self, mensaje):
        etiqueta = Texto("CASO BORDE", font_size=22, color=RED)
        etiqueta.move_to([-4.9, 2.6, 0])
        self.jugar([FadeIn(etiqueta), self.estado_anim(mensaje, RED)], 0.4)
        self.esperar(1.4)
        self.jugar([FadeOut(etiqueta)], 0.3)

    def ev_explorar_arista(self, ev):
        u, v, tipo = ev.nodo, ev.vecino, ev.tipo
        clave = frozenset((u, v))
        if tipo == "TREE_EDGE":
            flecha = hacer_flecha(self.pos[u], self.pos[v], YELLOW)
            self.sup[clave] = flecha
            self.jugar([self.estado_anim(f"{u} → {v}: {v} no ha sido visitado   →   arista del árbol, avanzamos",
                                         YELLOW), Create(flecha)], 0.6)
        elif tipo == "PARENT":
            self.jugar([self.estado_anim(f"{v} es el padre de {u}: se ignora esa arista (no es un retroceso)",
                                         GRAY_B)], 0.3)
            self.marcar_ignorada(clave)
        elif tipo == "BACK_EDGE":
            retro = hacer_retroceso(self.pos[u], self.pos[v])
            self.sup[clave] = retro
            self.jugar([
                self.estado_anim(f"{u} → {v}: {v} ya fue visitado (tin = {self.valor_tin[v]})   →   arista de retroceso",
                                 COLOR_RETROCESO),
                self.aristas[clave].animate.set_stroke(opacity=0.25),
                Create(retro),
                Indicate(self.etq_tin[v], color=YELLOW, scale_factor=1.25),
            ], 0.7)
        elif tipo == "FORWARD_EDGE":
            self.jugar([self.estado_anim(
                f"{v} es descendiente de {u}: esa arista de retroceso ya se procesó desde {v}", GRAY_B)], 0.3)
            if clave in self.sup:
                self.jugar([Indicate(self.sup[clave], color=GRAY_B, scale_factor=1.0)], 0.5)
        else:  # SELF_LOOP u otros
            self.jugar([self.estado_anim(f"Arista ({u}, {v}) sin efecto: se ignora", GRAY_B)], 0.3)

    def marcar_ignorada(self, clave):
        u, v = tuple(clave)
        medio = (self.pos[u] + self.pos[v]) / 2
        cruz = marca_x(GRAY_B, 0.16).move_to(medio)
        cruz.set_z_index(2)
        self.jugar([FadeIn(cruz, scale=0.5)], 0.25)
        self.jugar([FadeOut(cruz)], 0.25)

    def ev_actualizar_low(self, ev):
        u, v = ev.nodo, ev.vecino
        if ev.tipo == "BACK_EDGE":
            origen = self.etq_tin[v]
            texto = f"low[{u}] = min(low[{u}], tin[{v}]) = {ev.low}   →   el ciclo hace bajar low"
        else:
            origen = self.etq_low[v]
            texto = f"low[{u}] = min(low[{u}], low[{v}]) = {ev.low}   →   el hijo {v} propaga su low"
        destino = self.etq_low[u]
        chip_texto = Texto(str(ev.low), font_size=24, color=YELLOW)
        chip = VGroup(
            SurroundingRectangle(chip_texto, buff=0.1, color=YELLOW, corner_radius=0.1).set_fill(BLACK, 1),
            chip_texto,
        )
        chip.set_z_index(4)
        chip.move_to(origen.get_center())
        trayecto = ArcBetweenPoints(origen.get_center(), destino.get_center(), angle=-PI / 3)

        self.jugar([self.estado_anim(texto, YELLOW), FadeIn(chip, scale=0.6)], 0.35)
        self.jugar([MoveAlongPath(chip, trayecto)], 0.8)
        nuevo = self.cambiar_low(u, ev.low)
        self.jugar([Transform(destino, nuevo), FadeOut(chip, scale=0.6)], 0.4)
        self.jugar([Indicate(destino, color=YELLOW, scale_factor=1.3)], 0.5)

    def ev_retroceder(self, ev):
        u, padre = ev.nodo, ev.vecino
        anims = [self.nodos[u][0].animate.set_stroke(BLUE).set_fill(BLUE, opacity=0.45)]
        anims += self.desapilar(u)
        if padre >= 0:
            anims.append(self.indicador_anim(padre))
            anims.append(self.estado_anim(f"{u} termina con low[{u}] = {ev.low}   →   volvemos a {padre}", BLUE_B))
            self.pendiente = (padre, u, ev.low)
        else:
            anims.append(self.estado_anim(f"{u} termina: no hay más vecinos por explorar", BLUE_B))
        self.jugar(anims, 0.6)

    # ---------------- condición low[v] > tin[u]

    def mostrar_tarjeta(self, u, v, low_v, tin_u):
        centro = np.array([CENTRO_PANEL[0], 1.75, 0])
        marco = RoundedRectangle(width=2.6, height=1.95, corner_radius=0.12, color=GRAY_B, stroke_width=2)
        marco.move_to(centro)
        fila_a = Texto(f"low[{v}] = {low_v}", font_size=22, color=COLOR_LOW)
        simbolo = Texto("?", font_size=32, color=YELLOW)
        fila_b = Texto(f"tin[{u}] = {tin_u}", font_size=22, color=COLOR_TIN)
        bloque = VGroup(fila_a, simbolo, fila_b).arrange(DOWN, buff=0.1)
        bloque.move_to(centro + UP * 0.14)
        self.tarjeta = {"marco": marco, "bloque": bloque, "op": simbolo, "centro": centro}
        return [FadeIn(marco), FadeIn(bloque)]

    def resolver_chequeo(self, es_puente):
        u, v, low_v = self.pendiente
        tin_u = self.valor_tin[u]
        if (low_v > tin_u) != es_puente:
            raise ValueError(f"CSV inconsistente en la arista ({u}, {v}).")
        self.pendiente = None
        self.jugar(self.mostrar_tarjeta(u, v, low_v, tin_u) + [
            self.estado_anim(f"¿low[{v}] > tin[{u}]?   →   ¿{v} puede subir hasta {u} o más arriba sin esta arista?",
                             YELLOW)], 0.5)
        t = self.tarjeta
        self.esperar_lectura(minimo=self.t(0.5))
        simbolo = Texto(">" if es_puente else "≤", font_size=34, color=RED if es_puente else GRAY_B)
        simbolo.move_to(t["op"])
        veredicto = Texto("¡PUENTE!" if es_puente else "no es puente", font_size=24 if es_puente else 20,
                          color=RED if es_puente else GRAY_B)
        veredicto.move_to(t["centro"] + DOWN * 0.72)
        mensaje = (f"low[{v}] = {low_v} > tin[{u}] = {tin_u}   →   sin esta arista {v} queda aislado de {u}"
                   if es_puente else
                   f"low[{v}] = {low_v} ≤ tin[{u}] = {tin_u}   →   hay otro camino: no es puente")
        anims = [Transform(t["op"], simbolo), FadeIn(veredicto),
                 self.estado_anim(mensaje, RED if es_puente else GRAY_B)]
        if es_puente:
            anims += self.pintar_puente(u, v)
        self.jugar(anims, 0.6)
        if es_puente:
            self.jugar([Flash(self.pos_medio(u, v), color=RED, line_length=0.22, flash_radius=0.45,
                              num_lines=10, run_time=self.t(0.6))], 0.6)
        self.esperar_lectura(minimo=self.t(1.2 if es_puente else 0.5))
        self.jugar([FadeOut(t["marco"]), FadeOut(t["bloque"]), FadeOut(veredicto)], 0.4)
        self.tarjeta = None

    def pos_medio(self, u, v):
        return (self.pos[u] + self.pos[v]) / 2

    def pintar_puente(self, u, v):
        clave = frozenset((u, v))
        anims = [self.aristas[clave].animate.set_color(COLOR_PUENTE).set_stroke(width=7, opacity=1)]
        if clave in self.sup:
            anims.append(self.sup[clave].animate.set_color(COLOR_PUENTE))
        texto = Texto("PUENTE", font_size=18, color=COLOR_PUENTE)
        marco = SurroundingRectangle(texto, buff=0.07, color=COLOR_PUENTE, corner_radius=0.08)
        marco.set_fill(BLACK, 1)
        tag = VGroup(marco, texto)
        tag.move_to(self.pos_tag[clave])
        tag.set_z_index(2)
        self.tags[clave] = tag
        anims.append(FadeIn(tag, scale=0.6))
        return anims

    def ev_marcar_puente(self, ev):
        if self.pendiente is None or (self.pendiente[0], self.pendiente[1]) != (ev.nodo, ev.vecino):
            raise ValueError(f"MARCAR_PUENTE ({ev.nodo}, {ev.vecino}) sin evaluación previa.")
        self.resolver_chequeo(True)

    def ev_fin(self, ev):
        if self.pendiente is not None:
            self.resolver_chequeo(False)
        k = len(self.c.puentes)
        if k == 0:
            texto = "Algoritmo completado: ningún puente encontrado"
        elif k == 1:
            texto = f"Algoritmo completado: 1 puente encontrado {self.c.puentes[0]}"
        else:
            texto = f"Algoritmo completado: {k} puentes encontrados"
        anims = [self.estado_anim(texto, GREEN)]
        if self.indicador is not None:
            anims.append(FadeOut(self.indicador))
        if self.cab_pila is not None:
            anims.append(FadeOut(self.cab_pila))
        self.jugar(anims, 0.5)

    # ----------------------------------------------------- utilidades

    def grupo_grafo(self):
        objetos = list(self.nodos.values()) + list(self.aristas.values()) + list(self.sup.values())
        objetos += list(self.etq_tin.values()) + list(self.etq_low.values()) + list(self.tags.values())
        return VGroup(*objetos)


# ======================================================================
# ESCENA PRINCIPAL
# ======================================================================

class Puentes(Scene):

    def construct(self):

        # --------------------------------------------------
        # LEER LOS CSV REALES GENERADOS POR C++
        # --------------------------------------------------

        self.principal = Corrida(buscar_csv("puentes_animacion.csv", "PUENTES_CSV"))
        self.caso_ciclo = Corrida(buscar_csv("caso_ciclo.csv", "PUENTES_CSV_CICLO"))
        self.caso_arbol = Corrida(buscar_csv("caso_arbol.csv", "PUENTES_CSV_ARBOL"))

        if not self.principal.puentes:
            raise ValueError("El CSV principal no contiene ningún puente que mostrar.")

        self.titulo_fijo = None
        self.fuente = None

        # --------------------------------------------------
        # SECUENCIA
        # --------------------------------------------------

        self.introduccion()

        self.que_es_un_puente()

        self.explicar_dfs()

        self.preparar_escena_principal()

        # Ejecución real del CSV principal
        reproductor = Reproductor(self, self.principal)
        reproductor.ejecutar()

        self.verificar_condicion(reproductor)

        self.casos_borde()

        self.cierre()

    # ==================================================
    # INTRODUCCIÓN
    # ==================================================

    def introduccion(self):

        titulo = Texto(
            "PUENTES EN GRAFOS",
            font_size=52,
            color=BLUE_B
        )

        titulo.move_to([0, 2.4, 0])

        subtitulo = Texto(
            "Animando un Algoritmo",
            font_size=29
        )

        subtitulo.next_to(
            titulo,
            DOWN,
            buff=0.35
        )

        integrantes = VGroup(

            Texto(
                "Ariel Mathias Fernando Choque Marcelo",
                font_size=19
            ),

            Texto(
                "Rodrigo de Santa Maria Anco Ito",
                font_size=19
            ),

            Texto(
                "Gabriel Saavedra Peralta",
                font_size=19
            )
        )

        integrantes.arrange(
            DOWN,
            buff=0.16
        )

        integrantes.next_to(
            subtitulo,
            DOWN,
            buff=0.55
        )

        self.play(
            Write(titulo),
            run_time=0.8
        )

        self.play(
            FadeIn(subtitulo),
            run_time=0.5
        )

        self.play(
            LaggedStart(
                *[
                    FadeIn(nombre, shift=RIGHT * 0.15)
                    for nombre in integrantes
                ],
                lag_ratio=0.2
            ),
            run_time=0.8
        )

        self.wait(1.5)

        self.play(
            FadeOut(titulo),
            FadeOut(subtitulo),
            FadeOut(integrantes),
            run_time=0.6
        )

    # ==================================================
    # ¿QUÉ ES UN PUENTE?
    # ==================================================

    def que_es_un_puente(self):

        corrida = self.principal

        titulo_concepto = Texto(
            "¿Qué es un puente?",
            font_size=38,
            color=BLUE_B
        )

        titulo_concepto.to_edge(
            UP,
            buff=0.6
        )

        definicion = Texto(
            "Una arista cuya eliminación desconecta el grafo.",
            font_size=25,
            color=GREEN
        )

        definicion.move_to([0, 2.25, 0])

        self.play(
            FadeIn(titulo_concepto),
            run_time=0.5
        )

        self.play(
            FadeIn(definicion, shift=UP * 0.1),
            run_time=0.6
        )

        # Componente del grafo real que contiene al primer puente
        u_p, v_p = corrida.puentes[0]
        comp = next(c for c in componentes(corrida.nodos, corrida.aristas) if u_p in c)
        aristas = [a for a in corrida.aristas if a[0] in comp and a[1] in comp]
        base = disponer_grafo(corrida.nodos, corrida.aristas)
        xs = [base[u][0] for u in comp]
        ys = [base[u][1] for u in comp]
        centro = np.array([(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0.0])
        pos = {u: (base[u] - centro) * 1.3 + np.array([0, -0.4, 0]) for u in comp}

        nodos = {u: hacer_nodo(u, pos[u]) for u in comp}
        lineas = {frozenset(a): hacer_arista(pos[a[0]], pos[a[1]]) for a in aristas}

        def texto_componentes(cantidad, color):
            t = Texto(f"Componentes conexas: {cantidad}", font_size=22, color=color)
            t.move_to([0, 1.45, 0])
            return t

        contador = texto_componentes(1, GRAY_B)

        self.play(
            LaggedStart(*[FadeIn(n, shift=UP * 0.15) for n in nodos.values()], lag_ratio=0.15),
            run_time=0.7
        )

        self.play(
            LaggedStart(*[Create(l) for l in lineas.values()], lag_ratio=0.15),
            FadeIn(contador),
            run_time=0.7
        )

        mensaje = None

        def cambiar_mensaje(texto, color):
            nonlocal mensaje
            nuevo = Texto(texto, font_size=19, color=color)
            nuevo.move_to([0, -2.95, 0])
            viejo, mensaje = mensaje, nuevo
            return FadeIn(nuevo) if viejo is None else AnimationGroup(FadeOut(viejo), FadeIn(nuevo))

        # 1) Una arista de un ciclo: al quitarla el grafo sigue conexo
        ciclo = next(a for a in aristas if frozenset(a) not in {frozenset(p) for p in corrida.puentes})
        l_ciclo = lineas[frozenset(ciclo)]

        self.play(
            cambiar_mensaje(f"Quitamos la arista ({ciclo[0]}, {ciclo[1]}) de un ciclo...", WHITE),
            Indicate(l_ciclo, color=YELLOW, scale_factor=1.0),
            run_time=0.8
        )

        self.play(
            FadeOut(l_ciclo),
            run_time=0.6
        )

        self.play(
            cambiar_mensaje("...y todo sigue conectado: hay otro camino. No es un puente.", GREEN),
            Transform(contador, texto_componentes(len(componentes(comp, aristas, ciclo)), GREEN)),
            *[Indicate(n[0], color=GREEN, scale_factor=1.12) for n in nodos.values()],
            run_time=0.9
        )

        self.wait(1.6)

        self.play(
            Create(l_ciclo),
            run_time=0.6
        )

        # 2) El puente: al quitarlo el grafo se parte
        l_puente = lineas[frozenset((u_p, v_p))]

        self.play(
            cambiar_mensaje(f"Ahora quitamos la arista ({u_p}, {v_p})...", WHITE),
            l_puente.animate.set_color(RED).set_stroke(width=7),
            run_time=0.8
        )

        self.wait(0.5)

        grupos = componentes(comp, aristas, (u_p, v_p))
        grupos.sort(key=lambda g: sum(pos[u][0] for u in g) / len(g))
        colores = [BLUE, TEAL, YELLOW]
        desplazamientos = [LEFT * 0.7, RIGHT * 0.7]
        animaciones_corte = []
        for i, grupo in enumerate(grupos[:2]):
            for u in grupo:
                destino_nodo = nodos[u].copy()
                destino_nodo.shift(desplazamientos[i])
                destino_nodo[0].set_stroke(colores[i]).set_fill(colores[i], opacity=0.3)
                animaciones_corte.append(Transform(nodos[u], destino_nodo))
            for a in aristas:
                if a[0] in grupo and a[1] in grupo:
                    animaciones_corte.append(lineas[frozenset(a)].animate.shift(desplazamientos[i]))

        self.play(
            FadeOut(l_puente),
            *animaciones_corte,
            cambiar_mensaje(f"...y el grafo se parte en dos: ¡{u_p}-{v_p} es un puente!", RED),
            Transform(contador, texto_componentes(len(grupos), RED)),
            run_time=1.1
        )

        self.wait(2.2)

        self.play(
            FadeOut(mensaje),
            FadeOut(contador),
            *[FadeOut(n) for n in nodos.values()],
            *[FadeOut(l) for l in lineas.values()],
            FadeOut(definicion),
            run_time=0.6
        )

        # --------------------------------------------------
        # USO PRÁCTICO
        # --------------------------------------------------

        uso = Texto(
            "Aplicación práctica",
            font_size=31,
            color=GREEN
        )

        uso.move_to([0, 0.7, 0])

        uso_texto = Texto(
            "Encuentra las conexiones críticas: si una falla, la red se parte.\n"
            "Ej.: enlaces de una red, rutas entre ciudades, dependencias de software.",
            font_size=23,
            line_spacing=1.2
        )

        uso_texto.next_to(
            uso,
            DOWN,
            buff=0.4
        )

        self.play(
            FadeIn(uso),
            FadeIn(uso_texto),
            run_time=0.5
        )

        self.wait(2.5)

        self.play(
            FadeOut(titulo_concepto),
            FadeOut(uso),
            FadeOut(uso_texto),
            run_time=0.6
        )

    # ==================================================
    # DFS: tin Y low
    # ==================================================

    def explicar_dfs(self):

        titulo = Texto(
            "DFS: los valores tin y low",
            font_size=38,
            color=BLUE_B
        )

        titulo.to_edge(
            UP,
            buff=0.6
        )

        def linea(partes, tam=22):
            grupo = VGroup(*[Texto(t, font_size=tam, color=c) for t, c in partes])
            grupo.arrange(RIGHT, buff=0.12, aligned_edge=DOWN)
            return grupo

        l0 = linea([("DFS recorre el grafo en profundidad y retrocede.", GREEN)], 23)
        l1 = linea([("tin[u]", COLOR_TIN), (":  momento en que DFS descubre u.", WHITE)])
        l2a = linea([("low[u]", COLOR_LOW), (":  menor tin alcanzable desde el subárbol", WHITE)])
        l2b = linea([("de u usando a lo más una arista de retroceso.", WHITE)])
        regla = linea([("(u, v) es puente  si  low[v] > tin[u]", YELLOW)], 24)

        bloque = VGroup(l0, l1, l2a, l2b)
        bloque.arrange(DOWN, buff=0.34, aligned_edge=LEFT)
        l2b.align_to(l2a[1], LEFT)
        if bloque.width > 6.5:
            bloque.scale_to_fit_width(6.5)
        bloque.to_edge(LEFT, buff=0.7)
        bloque.set_y(0.35)
        regla.next_to(bloque, DOWN, buff=0.7, aligned_edge=LEFT)

        # Minigrafo: el mismo triángulo del ejemplo, con los valores reales de su DFS
        pos = {0: np.array([2.35, 0.95, 0.0]), 1: np.array([2.35, -1.25, 0.0]), 2: np.array([4.6, -0.15, 0.0])}
        aristas = [(0, 1), (1, 2), (2, 0)]
        nodos = {u: hacer_nodo(u, p) for u, p in pos.items()}
        lineas = {frozenset(a): hacer_arista(pos[a[0]], pos[a[1]]) for a in aristas}
        area = (0.3, 6.9, -2.3, 2.2)
        ancho, alto = medir_etiqueta()
        etq, _ = colocar_etiquetas(pos, aristas, ancho, alto, area)

        self.play(FadeIn(titulo), run_time=0.5)

        self.play(
            FadeIn(l0, shift=UP * 0.1),
            LaggedStart(*[FadeIn(n, shift=UP * 0.15) for n in nodos.values()], lag_ratio=0.15),
            *[Create(l) for l in lineas.values()],
            run_time=0.9
        )

        self.wait(0.8)

        # tin: orden de descubrimiento 0, 1, 2
        self.play(FadeIn(l1, shift=UP * 0.1), run_time=0.5)

        anillo = Circle(radius=ANILLO_R, color=YELLOW, stroke_width=4).move_to(pos[0]).set_z_index(3)
        tin_filas, low_filas = {}, {}
        self.play(Create(anillo), run_time=0.3)

        for orden, u in enumerate([0, 1, 2]):
            if orden > 0:
                self.play(Transform(anillo, Circle(radius=ANILLO_R, color=YELLOW, stroke_width=4)
                                    .move_to(pos[u]).set_z_index(3)), run_time=0.5)
            tin_filas[u] = fila_etiqueta("tin", orden, COLOR_TIN, etq[u] + UP * 0.15)
            self.play(
                nodos[u][0].animate.set_stroke(TEAL).set_fill(TEAL, opacity=0.3),
                FadeIn(tin_filas[u], scale=0.6),
                run_time=0.5
            )
            self.wait(0.2)

        self.wait(0.6)

        # low: empieza igual que tin y baja por el ciclo
        self.play(FadeIn(l2a, shift=UP * 0.1), FadeIn(l2b, shift=UP * 0.1), run_time=0.5)

        for u in [0, 1, 2]:
            low_filas[u] = fila_etiqueta("low", u, COLOR_LOW, etq[u] + DOWN * 0.15)
        self.play(*[FadeIn(f, scale=0.6) for f in low_filas.values()], run_time=0.5)

        self.wait(0.5)

        retroceso = hacer_retroceso(pos[2], pos[0])
        self.play(
            Create(retroceso),
            lineas[frozenset((2, 0))].animate.set_stroke(opacity=0.25),
            Indicate(tin_filas[0], color=YELLOW, scale_factor=1.25),
            run_time=0.8
        )

        for u in [2, 1]:
            origen = tin_filas[0] if u == 2 else low_filas[2]
            chip_texto = Texto("0", font_size=24, color=YELLOW)
            chip = VGroup(
                SurroundingRectangle(chip_texto, buff=0.1, color=YELLOW, corner_radius=0.1).set_fill(BLACK, 1),
                chip_texto
            )
            chip.set_z_index(4)
            chip.move_to(origen.get_center())
            trayecto = ArcBetweenPoints(origen.get_center(), low_filas[u].get_center(), angle=-PI / 3)
            self.play(FadeIn(chip, scale=0.6), run_time=0.3)
            self.play(MoveAlongPath(chip, trayecto), run_time=0.7)
            self.play(
                Transform(low_filas[u], fila_etiqueta("low", 0, COLOR_LOW, low_filas[u].get_center())),
                FadeOut(chip, scale=0.6),
                run_time=0.4
            )
            self.play(
                Indicate(low_filas[u], color=YELLOW, scale_factor=1.3),
                run_time=0.5
            )

        self.wait(1.2)

        self.play(
            FadeIn(regla, shift=UP * 0.1),
            run_time=0.6
        )

        self.wait(3)

        self.play(
            *[FadeOut(m) for m in self.mobjects],
            run_time=0.7
        )

    # ==================================================
    # ESCENA PRINCIPAL
    # ==================================================

    def preparar_escena_principal(self):

        self.titulo_fijo = Texto(
            "PUENTES EN GRAFOS",
            font_size=31,
            color=BLUE_B
        )

        self.titulo_fijo.to_edge(
            UP,
            buff=0.18
        )

        self.fuente = Texto(
            "Ejecución real: C++  →  CSV  →  Manim",
            font_size=15,
            color=GRAY_B
        )

        self.fuente.to_corner(
            UR,
            buff=0.2
        )

        self.play(
            FadeIn(self.titulo_fijo),
            FadeIn(self.fuente),
            run_time=0.5
        )

        self.wait(1)

    # ==================================================
    # CONDICIÓN low[v] > tin[u] SOBRE TODAS LAS ARISTAS DEL ÁRBOL
    # ==================================================

    def verificar_condicion(self, rep):

        corrida = rep.c

        self.wait(0.8)

        grupo = rep.grupo_grafo()
        fase = rep.fase
        contador = rep.contador

        titulo = Texto(
            "Condición del puente",
            font_size=25,
            color=BLUE_B
        )
        titulo.move_to([0, 2.65, 0])

        self.play(
            Transform(fase, titulo),
            FadeOut(contador),
            grupo.animate.scale(0.78).to_edge(LEFT, buff=0.6).shift(DOWN * 0.1),
            run_time=1.0
        )

        # Tabla: una fila por arista del árbol DFS, con los valores reales del CSV
        x0 = 0.9
        filas = corrida.evaluaciones
        y_cab = 1.55
        paso = min(0.62, 3.2 / max(1, len(filas)))

        cabecera = VGroup(
            Texto("arista (u, v)", font_size=18, color=GRAY_B).move_to([x0 + 0.7, y_cab, 0]),
            Texto("low[v]", font_size=18, color=COLOR_LOW).move_to([x0 + 2.2, y_cab, 0]),
            Texto("tin[u]", font_size=18, color=COLOR_TIN).move_to([x0 + 3.5, y_cab, 0]),
            Texto("¿low[v] > tin[u]?", font_size=18, color=YELLOW).move_to([x0 + 4.95, y_cab, 0]),
        )
        divisor = Line([x0 - 0.1, y_cab - 0.3, 0], [x0 + 5.95, y_cab - 0.3, 0], color=GRAY, stroke_width=2)

        self.play(FadeIn(cabecera), Create(divisor), run_time=0.6)

        lineas_tabla = []
        for i, (u, v, tin_u, low_v, es_puente) in enumerate(filas):
            y = y_cab - 0.7 - i * paso
            color = RED if es_puente else GRAY_B
            fila = VGroup(
                Texto(f"({u}, {v})", font_size=24, color=WHITE if not es_puente else RED).move_to([x0 + 0.7, y, 0]),
                Texto(f"{low_v}", font_size=24, color=COLOR_LOW).move_to([x0 + 2.2, y, 0]),
                Texto(f"{tin_u}", font_size=24, color=COLOR_TIN).move_to([x0 + 3.5, y, 0]),
                Texto(">  puente" if es_puente else "≤  no", font_size=24, color=color).move_to([x0 + 4.95, y, 0]),
            )
            lineas_tabla.append(fila)
            arista = rep.aristas[frozenset((u, v))]
            self.play(
                FadeIn(fila, shift=UP * 0.1),
                Indicate(arista, color=YELLOW if not es_puente else RED, scale_factor=1.0),
                run_time=0.7
            )
            self.wait(0.35)

        k = len(corrida.puentes)
        total = len(corrida.aristas)
        nombres = ", ".join(f"({u}, {v})" for u, v in corrida.puentes)
        resultado = Texto(
            f"Puentes: {k} de {total} aristas   →   {nombres}",
            font_size=25,
            color=GREEN
        )
        resultado.move_to([0, -2.4, 0])

        self.play(
            FadeIn(resultado, shift=UP * 0.1),
            rep.estado_anim("Cada arista del árbol DFS se evalúa una sola vez al retroceder", GRAY_B),
            run_time=0.7
        )

        self.wait(3)

        self.limpiar_escena_principal()

    def limpiar_escena_principal(self):

        conservar = {self.titulo_fijo, self.fuente}

        restantes = [m for m in self.mobjects if m not in conservar]

        if restantes:
            self.play(
                *[FadeOut(m) for m in restantes],
                run_time=0.7
            )

    # ==================================================
    # CASOS BORDE (cada uno es una ejecución C++ distinta)
    # ==================================================

    def casos_borde(self):

        casos = [
            (self.caso_ciclo, "Ciclo", "Un ciclo no tiene puentes",
             "Todas las aristas tienen un camino alterno", GREEN),
            (self.caso_arbol, "Árbol", "En un árbol toda arista es un puente",
             "No existe ningún camino alterno", RED),
        ]

        for corrida, nombre, titulo_caso, explicacion, color in casos:

            encabezado = Texto(
                f"CASO BORDE: {nombre}",
                font_size=38,
                color=RED
            )

            encabezado.move_to([0, 0.3, 0])

            subtitulo = Texto(
                "Ejecución C++ independiente sobre otro grafo",
                font_size=22,
                color=GRAY_B
            )

            subtitulo.next_to(
                encabezado,
                DOWN,
                buff=0.35
            )

            self.play(
                FadeIn(encabezado),
                FadeIn(subtitulo),
                run_time=0.6
            )

            self.wait(1.2)

            self.play(
                FadeOut(encabezado),
                FadeOut(subtitulo),
                run_time=0.5
            )

            reproductor = Reproductor(self, corrida, rapido=True)
            reproductor.ejecutar()

            k = len(corrida.puentes)
            total = len(corrida.aristas)

            resumen = Texto(
                f"{titulo_caso}: {k} puente{'s' if k != 1 else ''} de {total} aristas",
                font_size=26,
                color=color
            )

            resumen.move_to([0, -2.4, 0])

            self.play(
                FadeIn(resumen, shift=UP * 0.1),
                reproductor.estado_anim(explicacion, GRAY_B),
                run_time=0.7
            )

            self.wait(2.5)

            self.limpiar_escena_principal()

        self.play(
            FadeOut(self.titulo_fijo),
            FadeOut(self.fuente),
            run_time=0.5
        )

    # ==================================================
    # CIERRE
    # ==================================================

    def cierre(self):

        principal = self.principal

        self.wait(0.3)

        if len(self.mobjects) > 0:

            self.play(
                *[
                    FadeOut(objeto)
                    for objeto in self.mobjects
                ],
                run_time=0.5
            )

        # --------------------------------------------------
        # COMPLEJIDAD
        # --------------------------------------------------

        titulo = Texto(
            "Complejidad",
            font_size=39,
            color=BLUE_B
        )

        titulo.move_to([
            0,
            1.95,
            0
        ])

        operaciones = Texto(
            "Recorrido DFS   •   tin y low   •   Detección de puentes",
            font_size=25
        )

        operaciones.next_to(
            titulo,
            DOWN,
            buff=0.45
        )

        tiempo = Texto(
            "Tiempo:  O(V + E)",
            font_size=33,
            color=GREEN
        )

        tiempo.next_to(
            operaciones,
            DOWN,
            buff=0.45
        )

        detalle = Texto(
            "Cada vértice y cada arista se procesan una sola vez",
            font_size=23,
            color=YELLOW
        )

        detalle.next_to(
            tiempo,
            DOWN,
            buff=0.35
        )

        espacio = Texto(
            "Espacio:  O(V + E)   (listas de adyacencia, tin, low y pila)",
            font_size=22,
            color=GRAY_B
        )

        espacio.next_to(
            detalle,
            DOWN,
            buff=0.28
        )

        v = len(principal.nodos)
        e = len(principal.aristas)
        examinadas = sum(1 for ev in principal.eventos if ev.accion == "EXPLORAR_ARISTA")
        igualdad = f" = 2E" if examinadas == 2 * e else ""

        medido = Texto(
            f"En el CSV de esta ejecución:  V = {v},  E = {e},  aristas examinadas = {examinadas}{igualdad}",
            font_size=20,
            color=BLUE_A
        )

        medido.next_to(
            espacio,
            DOWN,
            buff=0.5
        )

        self.play(
            FadeIn(titulo),
            run_time=0.4
        )

        self.play(
            FadeIn(operaciones),
            run_time=0.4
        )

        self.play(
            Write(tiempo),
            run_time=0.6
        )

        self.play(
            FadeIn(detalle),
            FadeIn(espacio),
            run_time=0.5
        )

        self.play(
            FadeIn(medido, shift=UP * 0.1),
            run_time=0.5
        )

        self.wait(4)

        # --------------------------------------------------
        # RESUMEN FINAL
        # --------------------------------------------------

        self.play(
            FadeOut(titulo),
            FadeOut(operaciones),
            FadeOut(tiempo),
            FadeOut(detalle),
            FadeOut(espacio),
            FadeOut(medido),
            run_time=0.6
        )

        resumen = Texto(
            "Puentes en Grafos",
            font_size=42,
            color=BLUE_B
        )

        resumen.move_to([
            0,
            1.35,
            0
        ])

        resumen2 = Texto(
            "DFS + tin + low = puentes en O(V + E)",
            font_size=25
        )

        resumen2.next_to(
            resumen,
            DOWN,
            buff=0.4
        )

        resumen3 = Texto(
            "Implementación C++  •  Eventos CSV  •  Animación Manim",
            font_size=21,
            color=GRAY_B
        )

        resumen3.next_to(
            resumen2,
            DOWN,
            buff=0.35
        )

        final = Texto(
            "Fin",
            font_size=28,
            color=GREEN
        )

        final.next_to(
            resumen3,
            DOWN,
            buff=0.6
        )

        self.play(
            FadeIn(resumen),
            run_time=0.4
        )

        self.play(
            FadeIn(resumen2),
            FadeIn(resumen3),
            run_time=0.5
        )

        self.play(
            FadeIn(final),
            run_time=0.3
        )

        self.wait(3.5)

"""Pruebas del algoritmo de puentes (C++) y de su CSV de eventos.

Ejecutar desde la raiz del repositorio:

    python -m unittest discover -s tests -v

Compila cpp/Proyecto_AED.cpp con $CXX (por defecto g++) en una carpeta temporal y
contrasta cada ejecucion real contra dos oraculos independientes:

  1. Definicion de puente por fuerza bruta: quitar la arista y contar componentes.
  2. Una implementacion de referencia (DFS iterativo) que genera el CSV esperado.
"""

import csv
import os
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "cpp" / "Proyecto_AED.cpp"
GRAFOS = RAIZ / "cpp" / "grafos"
OUTPUT = RAIZ / "output"

COLUMNAS = ["Iteracion", "Accion", "Nodo_Actual", "Nodo_Vecino",
            "Orden_Visita", "Low", "Tipo_Arista", "Resultado"]

_tmp = None
_exe = None


def setUpModule():
    global _tmp, _exe
    _tmp = tempfile.mkdtemp(prefix="puentes_test_")
    _exe = Path(_tmp) / ("puentes.exe" if os.name == "nt" else "puentes")
    cxx = os.environ.get("CXX", "g++")
    r = subprocess.run([cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", str(FUENTE), "-o", str(_exe)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("No compila:\n" + r.stdout + r.stderr)
    if r.stderr.strip():
        raise RuntimeError("El compilador emitio advertencias:\n" + r.stderr)


def tearDownModule():
    shutil.rmtree(_tmp, ignore_errors=True)


# ---------------------------------------------------------------- utilidades

def escribir_grafo(n, aristas, nombre="g.txt"):
    ruta = Path(_tmp) / nombre
    ruta.write_text(f"{n} {len(aristas)}\n" + "".join(f"{u} {v}\n" for u, v in aristas))
    return ruta


def ejecutar(n, aristas):
    """Ejecuta el C++ real sobre el grafo. Devuelve (filas_csv, stdout)."""
    entrada = escribir_grafo(n, aristas)
    salida = Path(_tmp) / "salida.csv"
    if salida.exists():
        salida.unlink()
    r = subprocess.run([str(_exe), str(entrada), str(salida)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return leer_csv(salida), r.stdout


def leer_csv(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fila_a_tupla(f):
    return (f["Accion"], int(f["Nodo_Actual"]), int(f["Nodo_Vecino"]),
            f["Orden_Visita"], f["Low"], f["Tipo_Arista"], f["Resultado"])


def puentes_csv(filas):
    return [frozenset((int(f["Nodo_Actual"]), int(f["Nodo_Vecino"])))
            for f in filas if f["Accion"] == "MARCAR_PUENTE"]


def componentes(n, aristas, omitir=None):
    padre = list(range(n))

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for i, (u, v) in enumerate(aristas):
        if i != omitir:
            padre[raiz(u)] = raiz(v)
    return len({raiz(x) for x in range(n)})


def puentes_fuerza_bruta(n, aristas):
    """Definicion: una arista es puente si al quitarla aumentan las componentes."""
    base = componentes(n, aristas)
    return {frozenset(a) for i, a in enumerate(aristas)
            if a[0] != a[1] and componentes(n, aristas, omitir=i) > base}


def referencia(n, aristas):
    """Eventos esperados, con un DFS iterativo escrito aparte del C++."""
    ev = []

    def log(a, u, v, t, l, tipo, res):
        ev.append((a, u, v, "NULL" if t == -1 else str(t), "NULL" if l == -1 else str(l), tipo, res))

    adj = [[] for _ in range(n)]
    tin = [-1] * n
    low = [-1] * n
    vis = [False] * n
    reloj = 0

    for i in range(n):
        log("CREAR_NODO", i, -1, -1, -1, "NONE", "SETUP_GRAFO")
    for idx, (u, v) in enumerate(aristas):
        adj[u].append((v, idx))
        if u != v:
            adj[v].append((u, idx))
        log("CREAR_ARISTA", u, v, -1, -1, "NONE", "SETUP_GRAFO")

    for raiz in range(n):
        if vis[raiz]:
            continue
        vis[raiz] = True
        tin[raiz] = low[raiz] = reloj
        reloj += 1
        log("VISITAR", raiz, -1, tin[raiz], low[raiz], "NONE", "NODO_DESCUBIERTO")
        pila = [[raiz, -1, -1, 0]]
        while pila:
            marco = pila[-1]
            u, p, pid, i = marco
            if i < len(adj[u]):
                marco[3] += 1
                v, eid = adj[u][i]
                if eid == pid:
                    log("EXPLORAR_ARISTA", u, v, tin[u], low[u], "PARENT", "IGNORAR_PADRE")
                elif v == u:
                    log("EXPLORAR_ARISTA", u, v, tin[u], low[u], "SELF_LOOP", "BUCLE_IGNORADO")
                elif vis[v]:
                    if tin[v] < tin[u]:
                        log("EXPLORAR_ARISTA", u, v, tin[u], low[u], "BACK_EDGE", "ARISTA_RETROCESO")
                        if tin[v] < low[u]:
                            low[u] = tin[v]
                            log("ACTUALIZAR_LOW", u, v, tin[u], low[u], "BACK_EDGE", "LOW_ACTUALIZADO_POR_CICLO")
                    else:
                        log("EXPLORAR_ARISTA", u, v, tin[u], low[u], "FORWARD_EDGE", "ARISTA_YA_PROCESADA")
                else:
                    log("EXPLORAR_ARISTA", u, v, tin[u], low[u], "TREE_EDGE", "AVANZAR_DFS")
                    vis[v] = True
                    tin[v] = low[v] = reloj
                    reloj += 1
                    log("VISITAR", v, u, tin[v], low[v], "NONE", "NODO_DESCUBIERTO")
                    pila.append([v, u, eid, 0])
            else:
                log("RETROCEDER", u, p, tin[u], low[u], "NONE", "FIN_NODO")
                pila.pop()
                if p != -1:
                    if low[u] < low[p]:
                        low[p] = low[u]
                        log("ACTUALIZAR_LOW", p, u, tin[p], low[p], "TREE_EDGE", "LOW_PROPAGADO_HIJO")
                    if low[u] > tin[p]:
                        log("MARCAR_PUENTE", p, u, tin[p], low[u], "TREE_EDGE", "PUENTE_ENCONTRADO")
    log("FIN", -1, -1, -1, -1, "NONE", "ALGORITMO_COMPLETADO")
    return ev


def leer_demo(nombre):
    lineas = (GRAFOS / nombre).read_text().split()
    n, m = int(lineas[0]), int(lineas[1])
    datos = list(map(int, lineas[2:]))
    return n, [(datos[2 * i], datos[2 * i + 1]) for i in range(m)]


class Base(unittest.TestCase):
    def verificar(self, n, aristas, esperado=None):
        """Verifica integridad, equivalencia con la referencia y puentes correctos."""
        filas, _ = ejecutar(n, aristas)

        # Integridad del CSV
        self.assertEqual(list(filas[0].keys()), COLUMNAS)
        self.assertEqual([int(f["Iteracion"]) for f in filas], list(range(1, len(filas) + 1)))
        self.assertEqual(filas[-1]["Accion"], "FIN")
        self.assertEqual(sum(f["Accion"] == "FIN" for f in filas), 1)
        self.assertEqual([f["Accion"] for f in filas[:n]], ["CREAR_NODO"] * n)
        self.assertEqual([f["Accion"] for f in filas[n:n + len(aristas)]], ["CREAR_ARISTA"] * len(aristas))
        self.assertEqual(sum(f["Accion"] == "VISITAR" for f in filas), n)
        self.assertEqual(sum(f["Accion"] == "RETROCEDER" for f in filas), n)

        # Equivalencia evento por evento con la implementacion de referencia
        self.assertEqual([fila_a_tupla(f) for f in filas], referencia(n, aristas))

        # Puentes segun la definicion (fuerza bruta)
        encontrados = puentes_csv(filas)
        self.assertEqual(len(encontrados), len(set(encontrados)), "puente repetido")
        self.assertEqual(set(encontrados), puentes_fuerza_bruta(n, aristas))
        if esperado is not None:
            self.assertEqual(set(encontrados), {frozenset(e) for e in esperado})
        return filas


# --------------------------------------------------------------------- tests

class CasosDeLaAnimacion(Base):
    def test_ejemplo_del_equipo(self):
        n, aristas = leer_demo("ejemplo.txt")
        filas, salida = ejecutar(n, aristas)
        self.verificar(n, aristas, esperado=[(2, 3)])
        self.assertIn("Puentes: 1", salida)
        self.assertIn("(2, 3)", salida)
        # El nodo 4 aislado se visita y retrocede sin explorar aristas
        i = next(i for i, f in enumerate(filas) if f["Accion"] == "VISITAR" and f["Nodo_Actual"] == "4")
        self.assertEqual(filas[i + 1]["Accion"], "RETROCEDER")
        self.assertEqual(filas[i + 1]["Nodo_Actual"], "4")

    def test_sin_argumentos_equivale_al_ejemplo(self):
        carpeta = Path(_tmp) / "defecto"
        carpeta.mkdir(exist_ok=True)
        subprocess.run([str(_exe)], cwd=carpeta, check=True, capture_output=True)
        n, aristas = leer_demo("ejemplo.txt")
        filas, _ = ejecutar(n, aristas)
        self.assertEqual(leer_csv(carpeta / "puentes_animacion.csv"), filas)

    def test_ciclo_sin_puentes(self):
        n, aristas = leer_demo("ciclo.txt")
        self.verificar(n, aristas, esperado=[])

    def test_arbol_todas_son_puentes(self):
        n, aristas = leer_demo("arbol.txt")
        filas = self.verificar(n, aristas, esperado=aristas)
        self.assertEqual(len(puentes_csv(filas)), len(aristas))

    def test_csv_publicados_estan_sincronizados(self):
        """Los CSV de output/ son exactamente lo que produce el C++ hoy."""
        for demo, publicado in [("ejemplo.txt", "puentes_animacion.csv"),
                                ("ciclo.txt", "caso_ciclo.csv"),
                                ("arbol.txt", "caso_arbol.csv")]:
            with self.subTest(publicado):
                n, aristas = leer_demo(demo)
                filas, _ = ejecutar(n, aristas)
                self.assertEqual(leer_csv(OUTPUT / publicado), filas)


class AlgoritmoYCasosBorde(Base):
    def test_grafo_desconectado(self):
        aristas = [(0, 1), (1, 2), (2, 0), (2, 3), (4, 5), (5, 6)]
        filas = self.verificar(8, aristas, esperado=[(2, 3), (4, 5), (5, 6)])
        # Una raiz nueva por componente: 0, 4 y 7 (nodo aislado)
        raices = [f["Nodo_Actual"] for f in filas if f["Accion"] == "VISITAR" and f["Nodo_Vecino"] == "-1"]
        self.assertEqual(raices, ["0", "4", "7"])

    def test_low_se_actualiza_por_arista_de_retroceso(self):
        filas = self.verificar(5, [(0, 1), (1, 2), (2, 0), (2, 3)])
        act = [f for f in filas if f["Accion"] == "ACTUALIZAR_LOW" and f["Tipo_Arista"] == "BACK_EDGE"]
        self.assertEqual(len(act), 1)
        self.assertEqual((act[0]["Nodo_Actual"], act[0]["Nodo_Vecino"], act[0]["Low"]), ("2", "0", "0"))

    def test_padre_no_se_confunde_con_retroceso(self):
        filas = self.verificar(5, [(0, 1), (1, 2), (2, 0), (2, 3)])
        padre, tin = {}, {}
        for f in filas:
            u = int(f["Nodo_Actual"])
            if f["Accion"] == "VISITAR":
                padre[u] = int(f["Nodo_Vecino"])
                tin[u] = int(f["Orden_Visita"])
            if f["Accion"] == "EXPLORAR_ARISTA":
                v = int(f["Nodo_Vecino"])
                if f["Tipo_Arista"] == "PARENT":
                    self.assertEqual(v, padre[u])
                elif f["Tipo_Arista"] == "BACK_EDGE":
                    self.assertNotEqual(v, padre[u])
                    self.assertLess(tin[v], tin[u])  # siempre hacia un ancestro
                elif f["Tipo_Arista"] == "FORWARD_EDGE":
                    self.assertGreater(tin[v], tin[u])  # el ancestro ve a su descendiente

    def test_arista_descendiente_no_se_marca_como_retroceso(self):
        """Regresion: el nodo 0 ve a su descendiente 2 -> FORWARD_EDGE, no BACK_EDGE."""
        filas, _ = ejecutar(5, [(0, 1), (1, 2), (2, 0), (2, 3)])
        f = [x for x in filas if x["Accion"] == "EXPLORAR_ARISTA"
             and x["Nodo_Actual"] == "0" and x["Nodo_Vecino"] == "2"]
        self.assertEqual([x["Tipo_Arista"] for x in f], ["FORWARD_EDGE"])

    def test_aristas_paralelas_no_son_puente(self):
        filas = self.verificar(2, [(0, 1), (0, 1)], esperado=[])
        tipos = [f["Tipo_Arista"] for f in filas if f["Nodo_Actual"] == "1" and f["Accion"] == "EXPLORAR_ARISTA"]
        self.assertEqual(tipos, ["PARENT", "BACK_EDGE"])  # la 2.a arista al padre es retroceso
        self.verificar(3, [(0, 1), (0, 1), (1, 2)], esperado=[(1, 2)])

    def test_bucle_no_es_puente(self):
        filas = self.verificar(2, [(0, 0), (0, 1)], esperado=[(0, 1)])
        self.assertIn("SELF_LOOP", [f["Tipo_Arista"] for f in filas])

    def test_nodo_unico_y_grafo_sin_aristas(self):
        filas = self.verificar(1, [], esperado=[])
        self.assertEqual([f["Accion"] for f in filas], ["CREAR_NODO", "VISITAR", "RETROCEDER", "FIN"])
        self.verificar(4, [], esperado=[])

    def test_arista_unica_es_puente(self):
        self.verificar(2, [(0, 1)], esperado=[(0, 1)])

    def test_dos_ciclos_unidos_por_un_puente(self):
        aristas = [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 5), (5, 3)]
        self.verificar(6, aristas, esperado=[(2, 3)])

    def test_grafos_aleatorios_contra_oraculos(self):
        azar = random.Random(2026)
        for caso in range(80):
            n = azar.randint(1, 12)
            m = azar.randint(0, 18)
            aristas = [(azar.randrange(n), azar.randrange(n)) for _ in range(m)]
            with self.subTest(caso=caso, n=n, aristas=aristas):
                self.verificar(n, aristas)


class Complejidad(Base):
    def test_eventos_crecen_linealmente_con_v_mas_e(self):
        """Un camino de 1000 nodos (maximo) y una malla: #eventos = O(V + E)."""
        n = 1000
        camino = [(i, i + 1) for i in range(n - 1)]
        filas = self.verificar(n, camino, esperado=camino)
        self.assertLessEqual(len(filas), 8 * (n + len(camino)))

        ancho = 30
        malla = []
        for i in range(ancho * ancho):
            if (i + 1) % ancho:
                malla.append((i, i + 1))
            if i + ancho < ancho * ancho:
                malla.append((i, i + ancho))
        filas, _ = ejecutar(ancho * ancho, malla)
        self.assertEqual(puentes_csv(filas), [])
        self.assertLessEqual(len(filas), 8 * (ancho * ancho + len(malla)))
        exploradas = sum(f["Accion"] == "EXPLORAR_ARISTA" for f in filas)
        self.assertEqual(exploradas, 2 * len(malla))  # cada arista se examina una vez por extremo


class EntradasInvalidas(unittest.TestCase):
    def correr(self, *args):
        return subprocess.run([str(_exe), *map(str, args)], capture_output=True, text=True)

    def test_archivo_inexistente(self):
        r = self.correr(Path(_tmp) / "no_existe.txt", Path(_tmp) / "x.csv")
        self.assertNotEqual(r.returncode, 0)

    def test_arista_fuera_de_rango(self):
        ruta = escribir_grafo(2, [(0, 5)], "malo.txt")
        r = self.correr(ruta, Path(_tmp) / "x.csv")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fuera de rango", r.stderr)

    def test_faltan_aristas(self):
        ruta = Path(_tmp) / "corto.txt"
        ruta.write_text("3 2\n0 1\n")
        self.assertNotEqual(self.correr(ruta, Path(_tmp) / "x.csv").returncode, 0)


if __name__ == "__main__":
    unittest.main()

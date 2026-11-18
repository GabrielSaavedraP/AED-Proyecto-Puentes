"""Pruebas de la parte Python: lectura/validacion del CSV y disposicion del grafo.

    python -m unittest discover -s tests -v

Requiere manim (pip install -r python/requirements.txt); si no esta instalado, se omiten.
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
OUTPUT = RAIZ / "output"

try:
    spec = importlib.util.spec_from_file_location("puentes_animation", RAIZ / "python" / "puentes_animation.py")
    pa = importlib.util.module_from_spec(spec)
    sys.modules["puentes_animation"] = pa
    spec.loader.exec_module(pa)
except ImportError:  # manim no instalado
    pa = None


@unittest.skipIf(pa is None, "manim no esta instalado")
class LecturaDelCSV(unittest.TestCase):

    def test_ejemplo(self):
        c = pa.Corrida(OUTPUT / "puentes_animacion.csv")
        self.assertEqual(c.nodos, [0, 1, 2, 3, 4])
        self.assertEqual(len(c.aristas), 4)
        self.assertEqual(c.puentes, [(2, 3)])
        self.assertEqual(c.tin_final, {0: 0, 1: 1, 2: 2, 3: 3, 4: 4})
        self.assertEqual(c.low_final, {0: 0, 1: 0, 2: 0, 3: 3, 4: 4})
        self.assertEqual(c.profundidad, 4)

    def test_casos_borde(self):
        ciclo = pa.Corrida(OUTPUT / "caso_ciclo.csv")
        arbol = pa.Corrida(OUTPUT / "caso_arbol.csv")
        self.assertEqual(ciclo.puentes, [])
        self.assertEqual(len(arbol.puentes), len(arbol.aristas))
        self.assertEqual({frozenset(p) for p in arbol.puentes}, {frozenset(a) for a in arbol.aristas})

    def test_evaluaciones_coinciden_con_los_puentes(self):
        c = pa.Corrida(OUTPUT / "puentes_animacion.csv")
        self.assertEqual([(u, v) for u, v, _, _, es in c.evaluaciones if es], c.puentes)
        self.assertEqual(len(c.evaluaciones), len(c.nodos) - 2)  # aristas del arbol: 0-1, 1-2, 2-3

    def test_csv_corrupto_se_rechaza(self):
        original = (OUTPUT / "puentes_animacion.csv").read_text().splitlines()
        tmp = Path(tempfile.mkdtemp())
        try:
            casos = {
                "cabecera": [original[0].replace("Low", "Bajo")] + original[1:],
                "sin_fin": original[:-1],
                "puente_falso": [l.replace("MARCAR_PUENTE,2,3,2,3", "MARCAR_PUENTE,2,3,2,1") for l in original],
                "puente_omitido": [l for l in original if "MARCAR_PUENTE" not in l],
                "pila_rota": [l for l in original if not l.startswith("26,")],
            }
            for nombre, lineas in casos.items():
                with self.subTest(nombre):
                    ruta = tmp / f"{nombre}.csv"
                    ruta.write_text("\n".join(lineas) + "\n")
                    with self.assertRaises(ValueError):
                        pa.Corrida(ruta)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_variable_de_entorno(self):
        os.environ["PUENTES_TEST_CSV"] = str(OUTPUT / "caso_ciclo.csv")
        try:
            self.assertEqual(pa.buscar_csv("no_existe.csv", "PUENTES_TEST_CSV"), OUTPUT / "caso_ciclo.csv")
        finally:
            del os.environ["PUENTES_TEST_CSV"]
        with self.assertRaises(FileNotFoundError):
            pa.buscar_csv("no_existe.csv", "PUENTES_VARIABLE_INEXISTENTE")


@unittest.skipIf(pa is None, "manim no esta instalado")
class TextosEnPantalla(unittest.TestCase):

    def test_los_textos_largos_no_se_parten_en_lineas(self):
        """Regresion: a 10x Pango partia el texto segun la resolucion de salida."""
        referencia = pa.Texto("Ag", font_size=22).height
        for texto, tam in [("PUENTES EN GRAFOS", 52),
                           ("Ariel Mathias Fernando Choque Marcelo", 19),
                           ("low[3] = 3 > tin[2] = 2   ->   sin esta arista 3 queda aislado de 2", 19),
                           ("Espacio:  O(V + E)   (listas de adyacencia, tin, low y pila)", 22)]:
            with self.subTest(texto=texto):
                self.assertLess(pa.Texto(texto, font_size=tam).height, referencia * tam / 22 * 1.6)

    def test_tamano_visual_equivale_al_text_de_manim(self):
        nitido = pa.Texto("Evento 12 de 31", font_size=16)
        directo = pa.Text("Evento 12 de 31", font_size=16, font=pa.FUENTE)
        self.assertAlmostEqual(nitido.height, directo.height, delta=0.06)
        self.assertAlmostEqual(nitido.width, directo.width, delta=0.15 * directo.width)

    def test_no_se_altera_la_configuracion_global(self):
        antes = pa.config["pixel_width"]
        pa.Texto("prueba")
        self.assertEqual(pa.config["pixel_width"], antes)


@unittest.skipIf(pa is None, "manim no esta instalado")
class DisposicionDelGrafo(unittest.TestCase):
    """Las etiquetas tin/low no tapan nodos ni cruzan aristas, y nada sale de pantalla."""

    def revisar(self, archivo):
        c = pa.Corrida(OUTPUT / archivo)
        pos = pa.disponer_grafo(c.nodos, c.aristas)
        ancho, alto = pa.medir_etiqueta()
        etiquetas, _ = pa.colocar_etiquetas(pos, c.aristas, ancho, alto)
        hw, hh = ancho / 2, alto / 2
        xmin, xmax, ymin, ymax = pa.AREA_GRAFO
        for u, centro in etiquetas.items():
            cx, cy = centro[0], centro[1]
            with self.subTest(archivo=archivo, nodo=u):
                self.assertTrue(xmin <= cx - hw and cx + hw <= xmax and ymin <= cy - hh and cy + hh <= ymax,
                                "etiqueta fuera del area visible")
                for a, b in c.aristas:
                    self.assertFalse(pa._toca_segmento(cx, cy, hw, hh, pos[a], pos[b], 0.0),
                                     f"la etiqueta de {u} cruza la arista ({a}, {b})")
                for w, p in pos.items():
                    self.assertFalse(pa._toca_circulo(cx, cy, hw, hh, p, pa.NODO_R, 0.0),
                                     f"la etiqueta de {u} tapa el nodo {w}")
                for w, otro in etiquetas.items():
                    if w != u:
                        self.assertFalse(abs(cx - otro[0]) < ancho and abs(cy - otro[1]) < alto,
                                         f"las etiquetas de {u} y {w} se superponen")

    def test_ejemplo(self):
        self.revisar("puentes_animacion.csv")

    def test_ciclo(self):
        self.revisar("caso_ciclo.csv")

    def test_arbol(self):
        self.revisar("caso_arbol.csv")

    def test_etiquetas_de_puente_no_chocan(self):
        ancho, alto = pa.medir_etiqueta()
        for archivo in ["puentes_animacion.csv", "caso_arbol.csv"]:
            c = pa.Corrida(OUTPUT / archivo)
            rep = pa.Reproductor(None, c)
            self.assertEqual(len(rep.pos_tag), len(c.puentes))
            for clave, centro in rep.pos_tag.items():
                cx, cy, hw, hh = centro[0], centro[1], 0.5, 0.18
                with self.subTest(archivo=archivo, puente=sorted(clave)):
                    for a, b in c.aristas:
                        self.assertFalse(pa._toca_segmento(cx, cy, hw, hh, rep.pos[a], rep.pos[b], 0.0))
                    for p in rep.pos.values():
                        self.assertFalse(pa._toca_circulo(cx, cy, hw, hh, p, pa.NODO_R, 0.0))
                    for e in rep.pos_etiqueta.values():
                        self.assertFalse(abs(cx - e[0]) < hw + ancho / 2 and abs(cy - e[1]) < hh + alto / 2)

    def test_nodos_dentro_de_pantalla_y_aristas_visibles(self):
        for archivo in ["puentes_animacion.csv", "caso_ciclo.csv", "caso_arbol.csv"]:
            c = pa.Corrida(OUTPUT / archivo)
            pos = pa.disponer_grafo(c.nodos, c.aristas)
            puntos = list(pos.values())
            for i, p in enumerate(puntos):
                self.assertTrue(abs(p[0]) < 7.0 and abs(p[1]) < 3.5)
                for q in puntos[i + 1:]:
                    self.assertGreater(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5, 4 * pa.NODO_R)
            for a, b in c.aristas:
                largo = ((pos[a][0] - pos[b][0]) ** 2 + (pos[a][1] - pos[b][1]) ** 2) ** 0.5
                self.assertGreater(largo - 2 * pa.NODO_R, 1.0, f"arista ({a}, {b}) demasiado corta en {archivo}")

    def test_disposicion_automatica_para_otros_grafos(self):
        nodos = list(range(7))
        aristas = [(0, 1), (1, 2), (2, 0), (3, 4)]  # 3 componentes, incluye un nodo aislado
        pos = pa.disponer_grafo(nodos, aristas)
        self.assertEqual(sorted(pos), nodos)
        puntos = list(pos.values())
        for i, p in enumerate(puntos):
            for q in puntos[i + 1:]:
                self.assertGreater(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5, 2 * pa.NODO_R)


if __name__ == "__main__":
    unittest.main()

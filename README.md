# Puentes en Grafos — Implementación y Animación

Proyecto Final 2: **Anima tu Algoritmo o Estructura de Datos**

Curso: Algoritmos y Estructuras de Datos (CS2023) — UTEC — Semestre 2026-2

Docente: Víctor Racsó Galván Oyola

**Video:** [PLACEHOLDER]

## Integrantes

| Integrante | Rol |
|---|---|
| Ariel Mathias Fernando Choque Marcelo | Implementación del algoritmo en C++ y generación del CSV |
| Rodrigo de Santa Maria Anco Ito | Parser del CSV y animación en Manim |
| Gabriel Saavedra Peralta | Guion, informe, README y coordinación del formato del CSV |

## Descripción

Un **puente** es una arista de un grafo no dirigido cuya eliminación aumenta el número de componentes conexas. El algoritmo recorre el grafo con DFS y calcula, para cada nodo:

- **Orden_Visita** (`tin` en el código): momento en que el DFS descubre el nodo. No cambia una vez asignado.
- **Low**: menor `Orden_Visita` alcanzable desde el subárbol del nodo usando a lo más una arista de retroceso.

Una arista de árbol `(u, v)` es puente si `low[v] > tin[u]`.

**Complejidad:** tiempo O(V + E), espacio O(V + E).

## Arquitectura

```
C++ (algoritmo real)  ->  puentes_animacion.csv  ->  Python + Manim (animación)
```

La animación no se dibuja a mano: cada fila del CSV es un paso real de la ejecución del algoritmo en C++.

## Cómo reproducir

1. Descargar el repositorio (clonar o ZIP desde GitHub).
2. **C++:** abrir la carpeta `/cpp` en CLion, compilar y ejecutar `main`. Se genera `puentes_animacion.csv` en la carpeta de ejecución del proyecto. Copiar ese archivo a `/python`.
3. **Python:** abrir `/python` en PyCharm.
   ```bash
   pip install manim
   manim -pqh puentes_animation.py Puentes
   ```
4. El video queda en `python/media/videos/`.

## Grafo de ejemplo (en `main`)

- Aristas: `0-1`, `1-2`, `2-0` (ciclo) y `2-3`.
- Nodo `4` aislado (caso borde: componente de un solo nodo).
- Resultado esperado: **un único puente, la arista (2, 3)**.

## Formato del CSV

Columnas: `Iteracion,Accion,Nodo_Actual,Nodo_Vecino,Orden_Visita,Low,Tipo_Arista,Resultado`

| Accion | Significado |
|---|---|
| `CREAR_NODO` | Se agrega un nodo al grafo |
| `CREAR_ARISTA` | Se agrega una arista |
| `VISITAR` | El DFS descubre un nodo y le asigna `Orden_Visita` y `Low` |
| `EXPLORAR_ARISTA` | El DFS examina una arista (`Tipo_Arista`: `TREE_EDGE`, `BACK_EDGE`, `PARENT`) |
| `ACTUALIZAR_LOW` | `Low` del nodo baja por una arista de retroceso o por un hijo |
| `MARCAR_PUENTE` | Se confirma que la arista es puente |
| `RETROCEDER` | El DFS termina un nodo y vuelve a su padre |
| `FIN` | Fin del algoritmo |

Notas: `Nodo_Vecino = -1` significa "sin vecino" (por ejemplo, la raíz no tiene padre). `Orden_Visita` y `Low` valen `NULL` cuando aún no aplican.

## Referencias

- 3Blue1Brown — https://www.3blue1brown.com/
- Reducible — https://www.youtube.com/c/Reducible
- VisuAlgo — https://visualgo.net/

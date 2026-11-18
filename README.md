# Puentes en Grafos — Implementación y Animación

Proyecto Final 2 — **Anima tu Algoritmo o Estructura de Datos**  
Curso: Algoritmos y Estructuras de Datos (CS2023) — UTEC — Semestre 2026-2  
Docente: Víctor Racsó Galván Oyola

**Video:** [(https://youtu.be/TLwGAfyr-bQ)]

## Integrantes

| Integrante | Rol |
|---|---|
| Ariel Mathias Fernando Choque Marcelo | Implementación del algoritmo en C++ y generación de los CSV |
| Rodrigo de Santa Maria Anco Ito | Lectura de los CSV y animación en Manim |
| Gabriel Saavedra Peralta | Guion, informe, README y coordinación del formato del CSV |

## Descripción

Un **puente** es una arista de un grafo no dirigido cuya eliminación aumenta el número de componentes conexas. El algoritmo recorre el grafo con DFS y calcula, para cada nodo:

- **tin** (`Orden_Visita` en el CSV): momento en que el DFS descubre el nodo. No cambia una vez asignado.
- **low**: menor `tin` alcanzable desde el subárbol del nodo usando a lo más una arista de retroceso.

Una arista de árbol `(u, v)` es puente si `low[v] > tin[u]`.

**Complejidad:** tiempo O(V + E), espacio O(V + E).

## Arquitectura

```
C++ (algoritmo real)  ──►  3 archivos CSV  ──►  Python + Manim (animación)
```

La animación no se dibuja a mano: cada fila de los CSV es un paso real de la ejecución del algoritmo en C++, y Manim solo la reproduce.

## Cómo reproducir

1. Descargar el repositorio (clonar o ZIP desde GitHub).
2. **C++:** abrir la carpeta `/cpp` en CLion, compilar y ejecutar `main`. Se generan tres archivos en la carpeta de ejecución del proyecto:
   - `puentes_animacion.csv`
   - `caso_ciclo.csv`
   - `caso_arbol.csv`
3. Copiar los tres CSV a la carpeta `/python`.
4. **Python:** abrir `/python` en PyCharm.
   ```bash
   pip install manim
   manim -pqh puentes_animation.py Puentes
   ```
5. El video queda en `python/media/videos/`.

Si los CSV están en otra ruta, se pueden indicar con las variables de entorno `PUENTES_CSV`, `PUENTES_CSV_CICLO` y `PUENTES_CSV_ARBOL`.

## Grafos de la demostración

| Archivo | Grafo | Puentes |
|---|---|---|
| `puentes_animacion.csv` | Aristas `0-1`, `1-2`, `2-0` (ciclo) y `2-3`; nodo `4` aislado (caso borde) | Uno: `(2, 3)` |
| `caso_ciclo.csv` | Ciclo de 5 nodos | Ninguno |
| `caso_arbol.csv` | Árbol de 6 nodos | Todas las aristas |

## Formato del CSV

Columnas: `Iteracion,Accion,Nodo_Actual,Nodo_Vecino,Orden_Visita,Low,Tipo_Arista,Resultado`

| Accion | Significado |
|---|---|
| `CREAR_NODO` | Se agrega un nodo al grafo |
| `CREAR_ARISTA` | Se agrega una arista |
| `VISITAR` | El DFS descubre un nodo y le asigna `Orden_Visita` y `Low` |
| `EXPLORAR_ARISTA` | El DFS examina una arista (ver `Tipo_Arista`) |
| `ACTUALIZAR_LOW` | `Low` del nodo baja por una arista de retroceso o por un hijo |
| `MARCAR_PUENTE` | Se confirma que la arista es puente |
| `RETROCEDER` | El DFS termina un nodo y vuelve a su padre |
| `FIN` | Fin del algoritmo |

`Tipo_Arista` (solo en `EXPLORAR_ARISTA` y en los eventos que de ella derivan; `NONE` en el resto):

| Valor | Significado |
|---|---|
| `TREE_EDGE` | Arista hacia un nodo no visitado: el DFS avanza |
| `BACK_EDGE` | Arista hacia un ancestro ya visitado: puede bajar `low` |
| `FORWARD_EDGE` | Arista hacia un descendiente ya visitado: no tiene efecto |
| `PARENT` | Arista hacia el padre: se ignora |

Notas: `Nodo_Vecino = -1` significa "sin vecino" (por ejemplo, la raíz no tiene padre). `Orden_Visita` y `Low` valen `NULL` cuando aún no aplican. En `MARCAR_PUENTE`, `Orden_Visita` es el de `u` y `Low` es el del hijo `v`.

## Referencias

- 3Blue1Brown — https://www.3blue1brown.com/
- Reducible — https://www.youtube.com/c/Reducible
- VisuAlgo — https://visualgo.net/

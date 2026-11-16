# Puentes en Grafos — Implementación y Animación

Proyecto Final 2: **Anima tu Algoritmo o Estructura de Datos**

Curso: Algoritmos y Estructuras de Datos (CS2023) — UTEC — Semestre 2026-2

Docente: Víctor Racsó Galván Oyola

**Video:** [`output/Puentes.mp4`](output/Puentes.mp4) (1920×1080, 60 FPS)

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
C++ (algoritmo real)  ->  CSV de eventos  ->  Python + Manim (animación)
```

La animación no se dibuja a mano: cada fila del CSV es un paso real de la ejecución del algoritmo en C++. El script de Manim solo lee el CSV y comprueba que sus eventos sean coherentes (pila de DFS, valores de `low` y la condición `low[v] > tin[u]` frente a cada `MARCAR_PUENTE`); no recalcula el algoritmo.

Los dos casos borde del video (un ciclo y un árbol) son ejecuciones independientes del mismo programa C++ sobre otros grafos, con su propio CSV.

## Estructura del repositorio

```
cpp/       Proyecto_AED.cpp, CMakeLists.txt y grafos de entrada (cpp/grafos/)
python/    puentes_animation.py (animación Manim) y requirements.txt
output/    CSV generados por el C++ y video final
tests/     pruebas reproducibles del algoritmo, del CSV y de la animación
```

## Requisitos

- Compilador C++17 (`g++`). Probado con g++ 6.3 (MinGW) y `-std=c++17`.
- Python 3 (probado con 3.13) y Manim 0.21.0.
- Fuente **Times New Roman** instalada, la misma tipografía del video de Skip List (Windows y macOS la incluyen). Si falta, Pango usa otra fuente y el aspecto cambia.
- No hace falta LaTeX: la animación solo usa `Text`.

## Cómo reproducir

Todos los comandos se ejecutan desde la raíz del repositorio.

```bash
git clone https://github.com/GabrielSaavedraP/AED-Proyecto-Puentes.git
cd AED-Proyecto-Puentes
```

### 1. C++ y CSV

```bash
g++ -std=c++17 -O2 -o cpp/puentes cpp/Proyecto_AED.cpp
cpp/puentes cpp/grafos/ejemplo.txt output/puentes_animacion.csv
cpp/puentes cpp/grafos/ciclo.txt   output/caso_ciclo.csv
cpp/puentes cpp/grafos/arbol.txt   output/caso_arbol.csv
```

En Windows el ejecutable es `cpp/puentes.exe`. Cada ejecución imprime el resumen (`Puente: (2, 3)`, etc.) y escribe su CSV. Sin argumentos, `cpp/puentes` usa el grafo de ejemplo y escribe `puentes_animacion.csv` en la carpeta actual.

También se puede abrir la carpeta `cpp/` en CLion: `cpp/CMakeLists.txt` define el ejecutable `puentes`. La compilación comprobada en las pruebas es la de `g++` indicada arriba.

### 2. Pruebas

```bash
pip install -r python/requirements.txt
python -m unittest discover -s tests -v
```

### 3. Animación

```bash
manim -qh python/puentes_animation.py Puentes
```

El video queda en `media/videos/puentes_animation/1080p60/Puentes.mp4`. Para una vista previa rápida usar `-ql` (480p, 15 FPS; carpeta `480p15`).

La animación busca los CSV en este orden: la variable de entorno (`PUENTES_CSV`, `PUENTES_CSV_CICLO`, `PUENTES_CSV_ARBOL`), la carpeta `python/` y la carpeta `output/`.

## Grafos incluidos

| Archivo | Grafo | Puentes esperados |
|---|---|---|
| `cpp/grafos/ejemplo.txt` | Ciclo `0-1-2-0`, arista `2-3` y nodo `4` aislado | un único puente: `(2, 3)` |
| `cpp/grafos/ciclo.txt` | Ciclo de 5 nodos | ninguno |
| `cpp/grafos/arbol.txt` | Árbol de 6 nodos | las 5 aristas |

Formato de los archivos de grafo: una línea `n m` y luego `m` líneas `u v`, con vértices numerados de `0` a `n-1` (máximo 1000 vértices).

## Formato del CSV

Columnas: `Iteracion,Accion,Nodo_Actual,Nodo_Vecino,Orden_Visita,Low,Tipo_Arista,Resultado`

| Accion | Significado |
|---|---|
| `CREAR_NODO` | Se agrega un nodo al grafo |
| `CREAR_ARISTA` | Se agrega una arista |
| `VISITAR` | El DFS descubre un nodo y le asigna `Orden_Visita` y `Low`; `Nodo_Vecino` es su padre |
| `EXPLORAR_ARISTA` | El DFS examina una arista (ver `Tipo_Arista`) |
| `ACTUALIZAR_LOW` | `Low` del nodo baja por una arista de retroceso o por un hijo |
| `MARCAR_PUENTE` | Se confirma que la arista es puente; `Low` es `low[v]` y `Orden_Visita` es `tin[u]` |
| `RETROCEDER` | El DFS termina un nodo y vuelve a su padre |
| `FIN` | Fin del algoritmo |

| Tipo_Arista | Significado |
|---|---|
| `TREE_EDGE` | Arista hacia un nodo no visitado: el DFS avanza |
| `PARENT` | La arista por la que se llegó al nodo; se ignora |
| `BACK_EDGE` | Arista hacia un ancestro ya visitado |
| `FORWARD_EDGE` | Arista hacia un descendiente ya terminado; ya se procesó como `BACK_EDGE` desde ese nodo |
| `SELF_LOOP` | Bucle `(u, u)`; se ignora |

Notas: `Nodo_Vecino = -1` significa «sin vecino» (por ejemplo, la raíz no tiene padre). `Orden_Visita` y `Low` valen `NULL` cuando aún no aplican.

## Correcciones a la implementación C++

Se conservó el algoritmo del equipo, su formato de CSV y su complejidad O(V + E). Cambios:

1. **Aristas hacia descendientes.** En la versión original, cuando un nodo veía a un descendiente ya visitado (por ejemplo `0` viendo a `2` en el grafo de ejemplo) lo registraba como `BACK_EDGE`, aunque esa arista ya se había procesado desde el descendiente. Ahora solo es `BACK_EDGE` si `tin[v] < tin[u]`; en caso contrario se registra como `FORWARD_EDGE`. Con el grafo de ejemplo cambia únicamente la fila 27 del CSV.
2. **Padre por arista, no por vértice.** El padre se identifica con el identificador de la arista y no con el vértice. Con aristas paralelas, la segunda arista hacia el padre cuenta como retroceso; antes se ignoraba y se reportaba un puente falso.
3. **Bucles y validación.** Los bucles `(u, u)` se registran como `SELF_LOOP` y se ignoran; las aristas fuera de rango y los archivos inválidos terminan con un mensaje de error.
4. **Argumentos opcionales** `cpp/puentes [grafo.txt] [salida.csv]` y resumen de puentes por consola. Sin argumentos el comportamiento es el original.

## Pruebas

`python -m unittest discover -s tests -v` compila el C++ en una carpeta temporal y comprueba:

- Cada ejecución contra dos oráculos independientes: la definición de puente (quitar la arista y contar componentes) y una implementación de referencia en Python (DFS iterativo) que debe producir el mismo CSV, evento por evento.
- El ejemplo, el ciclo, el árbol, grafos desconectados, nodos aislados, aristas paralelas, bucles, retrocesos que bajan `low`, 80 grafos aleatorios y el crecimiento lineal de los eventos en grafos de hasta 1000 vértices.
- Que los CSV de `output/` coincidan exactamente con lo que produce el C++.
- La lectura del CSV en la animación (se rechazan archivos corruptos) y que las etiquetas `tin`/`low` no tapen nodos ni crucen aristas.

## Animación

Escena principal `Puentes` (`python/puentes_animation.py`), con la misma identidad visual de Skip List: fondo negro, paleta de Manim, tipografía serif, indicador amarillo, estado inferior y cierre con complejidad.

1. Introducción con título e integrantes.
2. Qué es un puente: quitar una arista de un ciclo no desconecta el grafo; quitar el puente sí.
3. DFS y el significado de `tin` y `low`.
4. Construcción del grafo a partir de `CREAR_NODO` y `CREAR_ARISTA`.
5. Recorrido DFS con pila, `tin`/`low` junto a cada nodo y la condición `low[v] > tin[u]` en cada retroceso.
6. Tabla de verificación con los valores reales de cada arista del árbol.
7. Casos borde: ciclo (ningún puente) y árbol (todas las aristas son puentes), cada uno con su propio CSV.
8. Complejidad O(V + E) en tiempo y espacio, y cierre.

## Referencias

- 3Blue1Brown — https://www.3blue1brown.com/
- Reducible — https://www.youtube.com/c/Reducible
- VisuAlgo — https://visualgo.net/

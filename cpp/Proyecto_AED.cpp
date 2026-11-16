#include <iostream>
#include <vector>
#include <fstream>
#include <string>
#include <algorithm>
#include <cstdlib>

using namespace std;

const int N = 1000;
int n, m; // n: vértices, m: aristas
vector<pair<int, int>> adj[N]; // (vecino, id_arista): el id distingue aristas paralelas
bool visited[N];
int tin[N], low[N];
int timer = 0;

// Puentes encontrados (solo para el resumen por consola)
vector<pair<int, int>> puentes;

// Variables para el CSV de animación
ofstream csvFile;
int iteracion = 1;

void logEvent(string accion, int u, int v, int t_in, int l_val, string tipoArista, string resultado) {
    if (csvFile.is_open()) {
        csvFile << iteracion++ << "," << accion << "," << u << "," << v << ","
                << (t_in == -1 ? "NULL" : to_string(t_in)) << ","
                << (l_val == -1 ? "NULL" : to_string(l_val)) << ","
                << tipoArista << "," << resultado << "\n";
    }
}

// idPadre: id de la ARISTA por la que se llegó a u (no solo el vértice padre).
// Así una segunda arista paralela hacia el padre cuenta como retroceso y no se confunde con el padre.
void DFS(int u, int p = -1, int idPadre = -1) {
    visited[u] = true;
    tin[u] = low[u] = timer++;

    logEvent("VISITAR", u, p, tin[u], low[u], "NONE", "NODO_DESCUBIERTO");

    for (const pair<int, int>& arista : adj[u]) {
        int v = arista.first;
        int id = arista.second;

        if (id == idPadre) {
            logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "PARENT", "IGNORAR_PADRE");
            continue;
        }
        if (v == u) {
            logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "SELF_LOOP", "BUCLE_IGNORADO");
            continue;
        }
        if (visited[v]) {
            if (tin[v] < tin[u]) {
                // v es un ancestro de u: arista de retroceso real.
                logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "BACK_EDGE", "ARISTA_RETROCESO");
                int oldLow = low[u];
                low[u] = min(low[u], tin[v]);
                if (low[u] != oldLow) {
                    logEvent("ACTUALIZAR_LOW", u, v, tin[u], low[u], "BACK_EDGE", "LOW_ACTUALIZADO_POR_CICLO");
                }
            } else {
                // v es un descendiente ya terminado: esta arista ya se procesó como
                // retroceso desde v, aquí solo se vuelve a ver desde el ancestro.
                logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "FORWARD_EDGE", "ARISTA_YA_PROCESADA");
            }
        } else {
            logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "TREE_EDGE", "AVANZAR_DFS");
            DFS(v, u, id);

            int oldLow = low[u];
            low[u] = min(low[u], low[v]);
            if (low[u] != oldLow) {
                logEvent("ACTUALIZAR_LOW", u, v, tin[u], low[u], "TREE_EDGE", "LOW_PROPAGADO_HIJO");
            }

            if (low[v] > tin[u]) {
                puentes.push_back({u, v});
                logEvent("MARCAR_PUENTE", u, v, tin[u], low[v], "TREE_EDGE", "PUENTE_ENCONTRADO");
            }
        }
    }
    logEvent("RETROCEDER", u, p, tin[u], low[u], "NONE", "FIN_NODO");
}

void agregarArista(int u, int v) {
    if (u < 0 || u >= n || v < 0 || v >= n) {
        cerr << "Error: arista (" << u << ", " << v << ") fuera de rango [0, " << n - 1 << "]" << endl;
        exit(1);
    }
    adj[u].push_back({v, m});
    if (u != v) adj[v].push_back({u, m}); // un bucle se guarda una sola vez
    m++;
    logEvent("CREAR_ARISTA", u, v, -1, -1, "NONE", "SETUP_GRAFO");
}

// Formato del archivo de grafo:  "n m"  y luego m líneas "u v"  (vértices 0..n-1)
void leerGrafo(const string& ruta, vector<pair<int, int>>& aristas) {
    ifstream in(ruta);
    int cantidadAristas = 0;
    if (!in.is_open() || !(in >> n >> cantidadAristas) || n < 0 || n > N || cantidadAristas < 0) {
        cerr << "Error: no se pudo leer un grafo valido (n <= " << N << ") desde '" << ruta << "'" << endl;
        exit(1);
    }
    for (int i = 0; i < cantidadAristas; ++i) {
        int u, v;
        if (!(in >> u >> v)) {
            cerr << "Error: faltan aristas en '" << ruta << "'" << endl;
            exit(1);
        }
        aristas.push_back({u, v});
    }
}

// Uso: puentes [grafo.txt] [salida.csv]
//   Sin argumentos se usa el grafo de ejemplo y se escribe puentes_animacion.csv
int main(int argc, char* argv[]) {
    string archivoGrafo = argc > 1 ? argv[1] : "";
    string archivoCsv = argc > 2 ? argv[2] : "puentes_animacion.csv";

    vector<pair<int, int>> aristas;
    if (archivoGrafo.empty()) {
        // Se arma la instancia ilustrativa + caso borde (nodo 4 aislado)
        n = 5;
        aristas = {{0, 1}, {1, 2}, {2, 0}, {2, 3}};
    } else {
        leerGrafo(archivoGrafo, aristas);
    }

    csvFile.open(archivoCsv);
    if (!csvFile.is_open()) {
        cerr << "Error: no se pudo crear '" << archivoCsv << "'" << endl;
        return 1;
    }
    csvFile << "Iteracion,Accion,Nodo_Actual,Nodo_Vecino,Orden_Visita,Low,Tipo_Arista,Resultado\n";

    // Definimos los n nodos (0 al n-1)
    for (int i = 0; i < n; ++i) {
        visited[i] = false;
        tin[i] = low[i] = -1;
        logEvent("CREAR_NODO", i, -1, -1, -1, "NONE", "SETUP_GRAFO");
    }

    for (const pair<int, int>& arista : aristas) {
        agregarArista(arista.first, arista.second);
    }

    // Recorrer todas las componentes
    for (int i = 0; i < n; ++i) {
        if (!visited[i]) {
            DFS(i);
        }
    }

    logEvent("FIN", -1, -1, -1, -1, "NONE", "ALGORITMO_COMPLETADO");
    csvFile.close();

    cout << "Archivo CSV generado exitosamente." << endl;
    cout << "Vertices: " << n << "  Aristas: " << m << "  Puentes: " << puentes.size() << endl;
    for (const pair<int, int>& p : puentes) {
        cout << "  Puente: (" << p.first << ", " << p.second << ")" << endl;
    }
    return 0;
}

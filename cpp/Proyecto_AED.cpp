#include <iostream>
#include <vector>
#include <fstream>
#include <string>
#include <algorithm>
#include <utility>

using namespace std;

const int N = 1000;
int n, m; // n: vértices, m: aristas
vector<int> adj[N];
bool visited[N];
int tin[N], low[N];
int timer_dfs = 0;

// Variables para el CSV de animación
ofstream csvFile;
int iteracion = 1;

void logEvent(const string& accion, int u, int v, int t_in, int l_val,
              const string& tipoArista, const string& resultado) {
    if (csvFile.is_open()) {
        csvFile << iteracion++ << "," << accion << "," << u << "," << v << ","
                << (t_in == -1 ? "NULL" : to_string(t_in)) << ","
                << (l_val == -1 ? "NULL" : to_string(l_val)) << ","
                << tipoArista << "," << resultado << "\n";
    }
}

void DFS(int u, int p = -1) {
    visited[u] = true;
    tin[u] = low[u] = timer_dfs++;

    logEvent("VISITAR", u, p, tin[u], low[u], "NONE", "NODO_DESCUBIERTO");

    for (int v : adj[u]) {
        if (v == p) {
            logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "PARENT", "IGNORAR_PADRE");
            continue;
        }
        if (visited[v]) {
            if (tin[v] > tin[u]) {
                logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "FORWARD_EDGE", "ARISTA_HACIA_DESCENDIENTE");
                continue;
            }
            logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "BACK_EDGE", "ARISTA_RETROCESO");
            int oldLow = low[u];
            low[u] = min(low[u], tin[v]);
            if (low[u] != oldLow) {
                logEvent("ACTUALIZAR_LOW", u, v, tin[u], low[u], "BACK_EDGE", "LOW_ACTUALIZADO_POR_CICLO");
            }
        } else {
            logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "TREE_EDGE", "AVANZAR_DFS");
            DFS(v, u);

            int oldLow = low[u];
            low[u] = min(low[u], low[v]);
            if (low[u] != oldLow) {
                logEvent("ACTUALIZAR_LOW", u, v, tin[u], low[u], "TREE_EDGE", "LOW_PROPAGADO_HIJO");
            }

            if (low[v] > tin[u]) {
                logEvent("MARCAR_PUENTE", u, v, tin[u], low[v], "TREE_EDGE", "PUENTE_ENCONTRADO");
            }
        }
    }
    logEvent("RETROCEDER", u, p, tin[u], low[u], "NONE", "FIN_NODO");
}

void agregarArista(int u, int v) {
    adj[u].push_back(v);
    adj[v].push_back(u);
    logEvent("CREAR_ARISTA", u, v, -1, -1, "NONE", "SETUP_GRAFO");
}

void correr(const string& archivo, int nodos, const vector<pair<int, int>>& aristas) {
    for (int i = 0; i < N; ++i) {
        adj[i].clear();
        visited[i] = false;
        tin[i] = low[i] = -1;
    }
    timer_dfs = 0;
    iteracion = 1;
    n = nodos;

    csvFile.open(archivo);
    csvFile << "Iteracion,Accion,Nodo_Actual,Nodo_Vecino,Orden_Visita,Low,Tipo_Arista,Resultado\n";

    for (int i = 0; i < n; ++i) {
        logEvent("CREAR_NODO", i, -1, -1, -1, "NONE", "SETUP_GRAFO");
    }
    for (const auto& a : aristas) {
        agregarArista(a.first, a.second);
    }

    // Recorrer todas las componentes
    for (int i = 0; i < n; ++i) {
        if (!visited[i]) {
            DFS(i);
        }
    }

    logEvent("FIN", -1, -1, -1, -1, "NONE", "ALGORITMO_COMPLETADO");
    csvFile.close();
}

int main() {
    // Definimos un grafo de 5 nodos (0 al 4)
    // Se arma la instancia ilustrativa + caso borde (nodo 4 aislado)
    correr("puentes_animacion.csv", 5, {{0, 1}, {1, 2}, {2, 0},  // Ciclo
                                        {2, 3}});                 // Puente
    correr("caso_ciclo.csv", 5, {{0, 1}, {1, 2}, {2, 3}, {3, 4}, {4, 0}});
    correr("caso_arbol.csv", 6, {{0, 1}, {0, 2}, {1, 3}, {1, 4}, {2, 5}});

    cout << "CSV generados exitosamente." << endl;
    return 0;
}

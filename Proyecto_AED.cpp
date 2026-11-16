#include <iostream>
#include <vector>
#include <fstream>
#include <string>
#include <algorithm>

using namespace std;

const int N = 1000;
int n, m; // n: vértices, m: aristas
vector<int> adj[N];
bool visited[N];
int tin[N], low[N];
int timer = 0;

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

void DFS(int u, int p = -1) {
    visited[u] = true;
    tin[u] = low[u] = timer++;

    logEvent("VISITAR", u, p, tin[u], low[u], "NONE", "NODO_DESCUBIERTO");

    for (int v : adj[u]) {
        if (v == p) {
            logEvent("EXPLORAR_ARISTA", u, v, tin[u], low[u], "PARENT", "IGNORAR_PADRE");
            continue;
        }
        if (visited[v]) {
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

int main() {
    csvFile.open("puentes_animacion.csv");
    csvFile << "Iteracion,Accion,Nodo_Actual,Nodo_Vecino,Orden_Visita,Low,Tipo_Arista,Resultado\n";

    // Definimos un grafo de 5 nodos (0 al 4)
    n = 5;
    for (int i = 0; i < n; ++i) {
        visited[i] = false;
        tin[i] = low[i] = -1;
        logEvent("CREAR_NODO", i, -1, -1, -1, "NONE", "SETUP_GRAFO");
    }

    // Se arma la instancia ilustrativa + caso borde (nodo 4 aislado)
    agregarArista(0, 1);
    agregarArista(1, 2);
    agregarArista(2, 0); // Ciclo
    agregarArista(2, 3); // Puente

    // Recorrer todas las componentes
    for (int i = 0; i < n; ++i) {
        if (!visited[i]) {
            DFS(i);
        }
    }

    logEvent("FIN", -1, -1, -1, -1, "NONE", "ALGORITMO_COMPLETADO");
    csvFile.close();

    cout << "Archivo CSV generado exitosamente." << endl;
    return 0;
}
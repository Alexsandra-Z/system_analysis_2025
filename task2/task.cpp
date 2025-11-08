import numpy as np
import math
from typing import Tuple, List, Tuple

def compute_entropy(matrices: List[np.ndarray]) -> Tuple[float, float]:
    n = matrices[0].shape[0]
    k = len(matrices)
    total_entropy = 0.0
    for matrix in matrices:
        for i in range(n):
            for j in range(n):
                if i != j:
                    p_ij = matrix[i, j] / (n - 1)
                    if p_ij > 0:
                        total_entropy += p_ij * math.log2(p_ij)

    H = -total_entropy
    H_max = (1 / math.e) * n * k
    h = H / H_max if H_max > 0 else 0
    return H, h


def generate_all_edge_permutations(edges: List[Tuple[str, str]], vertices: List[str]) -> List[List[Tuple[str, str]]]:
    n = len(vertices)
    all_possible_edges = [(vertices[i], vertices[j]) for i in range(n) for j in range(n) if i != j]
    existing_edges_set = set(edges)
    possible_new_edges = [edge for edge in all_possible_edges if edge not in existing_edges_set]

    permutations = []
    for remove_idx in range(len(edges)):
        for new_edge in possible_new_edges:
            new_edges = edges.copy()
            new_edges[remove_idx] = new_edge
            permutations.append(new_edges)
    return permutations

def main(s: str, e: str) -> Tuple[float, float]:
    # Разбор строки CSV в список рёбер
    lines = s.strip().split('\n')
    edges = []
    verts = set()
    for line in lines:
        if line.strip():
            v1, v2 = line.split(',')
            v1 = v1.strip()
            v2 = v2.strip()
            verts.add(v1)
            verts.add(v2)
            edges.append((v1, v2))
    #Упорядочевание вершин
    other_verts = sorted(v for v in verts if v != e)
    vertices = [e] + other_verts
    n = len(vertices)
    vert_index = {v: i for i, v in enumerate(vertices)}

    all_permutations = generate_all_edge_permutations(edges, vertices)

    best_H = -float('inf')
    best_h = 0
    best_edges = None

    #Перебор всех перестановок
    for perm_edges in all_permutations:
        adj = np.zeros((n, n), dtype=bool)
        for v1, v2 in perm_edges:
            i = vert_index[v1]
            j = vert_index[v2]
            adj[i, j] = True

        r1_np = adj.astype(int)
        r2_np = r1_np.T

        tranzitive_r = adj.copy()
        for _ in range(1, n):
            tranzitive_r = tranzitive_r | (tranzitive_r @ adj)

        r3_np = (tranzitive_r & ~adj).astype(int)
        r4_np = r3_np.T

        r2_bool = r2_np.astype(bool)
        r5_np = np.zeros((n, n), dtype=int)
        for i in range(n):
            for j in range(i + 1, n):
                if np.any(r2_bool[i] & r2_bool[j]):
                    r5_np[i, j] = 1
                    r5_np[j, i] = 1

        matrices = [r1_np, r2_np, r3_np, r4_np, r5_np]
        H, h_val = compute_entropy(matrices)

        if H > best_H:
            best_H = H
            best_h = h_val
            best_edges = perm_edges.copy()

    #Округление до одного знака после запятой
    return round(best_H, 1), round(best_h, 1)


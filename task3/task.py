from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union


RankItem = Union[int, List[int]]
Ranking = List[RankItem]


def _relaxed_json_loads(s: str) -> Any:
    s2 = re.sub(r",\s*([\]\}])", r"\1", s)
    return json.loads(s2)


def _flatten(r: Ranking) -> List[int]:
    out: List[int] = []
    for e in r:
        if isinstance(e, list):
            out.extend(int(x) for x in e)
        else:
            out.append(int(e))
    return out


def _levels(r: Ranking) -> Dict[int, int]:
    lvl: Dict[int, int] = {}
    for i, e in enumerate(r):
        if isinstance(e, list):
            for x in e:
                lvl[int(x)] = i
        else:
            lvl[int(e)] = i
    return lvl


def _build_relation_matrix(r: Ranking, objs: List[int]) -> List[List[int]]:
    lvl = _levels(r)
    n = len(objs)
    Y = [[0] * n for _ in range(n)]
    for i, oi in enumerate(objs):
        li = lvl[oi]
        row = Y[i]
        for j, oj in enumerate(objs):
            row[j] = 1 if lvl[oj] >= li else 0
    return Y


def _transpose(M: List[List[int]]) -> List[List[int]]:
    return [list(col) for col in zip(*M)]


def _and(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n = len(A)
    return [[1 if (A[i][j] and B[i][j]) else 0 for j in range(n)] for i in range(n)]


def _or(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n = len(A)
    return [[1 if (A[i][j] or B[i][j]) else 0 for j in range(n)] for i in range(n)]


def _warshall_closure(E: List[List[int]]) -> List[List[int]]:
    n = len(E)
    R = [row[:] for row in E]
    for k in range(n):
        rk = R[k]
        for i in range(n):
            if R[i][k]:
                ri = R[i]
                for j in range(n):
                    if rk[j]:
                        ri[j] = 1
    return R


def _connected_components_from_equiv(E: List[List[int]], objs: List[int]) -> List[List[int]]:
    n = len(objs)
    seen = [False] * n
    comps: List[List[int]] = []

    for start in range(n):
        if seen[start]:
            continue
        q = deque([start])
        seen[start] = True
        comp_idx: List[int] = []
        while q:
            v = q.popleft()
            comp_idx.append(v)
          
            for u in range(n):
                if not seen[u] and E[v][u]:
                    seen[u] = True
                    q.append(u)

        comp = sorted(objs[i] for i in comp_idx)
        comps.append(comp)

    comps.sort(key=lambda c: (c[0], len(c)))
    return comps


def _core_contradictions_strict(rA: Ranking, rB: Ranking) -> List[Tuple[int, int]]:
    lvlA = _levels(rA)
    lvlB = _levels(rB)

    objs = sorted(set(lvlA) | set(lvlB))
    core: List[Tuple[int, int]] = []
    for idx_i in range(len(objs)):
        i = objs[idx_i]
        for idx_j in range(idx_i + 1, len(objs)):
            j = objs[idx_j]
            a_ij = (lvlA[i] < lvlA[j])
            a_ji = (lvlA[j] < lvlA[i])
            b_ij = (lvlB[i] < lvlB[j])
            b_ji = (lvlB[j] < lvlB[i])

            if (a_ij and b_ji) or (a_ji and b_ij):
                core.append((i, j))
    return core


def _clusters_order_from_C(C: List[List[int]], clusters: List[List[int]], objs: List[int]) -> List[List[int]]:

    idx = {o: k for k, o in enumerate(objs)}
    m = len(clusters)

    def leq(A: List[int], B: List[int]) -> bool:
        for a in A:
            ia = idx[a]
            row = C[ia]
            for b in B:
                if row[idx[b]] == 0:
                    return False
        return True

    edges: List[List[int]] = [[] for _ in range(m)]
    indeg = [0] * m

    for i in range(m):
        for j in range(m):
            if i == j:
                continue
            A = clusters[i]
            B = clusters[j]
            ij = leq(A, B)
            ji = leq(B, A)
            if ij and not ji:
                edges[i].append(j)
                indeg[j] += 1


    order: List[int] = []
    zero = [i for i in range(m) if indeg[i] == 0]
    zero.sort(key=lambda k: (clusters[k][0], len(clusters[k])))

    while zero:
        v = zero.pop(0)
        order.append(v)
        for u in edges[v]:
            indeg[u] -= 1
            if indeg[u] == 0:
                zero.append(u)
        zero.sort(key=lambda k: (clusters[k][0], len(clusters[k])))


    if len(order) < m:
        rest = [i for i in range(m) if i not in set(order)]
        rest.sort(key=lambda k: (clusters[k][0], len(clusters[k])))
        order.extend(rest)

    return [clusters[i] for i in order]


def _as_ranking_output(clusters: List[List[int]]) -> Ranking:

    out: Ranking = []
    for c in clusters:
        if len(c) == 1:
            out.append(c[0])
        else:
            out.append(c)
    return out


def main(json_a: str, json_b: str) -> str:

    rA_raw = _relaxed_json_loads(json_a)
    rB_raw = _relaxed_json_loads(json_b)


    rA: Ranking = rA_raw  
    rB: Ranking = rB_raw 

    objs = sorted(set(_flatten(rA)) | set(_flatten(rB)))
    if not objs:
        return json.dumps([], ensure_ascii=False)

    YA = _build_relation_matrix(rA, objs)
    YB = _build_relation_matrix(rB, objs)

    core_pairs = _core_contradictions_strict(rA, rB)

    pos = {o: i for i, o in enumerate(objs)}
    core_idx = [(pos[i], pos[j]) for (i, j) in core_pairs]

    C = _and(YA, YB)

    for i, j in core_idx:
        C[i][j] = 1
        C[j][i] = 1

    #матрица эквивалентности
    CT = _transpose(C)
    E = _and(C, CT)

    #транзитивное замыкание
    E_star = _warshall_closure(E)

    # кластеры = компоненты связности графа E*
    clusters = _connected_components_from_equiv(E_star, objs)

    # упорядочивание кластеров по C
    clusters_sorted = _clusters_order_from_C(C, clusters, objs)

    #формирование результата
    result_ranking = _as_ranking_output(clusters_sorted)
    return json.dumps(result_ranking, ensure_ascii=False)

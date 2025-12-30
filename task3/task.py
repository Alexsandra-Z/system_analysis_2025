from __future__ import annotations

import json
import re
from collections import deque
from typing import Any, Dict, List, Tuple, Union

RankItem = Union[int, List[int]]
Ranking = List[RankItem]


def main(json_a: str, json_b: str) -> str:
    def loads_relaxed(s: str) -> Any:
        return json.loads(re.sub(r",\s*([\]\}])", r"\1", s))

    def flatten(r: Ranking) -> List[int]:
        out: List[int] = []
        for e in r:
            if isinstance(e, list):
                out.extend(int(x) for x in e)
            else:
                out.append(int(e))
        return out

    def levels(r: Ranking) -> Dict[int, int]:
        lvl: Dict[int, int] = {}
        for i, e in enumerate(r):
            if isinstance(e, list):
                for x in e:
                    lvl[int(x)] = i
            else:
                lvl[int(e)] = i
        return lvl

    def build_Y(r: Ranking, objs: List[int]) -> List[List[int]]:
        lvl = levels(r)
        n = len(objs)
        Y = [[0] * n for _ in range(n)]
        for i, oi in enumerate(objs):
            li = lvl[oi]
            row = Y[i]
            for j, oj in enumerate(objs):
                row[j] = 1 if lvl[oj] >= li else 0
        return Y

    def mat_and(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
        n = len(A)
        return [[1 if (A[i][j] and B[i][j]) else 0 for j in range(n)] for i in range(n)]

    def transpose(M: List[List[int]]) -> List[List[int]]:
        return [list(col) for col in zip(*M)]

    def warshall(E: List[List[int]]) -> List[List[int]]:
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

    def contradictions_strict(rA: Ranking, rB: Ranking) -> List[Tuple[int, int]]:
        lvlA = levels(rA)
        lvlB = levels(rB)
        objs2 = sorted(set(lvlA) | set(lvlB))
        core: List[Tuple[int, int]] = []
        for a in range(len(objs2)):
            i = objs2[a]
            for b in range(a + 1, len(objs2)):
                j = objs2[b]
                a_ij = lvlA[i] < lvlA[j]
                a_ji = lvlA[j] < lvlA[i]
                b_ij = lvlB[i] < lvlB[j]
                b_ji = lvlB[j] < lvlB[i]
                if (a_ij and b_ji) or (a_ji and b_ij):
                    core.append((i, j))
        return core

    def components(E: List[List[int]], objs: List[int]) -> List[List[int]]:
        n = len(objs)
        seen = [False] * n
        comps: List[List[int]] = []
        for start in range(n):
            if seen[start]:
                continue
            q = deque([start])
            seen[start] = True
            idxs: List[int] = []
            while q:
                v = q.popleft()
                idxs.append(v)
                row = E[v]
                for u in range(n):
                    if not seen[u] and row[u]:
                        seen[u] = True
                        q.append(u)
            comp = sorted(objs[i] for i in idxs)
            comps.append(comp)
        comps.sort(key=lambda c: (c[0], len(c)))
        return comps

    def order_clusters(C: List[List[int]], clusters: List[List[int]], objs: List[int]) -> List[List[int]]:
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
                ij = leq(clusters[i], clusters[j])
                ji = leq(clusters[j], clusters[i])
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
            used = set(order)
            rest = [i for i in range(m) if i not in used]
            rest.sort(key=lambda k: (clusters[k][0], len(clusters[k])))
            order.extend(rest)

        return [clusters[i] for i in order]

    def to_output(clusters: List[List[int]]) -> Ranking:
        out: Ranking = []
        for c in clusters:
            out.append(c[0] if len(c) == 1 else c)
        return out

    rA_raw = loads_relaxed(json_a)
    rB_raw = loads_relaxed(json_b)
    if not isinstance(rA_raw, list) or not isinstance(rB_raw, list):
        raise ValueError("Ожидались JSON-списки ранжировок (list).")

    rA: Ranking = rA_raw  
    rB: Ranking = rB_raw 

    objs = sorted(set(flatten(rA)) | set(flatten(rB)))
    if not objs:
        return json.dumps([], ensure_ascii=False)

    YA = build_Y(rA, objs)
    YB = build_Y(rB, objs)

    C = mat_and(YA, YB)

    pos = {o: i for i, o in enumerate(objs)}
    for i, j in contradictions_strict(rA, rB):
        ii, jj = pos[i], pos[j]
        C[ii][jj] = 1
        C[jj][ii] = 1

    E = mat_and(C, transpose(C))
    E_star = warshall(E)

    clusters = components(E_star, objs)
    clusters_sorted = order_clusters(C, clusters, objs)

    return json.dumps(to_output(clusters_sorted), ensure_ascii=False)

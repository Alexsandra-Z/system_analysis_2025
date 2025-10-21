from typing import List, Tuple
import csv
from io import StringIO
from collections import defaultdict, deque


def main(s: str, e: str) -> Tuple[
    List[List[bool]],
    List[List[bool]],
    List[List[bool]],
    List[List[bool]],
    List[List[bool]]
]:
    #Считывам входные данные, создаём картеж для ребер графа
    edges = []
    reader = csv.reader(StringIO(s))
    for row in reader:
        edges.append((row[0].strip(), row[1].strip()))

    #Определяем множество вершин, присваиваем им индексы
    nodes = sorted({v for edge in edges for v in edge})
    n = len(nodes)
    idx = {node: i for i, node in enumerate(nodes)}

    #Строим граф
    graph = defaultdict(list)
    for u, v in edges:
        graph[u].append(v)

    #Функция для определения уровней
    def bfs_levels(root):
        levels = {root: 0}
        queue = deque([root])
        while queue:
            u = queue.popleft()
            for v in graph[u]:
                if v not in levels:
                    levels[v] = levels[u] + 1
                    queue.append(v)
        return levels

    levels = bfs_levels(e)

    #Инициализация матриц, заполнение значениями по умолчанию
    r1 = [[False]*n for _ in range(n)]
    r2 = [[False]*n for _ in range(n)]
    r3 = [[False]*n for _ in range(n)]
    r4 = [[False]*n for _ in range(n)]
    r5 = [[False]*n for _ in range(n)]

    #r1 и r2
    for u, v in edges:
        i, j = idx[u], idx[v]
        r1[i][j] = True  #непосредственное управление
        r2[j][i] = True  #Непосредственное подчинение

    #r3 и r4
    def dfs_paths(start):
        visited = set()
        stack = [start]
        while stack:
            u = stack.pop()
            for v in graph[u]:
                if v not in visited:
                    visited.add(v)
                    stack.append(v)
        return visited

    for u in nodes:
        reachable = dfs_paths(u)
        for v in reachable:
            if u != v:
                i, j = idx[u], idx[v]
                #если нет прямого отношения, то опосредованное
                if not r1[i][j]:
                    r3[i][j] = True
                    r4[j][i] = True

    #r5 (соподчинение на одном уровне)
    parent = defaultdict(list)
    for u, v in edges:
        parent[v].append(u)

    for i, u in enumerate(nodes):
        for j, v in enumerate(nodes):
            if i != j and levels.get(u) == levels.get(v):
                #есть хотя бы один общий начальник
                if set(parent[u]) & set(parent[v]):
                    r5[i][j] = True

    return r1, r2, r3, r4, r5

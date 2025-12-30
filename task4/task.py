from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Tuple

Point = Tuple[float, float]

_NORMALIZE = {
    "нормально": "комфортно",
    "слабо": "слабый",
    "умеренно": "умеренный",
    "интенсивно": "интенсивный",
    "интенсивно ": "интенсивный",
    "умеренно ": "умеренный",
    "слабо ": "слабый",
}


def _loads(s: str) -> Any:
    s = re.sub(r",\s*([\]\}])", r"\1", s.strip())
    try:
        return json.loads(s)
    except Exception:
        return ast.literal_eval(s)


def _norm(x: Any) -> str:
    s = str(x).strip()
    return _NORMALIZE.get(s, s)


def _terms(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, list):
        terms = obj
    elif isinstance(obj, dict):
        if len(obj) == 1 and isinstance(next(iter(obj.values())), list):
            terms = next(iter(obj.values()))
        elif isinstance(obj.get("terms"), list):
            terms = obj["terms"]
        else:
            lists = [v for v in obj.values() if isinstance(v, list)]
            if not lists:
                raise ValueError("Не удалось извлечь список термов из JSON.")
            terms = lists[0]
    else:
        raise ValueError("Неверный формат: ожидается dict или list.")
    if not isinstance(terms, list):
        raise ValueError("Список термов должен быть list.")
    for t in terms:
        if not isinstance(t, dict) or "id" not in t or "points" not in t:
            raise ValueError("Каждый терм должен иметь поля 'id' и 'points'.")
    return terms


def _pts(term: Dict[str, Any]) -> List[Point]:
    pts = term["points"]
    if not isinstance(pts, list) or len(pts) < 2:
        raise ValueError(f"Терм {term.get('id')} имеет некорректные points.")
    out: List[Point] = []
    for p in pts:
        if not isinstance(p, list) or len(p) != 2:
            raise ValueError(f"Некорректная точка {p} в терме {term.get('id')}.")
        out.append((float(p[0]), float(p[1])))
    out.sort(key=lambda x: x[0])
    return out


def _mu(pts: List[Point], x: float) -> float:
    if x <= pts[0][0]:
        return float(pts[0][1])
    if x >= pts[-1][0]:
        return float(pts[-1][1])
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 == x2:
            continue
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1)
            y = y1 + t * (y2 - y1)
            if y < 0.0:
                y = 0.0
            elif y > 1.0:
                y = 1.0
            return float(y)
    left = max([p for p in pts if p[0] <= x], key=lambda p: p[0])
    right = min([p for p in pts if p[0] >= x], key=lambda p: p[0])
    if left[0] == right[0]:
        return float(max(left[1], right[1]))
    t = (x - left[0]) / (right[0] - left[0])
    return float(left[1] + t * (right[1] - left[1]))


def _x_at_y(p1: Point, p2: Point, y: float) -> List[float]:
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 or y1 == y2:
        return []
    if not (min(y1, y2) <= y <= max(y1, y2)):
        return []
    t = (y - y1) / (y2 - y1)
    return [float(x1 + t * (x2 - x1))]


def main(
    temperature_mfs_json: str,
    control_mfs_json: str,
    rules_json: str,
    temperature_value: float,
) -> float:
    temp_terms = _terms(_loads(temperature_mfs_json))
    ctrl_terms = _terms(_loads(control_mfs_json))
    rules_obj = _loads(rules_json)

    if not isinstance(rules_obj, list):
        raise ValueError("rules_json должен быть списком правил.")
    rules: List[Tuple[str, str]] = []
    for r in rules_obj:
        if not isinstance(r, (list, tuple)) or len(r) != 2:
            raise ValueError(f"Некорректное правило: {r}. Ожидалось [temp_term, control_term].")
        rules.append((_norm(r[0]), _norm(r[1])))

    temp_map: Dict[str, List[Point]] = {str(t["id"]): _pts(t) for t in temp_terms}
    ctrl_map: Dict[str, List[Point]] = {str(t["id"]): _pts(t) for t in ctrl_terms}

    t = float(temperature_value)
    mu_temp: Dict[str, float] = {_norm(k): _mu(v, t) for k, v in temp_map.items()}

    rule_alphas: List[Tuple[float, List[Point]]] = []
    for temp_term, ctrl_term in rules:
        alpha = float(mu_temp.get(temp_term, 0.0))
        if ctrl_term not in ctrl_map:
            ctrl_term2 = _norm(ctrl_term)
            if ctrl_term2 in ctrl_map:
                ctrl_term = ctrl_term2
            else:
                raise ValueError(f"Неизвестный терм управления в правилах: {ctrl_term}")
        rule_alphas.append((alpha, ctrl_map[ctrl_term]))

    all_x: List[float] = [p[0] for pts in ctrl_map.values() for p in pts]
    if not all_x:
        raise ValueError("Пустые функции принадлежности управления.")
    s_min, s_max = min(all_x), max(all_x)

    candidates = set(all_x)
    candidates.add(s_min)
    candidates.add(s_max)
    for alpha, pts in rule_alphas:
        if alpha <= 0.0:
            continue
        for p1, p2 in zip(pts, pts[1:]):
            for xc in _x_at_y(p1, p2, alpha):
                if s_min <= xc <= s_max:
                    candidates.add(xc)

    cand_sorted = sorted(candidates)

    def mu_out(s: float) -> float:
        m = 0.0
        for alpha, pts in rule_alphas:
            if alpha <= 0.0:
                continue
            mv = _mu(pts, s)
            val = alpha if alpha < mv else mv
            if val > m:
                m = val
        return float(m)

    vals = [(s, mu_out(s)) for s in cand_sorted]
    max_val = max(v for _, v in vals) if vals else 0.0
    if max_val <= 1e-9:
        return float(s_min)
    for s, v in vals:
        if abs(v - max_val) <= 1e-8:
            return float(s)
    return float(s_min)

from typing import Dict, List, Tuple

def build_matrices(elements: List[Dict], n: int) -> Tuple[List[List[int]], List[List[int]]]:
    INF = 10**9
    dur = [[INF] * n for _ in range(n)]
    dist = [[INF] * n for _ in range(n)]

    for e in elements:
        i = e["originIndex"]
        j = e["destinationIndex"]
        raw = e.get("duration", "0s")
        if isinstance(raw, dict):
            sec = int(raw.get("seconds", 0))
        elif isinstance(raw, str) and raw.endswith("s"):
            sec = int(float(raw[:-1]))
        else:
            sec = 0
        dur[i][j] = sec
        dist[i][j] = int(e.get("distanceMeters", 0))

    for k in range(n):
        dur[k][k] = 0
        dist[k][k] = 0

    return dur, dist

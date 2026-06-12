from typing import List, Optional, Tuple
import folium

def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    coords = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coords.append((lat / 1e5, lng / 1e5))
    return coords

def save_map_html(
    points: List[Tuple[float, float, str]],
    polyline: Optional[str],
    out_path: str,
) -> str:
    lat0, lng0, _ = points[0]
    m = folium.Map(location=(lat0, lng0), zoom_start=13)

    for i, (lat, lng, label) in enumerate(points):
        folium.Marker((lat, lng), popup=f"{i}. {label}").add_to(m)

    if polyline:
        pts = decode_polyline(polyline)
        folium.PolyLine(pts, weight=5, opacity=0.8).add_to(m)

    m.save(out_path)
    return out_path

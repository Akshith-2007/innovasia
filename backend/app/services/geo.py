"""Approximate district-headquarters coordinates for distance estimates (ADR-027).

shortcut: hand-entered HQ coordinates (±5-10 km) and straight-line distance x 1.3 road factor;
replace with surveyed mandi locations or a routing service if accuracy matters. Admins can override km per mandi.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

ROAD_FACTOR = 1.3

# (state, district as named in AGMARKNET data) -> (lat, lon) of the district headquarters town
DISTRICT_HQ: dict[tuple[str, str], tuple[float, float]] = {
    # Telangana
    ("Telangana", "Adilabad"): (19.67, 78.53), ("Telangana", "Asifabad"): (19.36, 79.28),
    ("Telangana", "Bhadradri Kothagudem"): (17.55, 80.62), ("Telangana", "Bhupalapally"): (18.43, 79.86),
    ("Telangana", "Hanumakonda"): (18.01, 79.56), ("Telangana", "Hyderabad"): (17.39, 78.49),
    ("Telangana", "Jagtial"): (18.79, 78.91), ("Telangana", "Jangaon"): (17.72, 79.15),
    ("Telangana", "Jogulamba Gadwal"): (16.23, 77.80), ("Telangana", "Karimnagar"): (18.44, 79.13),
    ("Telangana", "Khammam"): (17.25, 80.15), ("Telangana", "Mahabubabad"): (17.60, 80.00),
    ("Telangana", "Mahbubnagar"): (16.74, 78.00), ("Telangana", "Mancherial"): (18.87, 79.44),
    ("Telangana", "Medak"): (18.05, 78.26), ("Telangana", "Medchal Malkajgiri"): (17.63, 78.48),
    ("Telangana", "Nagarkurnool"): (16.48, 78.31), ("Telangana", "Nalgonda"): (17.05, 79.27),
    ("Telangana", "Narayanpet"): (16.74, 77.50), ("Telangana", "Nirmal"): (19.10, 78.34),
    ("Telangana", "Nizamabad"): (18.67, 78.09), ("Telangana", "Peddapalli"): (18.61, 79.37),
    ("Telangana", "Rajanna Siricilla"): (18.39, 78.81), ("Telangana", "Ranga Reddy"): (17.24, 78.56),
    ("Telangana", "Sangareddy"): (17.62, 78.08), ("Telangana", "Siddipet"): (18.10, 78.85),
    ("Telangana", "Suryapet"): (17.14, 79.62), ("Telangana", "Vikarabad"): (17.34, 77.90),
    ("Telangana", "Wanaparthy"): (16.36, 78.06), ("Telangana", "Warangal"): (17.97, 79.59),
    ("Telangana", "Yadadri Bhuvanagiri"): (17.51, 78.89),
    # Andhra Pradesh
    ("Andhra Pradesh", "Alluri Sitharama Raju"): (18.08, 82.67), ("Andhra Pradesh", "Anakapally"): (17.69, 83.00),
    ("Andhra Pradesh", "Ananthapuramu"): (14.68, 77.60), ("Andhra Pradesh", "Annamayya"): (14.06, 78.75),
    ("Andhra Pradesh", "Bapatla"): (15.90, 80.47), ("Andhra Pradesh", "Chittor"): (13.22, 79.10),
    ("Andhra Pradesh", "Dr.B.R.A.Konaseema"): (16.58, 82.01), ("Andhra Pradesh", "East Godavari"): (17.00, 81.80),
    ("Andhra Pradesh", "Eluru"): (16.71, 81.10), ("Andhra Pradesh", "Guntur"): (16.31, 80.44),
    ("Andhra Pradesh", "Kakinada"): (16.99, 82.25), ("Andhra Pradesh", "Krishna"): (16.19, 81.14),
    ("Andhra Pradesh", "Kurnool"): (15.83, 78.04), ("Andhra Pradesh", "Markapuram"): (15.74, 79.27),
    ("Andhra Pradesh", "NTR"): (16.51, 80.65), ("Andhra Pradesh", "Nandyal"): (15.48, 78.48),
    ("Andhra Pradesh", "Palnadu"): (16.24, 80.05), ("Andhra Pradesh", "Parvathipuram Manyam"): (18.78, 83.43),
    ("Andhra Pradesh", "Polavaram"): (17.25, 81.64), ("Andhra Pradesh", "Prakasam"): (15.50, 80.05),
    ("Andhra Pradesh", "SPSR Nellore"): (14.44, 79.99), ("Andhra Pradesh", "Sri Sathya Sai"): (14.17, 77.81),
    ("Andhra Pradesh", "Srikakulam"): (18.30, 83.90), ("Andhra Pradesh", "Tirupathi"): (13.63, 79.42),
    ("Andhra Pradesh", "Vijayanagaram"): (18.11, 83.40), ("Andhra Pradesh", "Visakhapatnam"): (17.69, 83.22),
    ("Andhra Pradesh", "West Godavari"): (16.54, 81.52), ("Andhra Pradesh", "YSR Kadapa"): (14.47, 78.82),
    # Karnataka
    ("Karnataka", "Bagalkot"): (16.18, 75.70), ("Karnataka", "Belagavi"): (15.85, 74.50),
    ("Karnataka", "Bellary"): (15.14, 76.92), ("Karnataka", "Bengaluru"): (12.97, 77.59),
    ("Karnataka", "Bengaluru Rural"): (13.29, 77.54), ("Karnataka", "Bengaluru South"): (12.72, 77.28),
    ("Karnataka", "Bidar"): (17.91, 77.52), ("Karnataka", "Chamarajanagar"): (11.92, 76.94),
    ("Karnataka", "Chikkaballapur"): (13.43, 77.73), ("Karnataka", "Chikkamagaluru"): (13.32, 75.77),
    ("Karnataka", "Chitradurga"): (14.23, 76.40), ("Karnataka", "Dakshina Kannada"): (12.91, 74.86),
    ("Karnataka", "Davangere"): (14.46, 75.92), ("Karnataka", "Dharwad"): (15.46, 75.01),
    ("Karnataka", "Gadag"): (15.43, 75.63), ("Karnataka", "Hassan"): (13.00, 76.10),
    ("Karnataka", "Haveri"): (14.79, 75.40), ("Karnataka", "Kalaburagi"): (17.33, 76.83),
    ("Karnataka", "Kodagu"): (12.42, 75.74), ("Karnataka", "Kolar"): (13.14, 78.13),
    ("Karnataka", "Koppal"): (15.35, 76.15), ("Karnataka", "Mandya"): (12.52, 76.90),
    ("Karnataka", "Mysuru"): (12.30, 76.64), ("Karnataka", "Raichur"): (16.20, 77.36),
    ("Karnataka", "Shivamogga"): (13.93, 75.57), ("Karnataka", "Tumakuru"): (13.34, 77.10),
    ("Karnataka", "Udupi"): (13.34, 74.75), ("Karnataka", "Uttara Kannada"): (14.81, 74.13),
    ("Karnataka", "Vijayanagara"): (15.27, 76.39), ("Karnataka", "Vijayapura"): (16.83, 75.71),
    ("Karnataka", "Yadgir"): (16.77, 77.14),
}


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


def road_km(origin: tuple[str, str], dest: tuple[str, str]) -> float | None:
    """Approximate road km between two district HQs; None when either district is unknown."""
    a, b = DISTRICT_HQ.get(origin), DISTRICT_HQ.get(dest)
    if a is None or b is None:
        return None
    return round(haversine_km(a, b) * ROAD_FACTOR, 1)


def districts() -> list[dict[str, str]]:
    return [{"state": s, "district": d} for s, d in sorted(DISTRICT_HQ)]

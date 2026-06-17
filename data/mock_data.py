import random
from datetime import datetime, timedelta

STATIONS = ["北京站", "上海站", "广州站", "郑州站", "武汉站", "西安站", "成都站", "济南站"]
STATION_WEIGHTS = [0.15, 0.20, 0.12, 0.18, 0.15, 0.08, 0.07, 0.05]

CAR_TYPES = {
    "敞车(C62)": {"weight_empty": 21, "weight_loaded": 60, "category": "general", "special": False},
    "棚车(P62)": {"weight_empty": 24, "weight_loaded": 58, "category": "general", "special": False},
    "平车(N17)": {"weight_empty": 18, "weight_loaded": 60, "category": "general", "special": False},
    "罐车(G60)": {"weight_empty": 22, "weight_loaded": 52, "category": "tanker", "special": True},
    "冷藏车(B6)": {"weight_empty": 30, "weight_loaded": 45, "category": "reefer", "special": True},
    "家畜车(J6)": {"weight_empty": 26, "weight_loaded": 40, "category": "livestock", "special": True},
    "长大货物车(D22)": {"weight_empty": 45, "weight_loaded": 120, "category": "oversize", "special": True},
    "集装箱车(X6K)": {"weight_empty": 22, "weight_loaded": 50, "category": "container", "special": False},
}

ISOLATION_RULES = {
    "tanker": ["reefer", "livestock"],
    "reefer": ["tanker"],
    "livestock": ["tanker", "oversize"],
    "oversize": ["livestock"],
}


def generate_sample_data(n_cars: int = 35) -> list:
    cars = []
    car_type_keys = list(CAR_TYPES.keys())
    
    for i in range(n_cars):
        car_type = random.choice(car_type_keys)
        type_info = CAR_TYPES[car_type]
        is_loaded = random.choice([True, True, False])
        
        destination = random.choices(STATIONS, weights=STATION_WEIGHTS, k=1)[0]
        dest_idx = STATIONS.index(destination)
        
        cargo_weight = random.uniform(type_info["weight_empty"] * 0.5, 
                                      type_info["weight_loaded"] - type_info["weight_empty"]) if is_loaded else 0
        total_weight = type_info["weight_empty"] + cargo_weight
        
        car = {
            "id": f"CR{10000 + i}",
            "car_type": car_type,
            "category": type_info["category"],
            "special": type_info["special"],
            "is_loaded": is_loaded,
            "destination": destination,
            "dest_order": dest_idx,
            "weight_empty": type_info["weight_empty"],
            "cargo_weight": round(cargo_weight, 1),
            "total_weight": round(total_weight, 1),
            "length": random.choice([12, 13, 14, 15, 16]),
            "notes": ""
        }
        cars.append(car)
    
    return cars


def get_stations():
    return STATIONS


def get_car_types():
    return CAR_TYPES


def get_isolation_rules():
    return ISOLATION_RULES


def station_color(station: str) -> str:
    colors = [
        "#e74c3c", "#3498db", "#2ecc71", "#f39c12",
        "#9b59b6", "#1abc9c", "#e67e22", "#34495e"
    ]
    if station in STATIONS:
        return colors[STATIONS.index(station)]
    return "#95a5a6"

from data.mock_data import get_isolation_rules, STATIONS

ISOLATION_RULES = get_isolation_rules()


def generate_marshalling_plan(cars: list, strategy: str = "by_station", max_weight: int = 5000) -> dict:
    if not cars:
        return {"sequence": [], "total_weight": 0, "total_cars": 0, "strategy": strategy}

    cars_copy = [car.copy() for car in cars]

    if strategy == "by_station":
        sequence = _sort_by_station(cars_copy)
    elif strategy == "by_weight":
        sequence = _sort_by_weight(cars_copy)
    elif strategy == "by_car_type":
        sequence = _sort_by_car_type(cars_copy)
    else:
        sequence = _sort_by_station(cars_copy)

    total_weight = sum(car["total_weight"] for car in sequence)
    total_cars = len(sequence)

    return {
        "sequence": sequence,
        "total_weight": round(total_weight, 1),
        "total_cars": total_cars,
        "strategy": strategy,
        "overweight": total_weight > max_weight,
    }


def _sort_by_station(cars: list) -> list:
    station_cars = {}
    for car in cars:
        dest = car["destination"]
        if dest not in station_cars:
            station_cars[dest] = []
        station_cars[dest].append(car)

    for station in station_cars:
        station_cars[station].sort(key=lambda c: (c["special"], c["category"]))

    sequence = []
    for station in STATIONS:
        if station in station_cars:
            sequence.extend(station_cars[station])

    return sequence


def _sort_by_weight(cars: list) -> list:
    heavy = [c for c in cars if c["is_loaded"]]
    light = [c for c in cars if not c["is_loaded"]]

    heavy.sort(key=lambda c: (-c["total_weight"], c["dest_order"]))
    light.sort(key=lambda c: c["dest_order"])

    return heavy + light


def _sort_by_car_type(cars: list) -> list:
    categories = {}
    for car in cars:
        cat = car["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(car)

    priority = ["general", "container", "tanker", "reefer", "livestock", "oversize"]
    sequence = []
    for cat in priority:
        if cat in categories:
            categories[cat].sort(key=lambda c: c["dest_order"])
            sequence.extend(categories[cat])

    return sequence


def detect_conflicts(plan: dict, max_weight: int = 5000) -> list:
    conflicts = []
    sequence = plan.get("sequence", [])

    if not sequence:
        return conflicts

    total_weight = sum(car["total_weight"] for car in sequence)
    if total_weight > max_weight:
        conflicts.append({
            "type": "超重",
            "severity": "high",
            "description": f"列车总重 {total_weight:.1f} 吨，超过限重 {max_weight} 吨",
            "excess": round(total_weight - max_weight, 1),
            "position": None,
        })

    for i in range(len(sequence)):
        for j in range(i + 1, min(i + 4, len(sequence))):
            car_a = sequence[i]
            car_b = sequence[j]
            if _needs_isolation(car_a, car_b):
                distance = j - i
                if distance < 3:
                    conflicts.append({
                        "type": "车种隔离冲突",
                        "severity": "high" if distance < 2 else "medium",
                        "description": f"{car_a['car_type']}({car_a['id']}) 与 {car_b['car_type']}({car_b['id']}) 需要隔离，当前距离 {distance} 辆",
                        "car_a_id": car_a["id"],
                        "car_b_id": car_b["id"],
                        "position_a": i + 1,
                        "position_b": j + 1,
                    })

    station_groups = {}
    for idx, car in enumerate(sequence):
        dest = car["destination"]
        if dest not in station_groups:
            station_groups[dest] = []
        station_groups[dest].append((idx, car))

    station_order = {station: i for i, station in enumerate(STATIONS)}
    prev_station_order = -1
    for station in STATIONS:
        if station in station_groups:
            current_order = station_order[station]
            if current_order < prev_station_order:
                first_car = station_groups[station][0][1]
                conflicts.append({
                    "type": "到站顺序冲突",
                    "severity": "low",
                    "description": f"到站 {station} 的车辆顺位不符合站序要求",
                    "station": station,
                    "position": station_groups[station][0][0] + 1,
                })
            prev_station_order = current_order

    special_cars = [car for car in sequence if car["special"]]
    for i, car in enumerate(special_cars[:-1]):
        next_special = special_cars[i + 1]
        idx_a = sequence.index(car)
        idx_b = sequence.index(next_special)
        if idx_b - idx_a < 2 and car["category"] != next_special["category"]:
            conflicts.append({
                "type": "特殊车辆连挂",
                "severity": "medium",
                "description": f"特殊车辆 {car['id']} 与 {next_special['id']} 距离过近",
                "car_a_id": car["id"],
                "car_b_id": next_special["id"],
                "position_a": idx_a + 1,
                "position_b": idx_b + 1,
            })

    return conflicts


def _needs_isolation(car_a: dict, car_b: dict) -> bool:
    cat_a = car_a["category"]
    cat_b = car_b["category"]

    if cat_a in ISOLATION_RULES and cat_b in ISOLATION_RULES[cat_a]:
        return True
    if cat_b in ISOLATION_RULES and cat_a in ISOLATION_RULES[cat_b]:
        return True
    return False


def generate_shunting_plan(plan: dict) -> dict:
    sequence = plan.get("sequence", [])
    if not sequence:
        return {"operations": [], "total_time": 0, "total_cars": 0}

    operations = []
    consecutive_groups = []
    if sequence:
        current_station = sequence[0]["destination"]
        current_group = [(1, sequence[0])]
        for idx in range(1, len(sequence)):
            car = sequence[idx]
            if car["destination"] == current_station:
                current_group.append((idx + 1, car))
            else:
                consecutive_groups.append((current_station, current_group))
                current_station = car["destination"]
                current_group = [(idx + 1, car)]
        consecutive_groups.append((current_station, current_group))

    track_num = 1
    station_operations = {}
    for station, cars_in_group in consecutive_groups:
        if station not in station_operations:
            station_operations[station] = []
        n_cars = len(cars_in_group)
        op = {
            "step": len(operations) + 1,
            "operation": f"摘解-{station}",
            "track": f"{track_num}道",
            "cars": n_cars,
            "car_ids": [car[1]["id"] for car in cars_in_group],
            "position_start": cars_in_group[0][0],
            "position_end": cars_in_group[-1][0],
            "duration": 3 + n_cars * 0.5,
            "type": "decouple",
        }
        operations.append(op)
        station_operations[station].append(op)
        track_num += 1

    total_time = sum(op["duration"] for op in operations) + len(operations) * 2

    return {
        "operations": operations,
        "total_time": round(total_time, 1),
        "total_cars": len(sequence),
        "n_stations": len(station_operations),
        "setup_time": round(len(operations) * 2, 1),
        "operation_time": round(sum(op["duration"] for op in operations), 1),
    }


def move_car_to_position(plan: dict, car_id: str, target_pos: int) -> dict:
    sequence = plan.get("sequence", [])
    if not sequence:
        return {"success": False, "message": "当前编组为空，无法调位", "new_plan": None}

    n_cars = len(sequence)
    current_pos = None
    for i, car in enumerate(sequence):
        if car["id"] == car_id:
            current_pos = i + 1
            break

    if current_pos is None:
        return {"success": False, "message": f"未找到车厢编号 {car_id}", "new_plan": None}

    if target_pos < 1 or target_pos > n_cars:
        return {
            "success": False,
            "message": f"目标顺位 {target_pos} 越界，有效范围为 1 到 {n_cars}",
            "new_plan": None
        }

    if target_pos == current_pos:
        return {
            "success": False,
            "message": f"目标顺位 {target_pos} 与当前顺位相同，无需调位",
            "new_plan": None
        }

    new_sequence = [car.copy() for car in sequence]
    car = new_sequence.pop(current_pos - 1)
    new_sequence.insert(target_pos - 1, car)

    new_plan = {
        "sequence": new_sequence,
        "total_weight": plan["total_weight"],
        "total_cars": plan["total_cars"],
        "strategy": plan["strategy"],
        "overweight": plan.get("overweight", False),
    }

    return {
        "success": True,
        "message": f"车厢 {car_id} 已从第 {current_pos} 位移动到第 {target_pos} 位",
        "new_plan": new_plan,
        "old_position": current_pos,
        "new_position": target_pos,
    }


def compare_plans(plan_a: dict, plan_b: dict) -> dict:
    if not plan_a or not plan_b:
        return None

    seq_a = plan_a.get("sequence", [])
    seq_b = plan_b.get("sequence", [])

    weight_diff = plan_a.get("total_weight", 0) - plan_b.get("total_weight", 0)

    station_groups_a = {}
    station_groups_b = {}
    for car in seq_a:
        station_groups_a.setdefault(car["destination"], 0)
        station_groups_a[car["destination"]] += 1
    for car in seq_b:
        station_groups_b.setdefault(car["destination"], 0)
        station_groups_b[car["destination"]] += 1

    car_id_to_pos_a = {car["id"]: i + 1 for i, car in enumerate(seq_a)}
    car_id_to_pos_b = {car["id"]: i + 1 for i, car in enumerate(seq_b)}

    position_changes = []
    for car_id in car_id_to_pos_a:
        if car_id in car_id_to_pos_b:
            pos_a = car_id_to_pos_a[car_id]
            pos_b = car_id_to_pos_b[car_id]
            if pos_a != pos_b:
                position_changes.append({
                    "car_id": car_id,
                    "position_a": pos_a,
                    "position_b": pos_b,
                    "change": pos_b - pos_a,
                })

    conflicts_a = detect_conflicts(plan_a)
    conflicts_b = detect_conflicts(plan_b)

    return {
        "total_weight_diff": round(weight_diff, 1),
        "total_cars_a": plan_a.get("total_cars", 0),
        "total_cars_b": plan_b.get("total_cars", 0),
        "strategy_a": plan_a.get("strategy", ""),
        "strategy_b": plan_b.get("strategy", ""),
        "position_changes": position_changes,
        "n_changes": len(position_changes),
        "conflicts_a": len(conflicts_a),
        "conflicts_b": len(conflicts_b),
        "conflict_diff": len(conflicts_a) - len(conflicts_b),
    }

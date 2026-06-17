import streamlit as st
from data.mock_data import station_color, STATIONS, CAR_TYPES
from core.marshalling import move_car_to_position, detect_conflicts, generate_shunting_plan

def render():
    st.header("📊 编组视图")
    st.caption("可视化展示编组顺位，按颜色区分到站")

    if not st.session_state.marshalling_plan:
        st.info("请先在导入页面生成编组方案")
        return

    plan = st.session_state.marshalling_plan
    sequence = plan["sequence"]
    n_cars = plan["total_cars"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("车次", st.session_state.train_info["train_number"])
    col2.metric("编组辆数", plan["total_cars"])
    col3.metric("总重量(吨)", f"{plan['total_weight']:.1f}")
    col4.metric("策略", plan["strategy"])

    st.markdown("---")

    st.subheader("到站图例")
    legend_cols = st.columns(len(STATIONS))
    for i, station in enumerate(STATIONS):
        color = station_color(station)
        legend_cols[i].markdown(
            f'<div style="display:flex;align-items:center;gap:0.5rem;">'
            f'<div style="width:16px;height:16px;background:{color};border-radius:3px;"></div>'
            f'<span style="font-size:0.8rem;">{station}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    st.subheader("编组顺位条")
    _render_marshalling_bar(sequence)

    st.markdown("---")

    st.subheader("按站统计")
    _render_station_stats(sequence)

    st.markdown("---")

    st.subheader("手动调位")
    _render_position_adjustment(sequence, n_cars, plan)

    st.markdown("---")

    st.subheader("详细列表")
    _render_car_table(sequence)


def _render_marshalling_bar(cars: list):
    if not cars:
        return

    bar_html = '<div style="display:flex;flex-wrap:wrap;gap:2px;padding:1rem;background:#f8f9fa;border-radius:0.5rem;border:1px solid #e9ecef;">'

    for i, car in enumerate(cars):
        color = station_color(car["destination"])
        loaded_class = "loaded" if car["is_loaded"] else "empty"
        special_border = "2px dashed #e74c3c" if car["special"] else "none"

        bar_html += f'''
        <div title="顺位:{i+1} | {car['id']} | {car['car_type']} | {car['destination']} | {'重车' if car['is_loaded'] else '空车'} | {car['total_weight']}吨"
             style="flex:0 0 auto;width:36px;height:60px;background:{color};
                    border-radius:3px;display:flex;align-items:center;justify-content:center;
                    color:white;font-size:10px;font-weight:bold;cursor:pointer;
                    box-shadow:0 1px 3px rgba(0,0,0,0.1);
                    border-bottom:4px solid {'#c0392b' if car['is_loaded'] else '#ecf0f1'};
                    border-top: {special_border};">
            {i+1}
        </div>
        '''

    bar_html += '</div>'

    st.markdown(bar_html, unsafe_allow_html=True)

    st.caption("⬇️ 底部红边表示重车，浅灰边表示空车；顶部虚线表示特殊车辆")


def _render_station_stats(cars: list):
    station_data = {}
    for car in cars:
        dest = car["destination"]
        if dest not in station_data:
            station_data[dest] = {"count": 0, "weight": 0, "loaded": 0, "empty": 0}
        station_data[dest]["count"] += 1
        station_data[dest]["weight"] += car["total_weight"]
        if car["is_loaded"]:
            station_data[dest]["loaded"] += 1
        else:
            station_data[dest]["empty"] += 1

    cols = st.columns(len(station_data))
    for i, (station, data) in enumerate(station_data.items()):
        color = station_color(station)
        with cols[i]:
            st.markdown(f'''
            <div style="padding:0.8rem;border-left:4px solid {color};background:#fff;border-radius:0.3rem;">
                <div style="font-weight:bold;color:#333;">{station}</div>
                <div style="font-size:0.85rem;color:#666;">
                    {data['count']} 辆 · {data['weight']:.0f}吨
                </div>
                <div style="font-size:0.75rem;color:#999;">
                    重 {data['loaded']} / 空 {data['empty']}
                </div>
            </div>
            ''', unsafe_allow_html=True)


def _render_car_table(cars: list):
    import pandas as pd

    data = []
    for i, car in enumerate(cars):
        data.append({
            "顺位": i + 1,
            "车厢编号": car["id"],
            "车型": car["car_type"],
            "到站": car["destination"],
            "状态": "重车" if car["is_loaded"] else "空车",
            "总重(吨)": car["total_weight"],
            "特殊": "是" if car["special"] else "否",
        })

    df = pd.DataFrame(data)

    def highlight_special(row):
        if row["特殊"] == "是":
            return ["background-color: #fff3cd"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_special, axis=1)
    st.dataframe(styled, use_container_width=True, height=400)


def _render_position_adjustment(sequence: list, n_cars: int, plan: dict):
    col_select, col_pos, col_btn = st.columns([3, 2, 2])

    with col_select:
        car_options = [f"第{i+1}位 - {car['id']} ({car['car_type']} - {car['destination']})"
                       for i, car in enumerate(sequence)]
        selected_idx = st.selectbox(
            "选择要调位的车厢",
            range(len(car_options)),
            format_func=lambda x: car_options[x],
            key="pos_adjust_car"
        )

    with col_pos:
        target_pos = st.number_input(
            f"目标顺位 (1 - {n_cars})",
            min_value=1,
            max_value=n_cars,
            value=1,
            step=1,
            key="pos_adjust_target"
        )

    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎯 应用调位", type="primary", use_container_width=True, key="pos_adjust_btn"):
            selected_car = sequence[selected_idx]
            car_id = selected_car["id"]

            result = move_car_to_position(plan, car_id, target_pos)

            if result["success"]:
                new_plan = result["new_plan"]
                max_weight = st.session_state.train_info["max_weight"]

                new_conflicts = detect_conflicts(new_plan, max_weight)
                new_shunting = generate_shunting_plan(new_plan)

                st.session_state.marshalling_plan = new_plan
                st.session_state.conflicts = new_conflicts
                st.session_state.shunting_plan = new_shunting

                st.success(result["message"])
                st.info(f"已自动重算：冲突数 {len(new_conflicts)} 个，调车耗时 {new_shunting['total_time']:.1f} 分钟")
                st.rerun()
            else:
                st.error(result["message"])

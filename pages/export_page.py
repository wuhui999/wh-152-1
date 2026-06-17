import streamlit as st
import pandas as pd
import io
from data.mock_data import station_color, STATIONS
from core.marshalling import compare_plans, detect_conflicts


def render():
    st.header("📤 方案导出")
    st.caption("两套方案对比和编组方案 CSV 导出")

    if not st.session_state.marshalling_plan:
        st.info("请先在导入页面生成编组方案")
        return

    plan_a = st.session_state.marshalling_plan
    plan_b = st.session_state.alternative_plan

    tab1, tab2 = st.tabs(["方案对比", "导出方案"])

    with tab1:
        _render_comparison(plan_a, plan_b)

    with tab2:
        _render_export(plan_a)


def _render_comparison(plan_a, plan_b):
    if not plan_b:
        st.info("未生成对比方案，请在导入页面选择对比策略后重新生成")
        return

    comparison = compare_plans(plan_a, plan_b)
    if not comparison:
        return

    st.subheader("对比概览")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("方案 A", comparison["strategy_a"], "主方案")
    col2.metric("方案 B", comparison["strategy_b"], "对比方案")
    col3.metric("位置变化数", comparison["n_changes"])
    col4.metric("冲突数差异", comparison["conflict_diff"],
                delta=f"A比B{'少' if comparison['conflict_diff'] <= 0 else '多'}")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 方案 A")
        st.write(f"**策略**: {plan_a.get('strategy', '')}")
        st.write(f"**车辆数**: {plan_a.get('total_cars', 0)} 辆")
        st.write(f"**总重量**: {plan_a.get('total_weight', 0):.1f} 吨")
        conflicts_a = detect_conflicts(plan_a)
        st.write(f"**冲突数**: {len(conflicts_a)} 个")
        _render_mini_bar(plan_a.get("sequence", []))

    with col_b:
        st.markdown("### 方案 B")
        st.write(f"**策略**: {plan_b.get('strategy', '')}")
        st.write(f"**车辆数**: {plan_b.get('total_cars', 0)} 辆")
        st.write(f"**总重量**: {plan_b.get('total_weight', 0):.1f} 吨")
        conflicts_b = detect_conflicts(plan_b)
        st.write(f"**冲突数**: {len(conflicts_b)} 个")
        _render_mini_bar(plan_b.get("sequence", []))

    st.markdown("---")

    st.subheader("位置变化详情")
    if comparison["position_changes"]:
        df_changes = pd.DataFrame(comparison["position_changes"])
        df_changes.columns = ["车厢编号", "方案A位置", "方案B位置", "位置变化"]
        df_changes = df_changes.sort_values("位置变化", key=lambda x: abs(x), ascending=False)
        st.dataframe(df_changes, use_container_width=True)
    else:
        st.success("两套方案车辆位置完全一致")

    st.markdown("---")

    st.subheader("按站分布对比")
    _render_station_comparison(plan_a, plan_b)


def _render_mini_bar(cars):
    if not cars:
        return

    bar_html = '<div style="display:flex;flex-wrap:wrap;gap:1px;padding:0.5rem;background:#f8f9fa;border-radius:0.3rem;">'
    for i, car in enumerate(cars[:50]):
        color = station_color(car["destination"])
        bar_html += f'''
        <div title="{i+1}. {car['id']} - {car['destination']}"
             style="width:12px;height:24px;background:{color};border-radius:2px;"></div>
        '''
    if len(cars) > 50:
        bar_html += f'<span style="font-size:0.7rem;color:#999;margin-left:4px;">+{len(cars)-50}</span>'
    bar_html += '</div>'
    st.markdown(bar_html, unsafe_allow_html=True)


def _render_station_comparison(plan_a, plan_b):
    seq_a = plan_a.get("sequence", [])
    seq_b = plan_b.get("sequence", [])

    station_a = {}
    station_b = {}

    for car in seq_a:
        station_a[car["destination"]] = station_a.get(car["destination"], 0) + 1
    for car in seq_b:
        station_b[car["destination"]] = station_b.get(car["destination"], 0) + 1

    data = []
    for station in STATIONS:
        count_a = station_a.get(station, 0)
        count_b = station_b.get(station, 0)
        if count_a > 0 or count_b > 0:
            data.append({
                "到站": station,
                "方案A(辆)": count_a,
                "方案B(辆)": count_b,
                "差异": count_b - count_a,
            })

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("无数据")


def _render_export(plan):
    st.subheader("导出编组方案")

    col_fmt, col_btn = st.columns([2, 1])

    with col_fmt:
        export_format = st.selectbox(
            "导出格式",
            ["CSV (编组顺位)", "CSV (车厢详细信息)", "CSV (调车作业方案)"],
            index=0
        )

    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)

        if "编组顺位" in export_format:
            csv_data = _generate_sequence_csv(plan)
        elif "车厢详细" in export_format:
            csv_data = _generate_detail_csv(plan)
        else:
            csv_data = _generate_shunting_csv()

        st.download_button(
            label="⬇️ 下载 CSV",
            data=csv_data,
            file_name=f"编组方案_{st.session_state.train_info['train_number']}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("预览")

    if "编组顺位" in export_format:
        _preview_sequence(plan)
    elif "车厢详细" in export_format:
        _preview_detail(plan)
    else:
        _preview_shunting()

    st.markdown("---")
    st.subheader("方案摘要")
    _render_summary(plan)


def _generate_sequence_csv(plan) -> str:
    sequence = plan.get("sequence", [])
    output = io.StringIO()
    output.write("顺位,车厢编号,车型,到站,状态,总重(吨)\n")

    for i, car in enumerate(sequence):
        output.write(f"{i+1},{car['id']},{car['car_type']},{car['destination']},"
                     f"{'重车' if car['is_loaded'] else '空车'},{car['total_weight']}\n")

    return output.getvalue().encode("utf-8-sig")


def _generate_detail_csv(plan) -> str:
    sequence = plan.get("sequence", [])
    output = io.StringIO()
    output.write("顺位,车厢编号,车型,类别,到站,重/空,自重(吨),载重(吨),总重(吨),特殊车辆\n")

    for i, car in enumerate(sequence):
        output.write(f"{i+1},{car['id']},{car['car_type']},{car['category']},{car['destination']},"
                     f"{'重车' if car['is_loaded'] else '空车'},{car['weight_empty']},"
                     f"{car['cargo_weight']},{car['total_weight']},{'是' if car['special'] else '否'}\n")

    return output.getvalue().encode("utf-8-sig")


def _generate_shunting_csv() -> str:
    shunting = st.session_state.shunting_plan
    if not shunting:
        return "".encode("utf-8-sig")

    output = io.StringIO()
    output.write("步骤,作业内容,占用线路,车辆数,顺位起始,顺位结束,预计耗时(分)\n")

    for op in shunting["operations"]:
        output.write(f"{op['step']},{op['operation']},{op['track']},{op['cars']},"
                     f"{op['position_start']},{op['position_end']},{op['duration']:.1f}\n")

    output.write(f"\n总耗时,{shunting['total_time']:.1f}分钟\n")
    output.write(f"作业步数,{len(shunting['operations'])}\n")
    output.write(f"总车辆数,{shunting['total_cars']}\n")

    return output.getvalue().encode("utf-8-sig")


def _preview_sequence(plan):
    sequence = plan.get("sequence", [])
    data = []
    for i, car in enumerate(sequence):
        data.append({
            "顺位": i + 1,
            "车厢编号": car["id"],
            "车型": car["car_type"],
            "到站": car["destination"],
            "状态": "重车" if car["is_loaded"] else "空车",
            "总重(吨)": car["total_weight"],
        })
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, height=300)


def _preview_detail(plan):
    sequence = plan.get("sequence", [])
    data = []
    for i, car in enumerate(sequence):
        data.append({
            "顺位": i + 1,
            "车厢编号": car["id"],
            "车型": car["car_type"],
            "类别": car["category"],
            "到站": car["destination"],
            "重/空": "重车" if car["is_loaded"] else "空车",
            "自重(吨)": car["weight_empty"],
            "载重(吨)": car["cargo_weight"],
            "总重(吨)": car["total_weight"],
            "特殊车辆": "是" if car["special"] else "否",
        })
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, height=300)


def _preview_shunting():
    shunting = st.session_state.shunting_plan
    if not shunting:
        st.info("无调车方案")
        return

    data = []
    for op in shunting["operations"]:
        data.append({
            "步骤": op["step"],
            "作业内容": op["operation"],
            "占用线路": op["track"],
            "车辆数": op["cars"],
            "顺位范围": f"{op['position_start']}-{op['position_end']}",
            "预计耗时(分)": op["duration"],
        })
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, height=300)


def _render_summary(plan):
    sequence = plan.get("sequence", [])
    if not sequence:
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"**车次**: {st.session_state.train_info['train_number']}")
        st.info(f"**编组辆数**: {plan.get('total_cars', 0)} 辆")
        st.info(f"**总重量**: {plan.get('total_weight', 0):.1f} 吨")

    with col2:
        loaded = sum(1 for c in sequence if c["is_loaded"])
        empty = len(sequence) - loaded
        st.info(f"**重车**: {loaded} 辆")
        st.info(f"**空车**: {empty} 辆")
        special = sum(1 for c in sequence if c["special"])
        st.info(f"**特殊车辆**: {special} 辆")

    with col3:
        stations = set(c["destination"] for c in sequence)
        st.info(f"**途经站数**: {len(stations)} 站")
        st.info(f"**冲突数**: {len(st.session_state.conflicts)} 个")
        if st.session_state.shunting_plan:
            st.info(f"**调车耗时**: {st.session_state.shunting_plan['total_time']:.1f} 分钟")

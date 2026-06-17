import streamlit as st
import pandas as pd
from data.mock_data import generate_sample_data, get_stations, get_car_types
from core.marshalling import generate_marshalling_plan, detect_conflicts, generate_shunting_plan

STATIONS = get_stations()
CAR_TYPES = get_car_types()


def render():
    st.header("📥 导入数据")
    st.caption("配置车次信息和车厢列表，生成编组方案")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("车次信息")
        train_number = st.text_input("车次编号", value=st.session_state.train_info["train_number"])
        max_weight = st.number_input("列车限重(吨)", min_value=1000, max_value=20000, 
                                     value=st.session_state.train_info["max_weight"], step=500)
        max_cars = st.number_input("最大辆数", min_value=10, max_value=100, 
                                   value=st.session_state.train_info["max_cars"], step=5)

        st.markdown("---")
        st.subheader("数据导入")
        if st.button("🔄 生成示例数据", use_container_width=True):
            st.session_state.cars = generate_sample_data(n_cars=35)
            st.success("已生成35辆示例车厢数据")
            st.rerun()

        uploaded_file = st.file_uploader("上传 CSV 文件", type=["csv"])
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.session_state.cars = _df_to_cars(df)
                st.success(f"成功导入 {len(st.session_state.cars)} 条数据")
            except Exception as e:
                st.error(f"导入失败: {e}")

    with col2:
        st.subheader("车厢列表")
        if st.session_state.cars:
            df = _cars_to_df(st.session_state.cars)
            st.dataframe(df, use_container_width=True, height=400)

            col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
            col_stats1.metric("总辆数", len(st.session_state.cars))
            total_weight = sum(c["total_weight"] for c in st.session_state.cars)
            col_stats2.metric("总重量(吨)", f"{total_weight:.1f}")
            loaded = sum(1 for c in st.session_state.cars if c["is_loaded"])
            col_stats3.metric("重车", loaded)
            col_stats4.metric("空车", len(st.session_state.cars) - loaded)
        else:
            st.info("暂无数据，请生成示例数据或上传CSV文件")

    st.markdown("---")
    st.subheader("生成编组方案")

    col_strat1, col_strat2, col_btn = st.columns([2, 2, 1])
    with col_strat1:
        strategy = st.selectbox(
            "主方案策略",
            ["by_station", "by_weight", "by_car_type"],
            format_func=lambda x: {
                "by_station": "按到站排序（推荐）",
                "by_weight": "按重量排序",
                "by_car_type": "按车型分类"
            }.get(x, x),
            index=0
        )
    with col_strat2:
        alt_strategy = st.selectbox(
            "对比方案策略",
            ["by_weight", "by_station", "by_car_type"],
            format_func=lambda x: {
                "by_station": "按到站排序",
                "by_weight": "按重量排序",
                "by_car_type": "按车型分类"
            }.get(x, x),
            index=0
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 生成方案", type="primary", use_container_width=True):
            if st.session_state.cars:
                plan = generate_marshalling_plan(st.session_state.cars, strategy, max_weight)
                conflicts = detect_conflicts(plan, max_weight)
                shunting = generate_shunting_plan(plan)

                alt_plan = generate_marshalling_plan(st.session_state.cars, alt_strategy, max_weight)

                st.session_state.train_info = {
                    "train_number": train_number,
                    "max_weight": max_weight,
                    "max_cars": max_cars,
                }
                st.session_state.marshalling_plan = plan
                st.session_state.conflicts = conflicts
                st.session_state.shunting_plan = shunting
                st.session_state.alternative_plan = alt_plan

                st.success("编组方案已生成！请切换到其他页面查看详情")
            else:
                st.error("请先导入车厢数据")

    if st.session_state.marshalling_plan:
        st.markdown("---")
        st.subheader("方案概览")
        plan = st.session_state.marshalling_plan
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("编组辆数", plan["total_cars"])
        col_b.metric("总重量(吨)", f"{plan['total_weight']:.1f}")
        col_c.metric("冲突数", len(st.session_state.conflicts))
        col_d.metric("调车耗时(分)", f"{st.session_state.shunting_plan['total_time']:.1f}")


def _cars_to_df(cars: list) -> pd.DataFrame:
    data = []
    for car in cars:
        data.append({
            "车厢编号": car["id"],
            "车型": car["car_type"],
            "类别": car["category"],
            "重/空": "重车" if car["is_loaded"] else "空车",
            "到站": car["destination"],
            "自重(吨)": car["weight_empty"],
            "载重(吨)": car["cargo_weight"],
            "总重(吨)": car["total_weight"],
            "特殊车辆": "是" if car["special"] else "否",
        })
    return pd.DataFrame(data)


def _df_to_cars(df: pd.DataFrame) -> list:
    cars = []
    for _, row in df.iterrows():
        car = {
            "id": str(row.get("车厢编号", row.get("id", ""))),
            "car_type": str(row.get("车型", row.get("car_type", "敞车(C62)"))),
            "category": str(row.get("类别", row.get("category", "general"))),
            "is_loaded": str(row.get("重/空", row.get("is_loaded", "重车"))) == "重车",
            "destination": str(row.get("到站", row.get("destination", "北京站"))),
            "weight_empty": float(row.get("自重(吨)", row.get("weight_empty", 20))),
            "cargo_weight": float(row.get("载重(吨)", row.get("cargo_weight", 30))),
            "total_weight": float(row.get("总重(吨)", row.get("total_weight", 50))),
            "special": str(row.get("特殊车辆", row.get("special", "否"))) == "是",
            "length": 14,
            "notes": "",
        }
        car["dest_order"] = STATIONS.index(car["destination"]) if car["destination"] in STATIONS else 0
        cars.append(car)
    return cars

import streamlit as st
import pandas as pd
from data.mock_data import station_color


def render():
    st.header("🔧 调车作业")
    st.caption("调车作业顺序和预计耗时估算")

    if not st.session_state.shunting_plan:
        st.info("请先在导入页面生成编组方案")
        return

    shunting = st.session_state.shunting_plan

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("作业步骤", len(shunting["operations"]))
    col2.metric("作业总耗时", f"{shunting['total_time']:.1f} 分钟")
    col3.metric("摘解站数", shunting["n_stations"])
    col4.metric("作业车辆", shunting["total_cars"])

    st.markdown("---")

    st.subheader("时间分解")
    _render_time_breakdown(shunting)

    st.markdown("---")

    st.subheader("作业顺序")
    _render_operations_list(shunting)

    st.markdown("---")

    st.subheader("调车线路占用图")
    _render_track_visualization(shunting)

    st.markdown("---")

    st.subheader("作业甘特图")
    _render_gantt_chart(shunting)


def _render_time_breakdown(shunting):
    setup_time = shunting.get("setup_time", 0)
    operation_time = shunting.get("operation_time", 0)
    total = shunting["total_time"]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("准备时间", f"{setup_time:.1f} 分钟")
    with col_b:
        st.metric("作业时间", f"{operation_time:.1f} 分钟")
    with col_c:
        st.metric("总耗时", f"{total:.1f} 分钟")

    setup_pct = setup_time / total * 100 if total > 0 else 0
    op_pct = operation_time / total * 100 if total > 0 else 0

    st.markdown(f'''
    <div style="display:flex;height:24px;border-radius:0.5rem;overflow:hidden;">
        <div style="width:{setup_pct}%;background:#3498db;display:flex;align-items:center;
                    justify-content:center;color:white;font-size:0.75rem;">
            准备 {setup_pct:.0f}%
        </div>
        <div style="width:{op_pct}%;background:#2ecc71;display:flex;align-items:center;
                    justify-content:center;color:white;font-size:0.75rem;">
            作业 {op_pct:.0f}%
        </div>
    </div>
    ''', unsafe_allow_html=True)


def _render_operations_list(shunting):
    operations = shunting["operations"]

    data = []
    for op in operations:
        data.append({
            "步骤": op["step"],
            "作业内容": op["operation"],
            "占用线路": op["track"],
            "车辆数": op["cars"],
            "顺位范围": f"{op['position_start']}-{op['position_end']}",
            "预计耗时(分)": f"{op['duration']:.1f}",
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)


def _render_track_visualization(shunting):
    operations = shunting["operations"]

    track_html = '<div style="display:flex;flex-direction:column;gap:0.5rem;">'

    for op in operations:
        station_name = op["operation"].replace("摘解-", "")
        color = station_color(station_name)

        track_html += f'''
        <div style="display:flex;align-items:center;gap:1rem;">
            <div style="width:60px;font-weight:bold;color:#666;font-size:0.9rem;">
                {op["track"]}
            </div>
            <div style="flex:1;background:#ecf0f1;border-radius:0.3rem;padding:0.5rem;
                        display:flex;gap:2px;">
                {_generate_car_blocks(op["cars"], color)}
            </div>
            <div style="width:80px;text-align:right;font-size:0.85rem;color:#666;">
                {op["cars"]} 辆
            </div>
        </div>
        '''

    track_html += '</div>'
    st.markdown(track_html, unsafe_allow_html=True)


def _generate_car_blocks(count, color):
    blocks = ""
    for i in range(min(count, 20)):
        blocks += f'<div style="width:14px;height:20px;background:{color};border-radius:2px;"></div>'
    if count > 20:
        blocks += f'<div style="display:flex;align-items:center;font-size:0.7rem;color:#666;margin-left:4px;">+{count-20}</div>'
    return blocks


def _render_gantt_chart(shunting):
    operations = shunting["operations"]
    if not operations:
        return

    total_time = shunting["total_time"]
    setup_per_step = shunting.get("setup_time", 0) / max(len(operations), 1)

    current_time = 0

    gantt_html = '<div style="position:relative;height:400px;">'

    for i, op in enumerate(operations):
        start = current_time + setup_per_step
        duration = op["duration"]
        station_name = op["operation"].replace("摘解-", "")
        color = station_color(station_name)

        left_pct = start / total_time * 100
        width_pct = duration / total_time * 100

        gantt_html += f'''
        <div style="position:absolute;top:{i * 50 + 20}px;left:0;right:0;height:40px;
                    border-bottom:1px solid #eee;">
            <div style="position:absolute;left:0;top:10px;font-size:0.8rem;color:#666;width:80px;">
                步骤{op["step"]}
            </div>
            <div style="position:absolute;left:80px;right:0;top:5px;bottom:5px;">
                <div style="position:absolute;left:{left_pct}%;width:{width_pct}%;
                            height:100%;background:{color};border-radius:4px;
                            display:flex;align-items:center;padding:0 8px;color:white;
                            font-size:0.8rem;white-space:nowrap;overflow:hidden;">
                    {station_name} ({op["cars"]}辆)
                </div>
                <div style="position:absolute;left:{left_pct + width_pct/2}%;top:100%;
                            font-size:0.7rem;color:#999;transform:translateX(-50%);">
                    {duration:.1f}分
                </div>
            </div>
        </div>
        '''

        current_time = start + duration

    gantt_html += '''
    <div style="position:absolute;bottom:0;left:80px;right:0;height:20px;
                border-top:2px solid #333;display:flex;justify-content:space-between;
                font-size:0.75rem;color:#666;">
        <span>0</span>
        <span>1/4</span>
        <span>1/2</span>
        <span>3/4</span>
        <span>''' + f'{total_time:.0f}分' + '''</span>
    </div>
    '''

    gantt_html += '</div>'
    st.markdown(gantt_html, unsafe_allow_html=True)

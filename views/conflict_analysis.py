import streamlit as st
from data.mock_data import station_color, STATIONS
from core.marshalling import detect_conflicts


def render():
    st.header("⚠️ 冲突分析")
    st.caption("检测超重、到站冲突、特殊车隔离等编组冲突")

    if not st.session_state.marshalling_plan:
        st.info("请先在导入页面生成编组方案")
        return

    plan = st.session_state.marshalling_plan
    conflicts = st.session_state.conflicts

    high_conflicts = [c for c in conflicts if c["severity"] == "high"]
    medium_conflicts = [c for c in conflicts if c["severity"] == "medium"]
    low_conflicts = [c for c in conflicts if c["severity"] == "low"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("冲突总数", len(conflicts))
    col2.metric("🔴 高危", len(high_conflicts))
    col3.metric("🟡 中危", len(medium_conflicts))
    col4.metric("🟢 低危", len(low_conflicts))

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["超重检测", "车种隔离冲突", "到站顺序冲突"])

    with tab1:
        _render_weight_conflicts(plan, conflicts)

    with tab2:
        _render_isolation_conflicts(plan, conflicts)

    with tab3:
        _render_station_conflicts(plan, conflicts)

    st.markdown("---")
    st.subheader("冲突位置标记")
    _render_conflict_bar(plan, conflicts)


def _render_weight_conflicts(plan, conflicts):
    max_weight = st.session_state.train_info["max_weight"]
    total_weight = plan["total_weight"]

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("列车总重", f"{total_weight:.1f} 吨")
    with col_b:
        st.metric("限重", f"{max_weight} 吨")

    progress = min(total_weight / max_weight, 1.0)
    bar_color = "#e74c3c" if total_weight > max_weight else "#2ecc71"

    st.markdown(f'''
    <div style="background:#ecf0f1;border-radius:0.5rem;height:24px;overflow:hidden;">
        <div style="width:{progress * 100}%;height:100%;background:{bar_color};
                    border-radius:0.5rem;transition:width 0.3s;"></div>
    </div>
    <div style="text-align:right;margin-top:0.25rem;font-size:0.8rem;color:#666;">
        装载率: {progress * 100:.1f}%
    </div>
    ''', unsafe_allow_html=True)

    weight_conflicts = [c for c in conflicts if c["type"] == "超重"]
    if weight_conflicts:
        for c in weight_conflicts:
            st.error(f"⚠️ {c['description']}（超出 {c['excess']} 吨）")
    else:
        st.success("✅ 列车重量符合限重要求")

    st.markdown("---")
    st.info("💡 建议：超重时可考虑减少车辆或减轻部分货物重量")


def _render_isolation_conflicts(plan, conflicts):
    isolation_conflicts = [c for c in conflicts if c["type"] == "车种隔离冲突" or c["type"] == "特殊车辆连挂"]

    if not isolation_conflicts:
        st.success("✅ 未检测到车种隔离冲突")
        return

    st.write(f"共检测到 {len(isolation_conflicts)} 个隔离冲突")

    for i, c in enumerate(isolation_conflicts):
        severity_color = {"high": "#e74c3c", "medium": "#f39c12", "low": "#3498db"}.get(c["severity"], "#95a5a6")
        severity_label = {"high": "高危", "medium": "中危", "low": "低危"}.get(c["severity"], "未知")

        st.markdown(f'''
        <div style="padding:1rem;border-left:4px solid {severity_color};
                    background:#fff;border-radius:0.3rem;margin-bottom:0.5rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:bold;color:#333;">{c['type']}</span>
                <span style="background:{severity_color};color:white;padding:2px 8px;
                             border-radius:3px;font-size:0.75rem;">{severity_label}</span>
            </div>
            <div style="color:#666;margin-top:0.5rem;">{c['description']}</div>
            <div style="font-size:0.85rem;color:#999;margin-top:0.25rem;">
                位置: 第 {c.get('position_a', '?')} 位 - 第 {c.get('position_b', '?')} 位
            </div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("---")
    st.info("💡 隔离规则：罐车与冷藏车/家畜车需隔离，长大货物车与家畜车需隔离")


def _render_station_conflicts(plan, conflicts):
    station_conflicts = [c for c in conflicts if c["type"] == "到站顺序冲突"]

    sequence = plan["sequence"]
    station_order_actual = []
    seen_stations = set()
    for car in sequence:
        if car["destination"] not in seen_stations:
            station_order_actual.append(car["destination"])
            seen_stations.add(car["destination"])

    st.subheader("站序对比")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**标准站序**")
        for i, station in enumerate(STATIONS):
            st.markdown(f"{i+1}. {station}")
    with col_b:
        st.write("**实际编组站序**")
        for i, station in enumerate(station_order_actual):
            color = station_color(station)
            is_correct = station == STATIONS[i] if i < len(STATIONS) else False
            status_icon = "✅" if is_correct else "⚠️"
            st.markdown(f'{status_icon} <span style="color:{color};font-weight:bold;">{i+1}. {station}</span>',
                        unsafe_allow_html=True)

    if station_conflicts:
        st.markdown("---")
        st.write(f"共检测到 {len(station_conflicts)} 个到站顺序问题")
        for c in station_conflicts:
            st.warning(f"📍 {c['description']}（首车位置: 第{c.get('position', '?')}位）")
    else:
        st.success("✅ 到站顺序符合站序要求")

    st.markdown("---")
    st.info("💡 站序优化可减少中间站摘挂作业，提高运输效率")


def _render_conflict_bar(plan, conflicts):
    sequence = plan["sequence"]
    if not sequence:
        return

    conflict_positions = {}
    for c in conflicts:
        if "position_a" in c and "position_b" in c:
            for pos in range(c["position_a"], c["position_b"] + 1):
                conflict_positions[pos] = max(
                    conflict_positions.get(pos, ""),
                    {"high": "high", "medium": "medium", "low": "low"}.get(c["severity"], "low")
                )
        elif "position" in c:
            conflict_positions[c["position"]] = max(
                conflict_positions.get(c["position"], ""),
                "medium"
            )

    bar_html = '<div style="display:flex;flex-wrap:wrap;gap:2px;padding:1rem;background:#f8f9fa;border-radius:0.5rem;">'

    for i, car in enumerate(sequence):
        pos = i + 1
        color = station_color(car["destination"])
        has_conflict = pos in conflict_positions

        if has_conflict:
            severity = conflict_positions[pos]
            if severity == "high":
                border_style = "3px solid #e74c3c"
                glow = "0 0 8px #e74c3c"
            elif severity == "medium":
                border_style = "3px solid #f39c12"
                glow = "0 0 6px #f39c12"
            else:
                border_style = "3px solid #3498db"
                glow = "0 0 4px #3498db"
        else:
            border_style = "none"
            glow = "none"

        bar_html += f'''
        <div title="顺位:{pos} | {car['id']} | {car['destination']}{' | 冲突' if has_conflict else ''}"
             style="flex:0 0 auto;width:32px;height:48px;background:{color};
                    border-radius:3px;display:flex;align-items:center;justify-content:center;
                    color:white;font-size:10px;font-weight:bold;
                    border: {border_style};
                    box-shadow: {glow};">
            {pos}
        </div>
        '''

    bar_html += '</div>'
    st.markdown(bar_html, unsafe_allow_html=True)

    st.caption("🔴红框=高危冲突  🟡黄框=中危冲突  🔵蓝框=低危冲突")

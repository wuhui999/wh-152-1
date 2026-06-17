import streamlit as st
from pages import import_page, marshalling_view, conflict_analysis, shunting_operations, export_page

st.set_page_config(
    page_title="铁路货运编组分析看板",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main .block-container {padding-top: 2rem;}
    h1, h2, h3 {color: #1e3a5f;}
    .stMetric {background-color: #f0f5fa; padding: 0.8rem; border-radius: 0.5rem;}
    div[data-testid="stSidebarNav"] li div a {padding-left: 1rem;}
</style>
""", unsafe_allow_html=True)

if "cars" not in st.session_state:
    from data.mock_data import generate_sample_data
    st.session_state.cars = generate_sample_data()
if "marshalling_plan" not in st.session_state:
    st.session_state.marshalling_plan = None
if "conflicts" not in st.session_state:
    st.session_state.conflicts = []
if "shunting_plan" not in st.session_state:
    st.session_state.shunting_plan = None
if "alternative_plan" not in st.session_state:
    st.session_state.alternative_plan = None
if "train_info" not in st.session_state:
    st.session_state.train_info = {
        "train_number": "12345",
        "max_weight": 5000,
        "max_cars": 50
    }

with st.sidebar:
    st.title("🚂 编组分析看板")
    st.markdown("---")
    page = st.radio(
        "导航",
        ["📥 导入数据", "📊 编组视图", "⚠️ 冲突分析", "🔧 调车作业", "📤 方案导出"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("铁路货运编组智能分析系统 v1.0")

if page.startswith("📥"):
    import_page.render()
elif page.startswith("📊"):
    marshalling_view.render()
elif page.startswith("⚠️"):
    conflict_analysis.render()
elif page.startswith("🔧"):
    shunting_operations.render()
elif page.startswith("📤"):
    export_page.render()

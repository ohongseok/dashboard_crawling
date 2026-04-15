import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# ==========================================
# 1. 페이지 설정 및 다크 테마 + 전용 폰트 고정
# ==========================================
st.set_page_config(page_title="운영 로그 대시보드 | KREAM Famous", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    /* 폰트 및 배경 설정 */
    html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, span, div, label {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    .stApp { background-color: #0E1117; }
    
    /* [수정] 데이터 값 색상을 민트색이 아닌 기존의 밝은 화이트/스카이블루 톤으로 복구 */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; /* 가장 깔끔한 화이트로 복구 */
        font-weight: 800 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    [data-testid="stMetricLabel"] { 
        color: #A0A0A0 !important; 
        font-weight: 600 !important;
    }
    
    /* UI 디자인 요소 */
    h1, h2, h3, h4 { color: #FAFAFA !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab"] { color: #A0A0A0; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #00D4FF !important; border-bottom: 2px solid #00D4FF !important; }
    .stDataFrame { border: 1px solid #30363D; border-radius: 8px; }
    .streamlit-expanderHeader { background-color: #161B22 !important; border: 1px solid #30363D !important; color: #FFFFFF !important; }
    hr { border-color: #30363D !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 로드 및 5인 체제 전처리
# ==========================================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7DmLGZwUTOY36vcC1aBgxsPwciNa5nYOYyODgCAPGWN_hR_LF-WXiYsHEdwa9uapI_M610WKtdF3S/pub?gid=808922108&single=true&output=csv"

# [크리티컬] 5인 체제로 확장
TARGET_MANAGERS = ['전현희', '유지윤', '손영우', '고희영', '오홍석']

# 인원별 고유 컬러 매핑 (기여도 파이 = 브랜드 막대 색상 동일화)
COLOR_MAP = {
    '전현희': '#00D4FF', # 스카이블루
    '유지윤': '#B554FF', # 퍼플
    '손영우': '#00FFA3', # 네온그린
    '고희영': '#FF5482', # 핑크레드
    '오홍석': '#FFD166'  # 옐로우
}

def hex_to_rgba(hex_str, opacity=0.2):
    hex_str = hex_str.lstrip('#')
    r, g, b = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {opacity})"

@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url, header=1)
        df['등록 요청일자'] = pd.to_datetime(df['등록 요청일자'], errors='coerce')
        df['Month'] = df['등록 요청일자'].dt.strftime('%Y-%m')
        df['SKU'] = pd.to_numeric(df['SKU'], errors='coerce').fillna(0).astype(int)
        # 공백 제거로 데이터 누락 방지
        df['리스트업 담당자'] = df['리스트업 담당자'].astype(str).str.strip()
        df['주차'] = df['주차'].astype(str).str.strip()
        return df[df['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

df = load_data(CSV_URL)
if df.empty: st.stop()

# ==========================================
# 3. 최상단: 통합 성과 (Executive Summary)
# ==========================================
st.title("📊 리스트업 운영 그룹 Dashboard")
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()

c_date, _ = st.columns([2, 3])
with c_date:
    selected_date = st.date_input("📅 조회 기준일 선택", value=today_date)

target_month = selected_date.strftime('%Y-%m')
target_week = f"{selected_date.strftime('%y')}W{selected_date.isocalendar()[1]:02d}"

df_week = df[df['주차'] == target_week]
df_month = df[df['Month'] == target_month]
df_day = df[df['등록 요청일자'].dt.date == selected_date]

st.markdown("### 🏆 팀 통합 성과 (Team Performance)")
t_tab_w, t_tab_m, t_tab_d = st.tabs([f"🎯 {target_week} 주차", f"📅 {target_month} 월간", f"⚡ {selected_date} 일간"])

def render_team_summary(target_df, label):
    if target_df.empty:
        st.info(f"{label} 데이터가 없습니다.")
        return
    st.metric(f"{label} 총 SKU 합계", f"{target_df['SKU'].sum():,} 개")
    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(target_df.groupby('리스트업 담당자')['SKU'].sum().reset_index(), 
                         values='SKU', names='리스트업 담당자', hole=0.4, template='plotly_dark',
                         color='리스트업 담당자', color_discrete_map=COLOR_MAP, title=f"{label} 인원별 기여도")
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        # 브랜드 막대 그래프에도 인원별 컬러 적용 (Stacked Bar)
        top_brands = target_df.groupby('브랜드')['SKU'].sum().nlargest(7).index
        top_df = target_df[target_df['브랜드'].isin(top_brands)]
        bar_data = top_df.groupby(['브랜드', '리스트업 담당자'])['SKU'].sum().reset_index()
        fig_bar = px.bar(bar_data, y='브랜드', x='SKU', color='리스트업 담당자', 
                         orientation='h', template='plotly_dark', title=f"{label} 탑 브랜드 (인원별 컬러)",
                         color_discrete_map=COLOR_MAP)
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, barmode='stack')
        st.plotly_chart(fig_bar, use_container_width=True)

with t_tab_w: render_team_summary(df_week, "주간")
with t_tab_m: render_team_summary(df_month, "월간")
with t_tab_d: render_team_summary(df_day, "일간")

st.markdown("---")

# ==========================================
# 4. 인원별 실시간 트래커 (5인 체제)
# ==========================================
st.markdown("### ⚡ 인원별 실시간 트래커")
m_cols = st.columns(5) # 5인 컬럼 레이아웃

for i, manager in enumerate(TARGET_MANAGERS):
    with m_cols[i]:
        st.markdown(f"#### 🧑‍💻 {manager}")
        m_tab_w, m_tab_m, m_tab_d = st.tabs(["주간", "월", "일"])
        
        def render_m_tab(m_target_df, p_label):
            m_data = m_target_df[m_target_df['리스트업 담당자'] == manager]
            s_sum = m_data['SKU'].sum() if not m_data.empty else 0
            if s_sum > 0:
                st.metric(f"{p_label} 실적", f"{s_sum:,}")
                st.dataframe(m_data.groupby('브랜드')['SKU'].sum().reset_index().sort_values('SKU', ascending=False), 
                             hide_index=True, use_container_width=True)
            else:
                st.metric(f"{p_label} 실적", "-")
                st.caption("내역 없음")
        
        with m_tab_w: render_m_tab(df_week, "주간")
        with m_tab_m: render_m_tab(df_month, "월간")
        with m_tab_d: render_m_tab(df_day, "일간")

st.markdown("---")

# ==========================================
# 5. 담당자별 데이터 (Deep Dive)
# ==========================================
st.markdown("## 🔍 담당자별 데이터")

for manager in TARGET_MANAGERS:
    m_df = df[df['리스트업 담당자'] == manager]
    st.markdown(f"### 👤 {manager}")
    
    if m_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("기간 SKU", "-")
        c2.metric("브랜드 수", "-")
        c3.metric("팀 내 기여도", "-")
        st.info(f"{manager}님의 작업 데이터가 아직 없습니다.")
        st.markdown("---")
        continue

    p_choice = st.radio("범위 선택:", ["전체 누적", f"{target_month} 월간", f"{target_week} 주간", f"{selected_date} 일간"], horizontal=True, key=f"r_{manager}")
    
    f_df = m_df.copy()
    team_total = 0
    if "월간" in p_choice: 
        f_df = m_df[m_df['Month'] == target_month]
        team_total = df_month['SKU'].sum()
    elif "주간" in p_choice: 
        f_df = m_df[m_df['주차'] == target_week]
        team_total = df_week['SKU'].sum()
    elif "일간" in p_choice: 
        f_df = m_df[m_df['등록 요청일자'].dt.date == selected_date]
        team_total = df_day['SKU'].sum()
    else: 
        team_total = df['SKU'].sum()

    if f_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("기간 SKU", "-")
        c2.metric("브랜드 수", "-")
        c3.metric("팀 내 기여도", "-")
        st.info("선택하신 기간의 데이터가 없습니다.")
        st.markdown("---")
        continue

    # [수정] 누적 기여도 산식: 해당 기간 개인 / 해당 기간 팀 전체
    contrib_str = f"{(f_df['SKU'].sum() / team_total * 100):.1f}%" if team_total > 0 else "0.0%"

    c1, c2, c3 = st.columns(3)
    c1.metric("기간 SKU", f"{f_df['SKU'].sum():,}")
    c2.metric("브랜드 수", f"{f_df['브랜드'].nunique():,}")
    c3.metric("팀 내 기여도", contrib_str)

    ch1, ch2 = st.columns(2)
    with ch1:
        if "일간" not in p_choice:
            t_data = f_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
            fig = px.area(t_data, x='등록 요청일자', y='SKU', template='plotly_dark', title="처리 추이")
            fig.update_traces(line_color=COLOR_MAP[manager], fillcolor=hex_to_rgba(COLOR_MAP[manager], 0.2))
            st.plotly_chart(fig, use_container_width=True)
    with ch2:
        b_data = f_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(5, 'SKU')
        fig = px.pie(b_data, values='SKU', names='브랜드', hole=0.4, template='plotly_dark', title="탑 브랜드 Top 5")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📑 상세 로그 보기"):
        st.dataframe(f_df.sort_values('등록 요청일자', ascending=False), use_container_width=True, hide_index=True)
    st.markdown("---")

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# ==========================================
# 1. 페이지 설정 및 다크 테마 UI 고정
# ==========================================
st.set_page_config(page_title="운영 로그 대시보드 | KREAM Famous", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4, p, span, div, label, .stMarkdown { color: #FAFAFA !important; }
    
    /* 메인 지표 강조 */
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 800; }
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; }
    
    /* 탭(Tabs) 디자인 커스텀 (다크 테마에 맞게) */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
    .stTabs [data-baseweb="tab"] { color: #A0A0A0; font-weight: 600; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { color: #00D4FF !important; border-bottom: 2px solid #00D4FF !important; }
    
    .stDataFrame { border: 1px solid #30363D; border-radius: 8px; }
    .streamlit-expanderHeader { background-color: #161B22 !important; border: 1px solid #30363D !important; color: #FFFFFF !important; }
    hr { border-color: #30363D !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 로드 및 전처리
# ==========================================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7DmLGZwUTOY36vcC1aBgxsPwciNa5nYOYyODgCAPGWN_hR_LF-WXiYsHEdwa9uapI_M610WKtdF3S/pub?gid=808922108&single=true&output=csv"
TARGET_MANAGERS = ['전현희', '유지윤', '손영우']

# 담당자별 고유 색상 지정 (차트 가독성용)
COLOR_MAP = {'전현희': '#00D4FF', '유지윤': '#B554FF', '손영우': '#00FFA3'}

@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url, header=1)
        df['등록 요청일자'] = pd.to_datetime(df['등록 요청일자'], errors='coerce')
        df['Month'] = df['등록 요청일자'].dt.strftime('%Y-%m')
        df['SKU'] = pd.to_numeric(df['SKU'], errors='coerce').fillna(0).astype(int)
        df['주차'] = df['주차'].astype(str).str.strip()
        return df[df['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

df = load_data(CSV_URL)
if df.empty: st.stop()

# ==========================================
# 3. 최상단: 기준일 설정 및 통합 성과 (Executive Summary)
# ==========================================
st.title("📊 리스트업 운영 그룹 Dashboard")
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()

c_date, c_empty = st.columns([2, 3])
with c_date:
    selected_date = st.date_input("📅 조회 기준일 선택", value=today_date)

target_month = selected_date.strftime('%Y-%m')
target_week = f"{selected_date.strftime('%y')}W{selected_date.isocalendar()[1]:02d}"

# 기간별 데이터 분리
df_week = df[df['주차'] == target_week]
df_month = df[df['Month'] == target_month]
df_day = df[df['등록 요청일자'].dt.date == selected_date]

st.markdown("### 🏆 팀 통합 성과 (Team Performance)")

# 통합 성과 탭 구성 (주차가 기본 화면)
tab_t_week, tab_t_month, tab_t_day = st.tabs([f"🎯 {target_week} 주차 (Main)", f"📅 {target_month} 월간", f"⚡ {selected_date} 일간"])

def render_team_tab(target_df, period_name):
    if target_df.empty:
        st.info(f"해당 {period_name}의 작업 데이터가 없습니다.")
        return
    
    total_sku = target_df['SKU'].sum()
    st.metric(f"{period_name} 총 SKU 합계", f"{total_sku:,} 개")
    
    ch1, ch2 = st.columns(2)
    with ch1:
        # 1. 인원별 기여도 (도넛 차트)
        pie_data = target_df.groupby('리스트업 담당자')['SKU'].sum().reset_index()
        fig_pie = px.pie(pie_data, values='SKU', names='리스트업 담당자', title=f"{period_name} 팀원 기여도", 
                         hole=0.4, template='plotly_dark', color='리스트업 담당자', color_discrete_map=COLOR_MAP)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
    with ch2:
        # 2. 상위 브랜드 (막대 차트)
        bar_data = target_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(7, 'SKU')
        fig_bar = px.bar(bar_data, x='SKU', y='브랜드', orientation='h', title=f"{period_name} 탑 브랜드", 
                         template='plotly_dark', color_discrete_sequence=['#00D4FF'])
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=300)
        st.plotly_chart(fig_bar, use_container_width=True)

with tab_t_week: render_team_tab(df_week, "주간")
with tab_t_month: render_team_tab(df_month, "월간")
with tab_t_day: render_team_tab(df_day, "일간")

st.markdown("---")

# ==========================================
# 4. 실시간 인원별 현황 (Live Tracker)
# ==========================================
st.markdown("### ⚡ 인원별 실시간 트래커")
manager_cols = st.columns(3)

for idx, manager in enumerate(TARGET_MANAGERS):
    with manager_cols[idx]:
        st.markdown(f"#### 🧑‍💻 {manager}")
        
        # 개인 탭 구성 (주차가 기본)
        tab_m_w, tab_m_m, tab_m_d = st.tabs(["주간", "월간", "일간"])
        
        m_df_w = df_week[df_week['리스트업 담당자'] == manager]
        m_df_m = df_month[df_month['리스트업 담당자'] == manager]
        m_df_d = df_day[df_day['리스트업 담당자'] == manager]
        
        def render_manager_tab(m_df, period_label):
            sku_sum = m_df['SKU'].sum()
            st.metric(f"{period_label} 실적", f"{sku_sum:,} SKU")
            if sku_sum > 0:
                st.caption(f"📌 {period_label} 작업 브랜드")
                b_df = m_df.groupby('브랜드')['SKU'].sum().reset_index().sort_values('SKU', ascending=False)
                st.dataframe(b_df, hide_index=True, use_container_width=True)
            else:
                st.caption("작업 내역 없음")

        with tab_m_w: render_manager_tab(m_df_w, "주간")
        with tab_m_m: render_manager_tab(m_df_m, "월간")
        with tab_m_d: render_manager_tab(m_df_d, "일간")

st.markdown("---")

# ==========================================
# 5. 담당자별 심층 분석 (Deep Dive - 기간 필터 추가)
# ==========================================
st.markdown("## 🔍 담당자별 심층 분석 (Deep Dive)")
st.caption("개별 담당자의 데이터를 원하는 기간(전체/월간/주간) 단위로 깊이 있게 분석합니다.")

for manager in TARGET_MANAGERS:
    m_df = df[df['리스트업 담당자'] == manager]
    if m_df.empty: continue

    st.markdown(f"### 👤 {manager}")
    
    # [Deep Dive 전용] 기간 선택 라디오 버튼
    period_choice = st.radio(
        "조회 범위 설정:", 
        ["전체 누적", f"{target_month} 월간", f"{target_week} 주간", f"{selected_date} 일간"],
        horizontal=True, 
        key=f"radio_{manager}"
    )
    
    # 선택된 기간에 맞게 데이터 재필터링
    filtered_m_df = m_df.copy()
    if period_choice == f"{target_month} 월간": filtered_m_df = m_df[m_df['Month'] == target_month]
    elif period_choice == f"{target_week} 주간": filtered_m_df = m_df[m_df['주차'] == target_week]
    elif period_choice == f"{selected_date} 일간": filtered_m_df = m_df[m_df['등록 요청일자'].dt.date == selected_date]

    if filtered_m_df.empty:
        st.warning(f"선택하신 '{period_choice}' 기간의 데이터가 없습니다.")
        st.markdown("---")
        continue

    # 1. 지표
    mc1, mc2, mc3 = st.columns(3)
    p_sku = filtered_m_df['SKU'].sum()
    mc1.metric(f"해당 기간 SKU", f"{p_sku:,}")
    mc2.metric("작업 브랜드 수", f"{filtered_m_df['브랜드'].nunique():,}")
    
    # 전체 기간 대비 선택 기간의 달성률 (일간 조회 시 제외)
    if period_choice != "전체 누적":
        mc3.metric("전체 누적 대비 비중", f"{(p_sku / m_df['SKU'].sum() * 100):.1f}%")
    else:
        mc3.metric("팀 내 기여도", f"{(p_sku / df['SKU'].sum() * 100):.1f}%")

    # 2. 차트
    ch1, ch2 = st.columns(2)
    with ch1:
        if period_choice == f"{selected_date} 일간":
            st.info("일간 조회 시 추이 그래프는 제공되지 않습니다.")
        else:
            trend_data = filtered_m_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
            fig_trend = px.area(trend_data, x='등록 요청일자', y='SKU', title=f"{period_choice} 처리 추이", 
                                height=250, template='plotly_dark')
            fig_trend.update_traces(line_color=COLOR_MAP[manager], fillcolor=f"{COLOR_MAP[manager]}33") # 투명도 적용
            st.plotly_chart(fig_trend, use_container_width=True)
            
    with ch2:
        brand_data = filtered_m_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(5, 'SKU')
        fig_pie = px.pie(brand_data, values='SKU', names='브랜드', title=f"{period_choice} 주요 브랜드 Top 5", 
                         hole=0.4, height=250, template='plotly_dark', color_discrete_sequence=px.colors.sequential.Tealgrn)
        st.plotly_chart(fig_pie, use_container_width=True)

    # 3. 상세 로그 (Expander)
    with st.expander(f"📑 {period_choice} 상세 데이터 로그 보기"):
        st.dataframe(filtered_m_df.sort_values('등록 요청일자', ascending=False), use_container_width=True, hide_index=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

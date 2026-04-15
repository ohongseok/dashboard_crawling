import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# ==========================================
# 1. 페이지 설정 및 Custom CSS
# ==========================================
st.set_page_config(page_title="운영 로그 대시보드 | KREAM Famous", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .reportview-container .main .block-container{ max-width: 1200px; }
    h1, h2, h3 { color: #1E1E1E; }
    .stMetric { background-color: #F8F9FA; padding: 10px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 로드 및 전처리 (3명 고정)
# ==========================================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7DmLGZwUTOY36vcC1aBgxsPwciNa5nYOYyODgCAPGWN_hR_LF-WXiYsHEdwa9uapI_M610WKtdF3S/pub?gid=808922108&single=true&output=csv"
TARGET_MANAGERS = ['전현희', '유지윤', '손영우']

@st.cache_data(ttl=300)
def load_and_filter_data(url):
    df = pd.read_csv(url, header=1)
    df['등록 요청일자'] = pd.to_datetime(df['등록 요청일자'], errors='coerce')
    df['SKU'] = pd.to_numeric(df['SKU'], errors='coerce').fillna(0).astype(int)
    
    # 지정된 3명의 데이터만 유지
    filtered_df = df[df['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()
    return filtered_df

try:
    df = load_and_filter_data(CSV_URL)
except Exception as e:
    st.error(f"데이터 연동 실패: {e}")
    st.stop()

# ==========================================
# 3. 최상단: 통합 성과 (Executive Summary)
# ==========================================
st.title("📊 리스트업 운영 그룹 Dashboard")
st.markdown(f"**조회 시점:** {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M')} (KST)")

total_sku = df['SKU'].sum()
total_brands = df['브랜드'].nunique()
total_logs = len(df)

st.markdown("### 🏆 3인 통합 누적 성과")
c1, c2, c3, c4 = st.columns(4)
c1.metric("누적 처리 SKU", f"{total_sku:,} 개")
c2.metric("전체 담당 브랜드", f"{total_brands:,} 개")
c3.metric("누적 작업 건수", f"{total_logs:,} 건")
c4.metric("운영 인원", "3 명")

st.markdown("---")

# ==========================================
# 4. 실시간 일일 현황 (Team Lead Focus)
# ==========================================
st.markdown("### ⚡ Live: 일일 작업 현황")
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()

# 팀 리드들을 위한 날짜 선택기 (기본: 오늘)
selected_date = st.date_input("📅 작업 일자 선택", value=today_date)
daily_df = df[df['등록 요청일자'].dt.date == selected_date]

if daily_df.empty:
    st.info(f"{selected_date} 일자의 작업 내역이 아직 업데이트되지 않았습니다.")
else:
    lead_cols = st.columns(3)
    for idx, manager in enumerate(TARGET_MANAGERS):
        with lead_cols[idx]:
            m_daily = daily_df[daily_df['리스트업 담당자'] == manager]
            st.markdown(f"#### 🧑‍💻 {manager}")
            if m_daily.empty:
                st.caption("오늘 작업 내역 없음")
            else:
                st.metric("금일 SKU", f"{m_daily['SKU'].sum():,} 개")
                # 당일 브랜드 리스트
                m_daily_summary = m_daily.groupby('브랜드')['SKU'].sum().reset_index().sort_values('SKU', ascending=False)
                st.dataframe(m_daily_summary, hide_index=True, use_container_width=True)

st.markdown("---")

# ==========================================
# 5. 개인별 Deep Dive (지표/차트 상시노출 + 로그 접기)
# ==========================================
st.markdown("## 🔍 담당자별 상세 분석")

for manager in TARGET_MANAGERS:
    m_df = df[df['리스트업 담당자'] == manager]
    if m_df.empty: continue

    st.markdown(f"### 👤 {manager} 실적 분석")
    
    # [1] 개인 요약 지표
    m_sku = m_df['SKU'].sum()
    m_brand_cnt = m_df['브랜드'].nunique()
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("개인 누적 SKU", f"{m_sku:,} 개")
    mc2.metric("담당 브랜드 수", f"{m_brand_cnt:,} 개")
    mc3.metric("팀 내 기여도", f"{(m_sku/total_sku*100):.1f}%")

    # [2] 시각화 차트 (상시 노출)
    ch1, ch2 = st.columns(2)
    with ch1:
        m_trend = m_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
        fig_trend = px.area(m_trend, x='등록 요청일자', y='SKU', title=f"{manager} 등록 추이",
                            template='plotly_white', color_discrete_sequence=['#4361EE'])
        fig_trend.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_trend, use_container_width=True)
    with ch2:
        m_brand = m_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(5, 'SKU')
        fig_pie = px.pie(m_brand, values='SKU', names='브랜드', title=f"{manager} 주요 브랜드 (Top 5)",
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_pie.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    # [3] 상세 운영 로그 (요청하신 대로 클릭하여 펼치는 방식)
    # expander 내부의 제목은 C-Level 가독성을 위해 간결하게 설정
    with st.expander(f"📑 {manager} 상세 데이터 로그 확인하기 (클릭)"):
        st.dataframe(
            m_df.sort_values('등록 요청일자', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    
    st.markdown("<br>", unsafe_allow_html=True) # 담당자 간 여백
    st.markdown("---")

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# ==========================================
# 1. 페이지 설정 및 다크 테마 고정 (Clean Black UI)
# ==========================================
st.set_page_config(page_title="운영 로그 대시보드 | KREAM Famous", page_icon="📊", layout="wide")

# [핵심] 배경은 완전 검정, 글자는 흰색으로 강제 고정하여 '지저분함'을 제거
st.markdown("""
    <style>
    /* 전체 배경을 딥 다크 컬러로 고정 */
    .stApp {
        background-color: #0E1117;
    }
    
    /* 모든 텍스트 기본색을 밝은 회색/흰색으로 설정 */
    h1, h2, h3, h4, p, span, div, label, .stMarkdown {
        color: #FAFAFA !important;
    }

    /* 지표(Metric) 카드 숫자색을 화이트/스카이블루로 강조 */
    [data-testid="stMetricValue"] {
        color: #00D4FF !important;
        font-weight: 700;
    }
    
    /* 지표 라벨 색상 */
    [data-testid="stMetricLabel"] {
        color: #A0A0A0 !important;
    }

    /* 데이터프레임 배경 및 가독성 조절 */
    .stDataFrame {
        border: 1px solid #30363D;
        border-radius: 8px;
    }

    /* Expander(상세 로그) 디자인 깔끔하게 정리 */
    .streamlit-expanderHeader {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        color: #FFFFFF !important;
    }
    
    /* 구분선 색상 */
    hr {
        border-color: #30363D !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 로드 및 전처리 (지정 3인 전용)
# ==========================================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7DmLGZwUTOY36vcC1aBgxsPwciNa5nYOYyODgCAPGWN_hR_LF-WXiYsHEdwa9uapI_M610WKtdF3S/pub?gid=808922108&single=true&output=csv"
TARGET_MANAGERS = ['전현희', '유지윤', '손영우']

@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url, header=1)
        df['등록 요청일자'] = pd.to_datetime(df['등록 요청일자'], errors='coerce')
        df['SKU'] = pd.to_numeric(df['SKU'], errors='coerce').fillna(0).astype(int)
        # 3명의 데이터만 추출
        return df[df['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

df = load_data(CSV_URL)

if df.empty:
    st.stop()

# ==========================================
# 3. 최상단: 통합 성과 (Executive Summary)
# ==========================================
st.title("📊 리스트업 운영 그룹 Dashboard")
st.caption(f"기준 시각: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M')} (KST)")

total_sku = df['SKU'].sum()
c1, c2, c3 = st.columns(3)
with c1: st.metric("그룹 누적 SKU 합계", f"{total_sku:,} 개")
with c2: st.metric("전체 운영 브랜드", f"{df['브랜드'].nunique():,} 개")
with c3: st.metric("누적 작업 건수", f"{len(df):,} 건")

st.markdown("---")

# ==========================================
# 4. 실시간 일간 현황 (Live: 팀 리드 필수 확인 영역)
# ==========================================
st.markdown("### ⚡ Live: 일일 작업 현황")
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()
selected_date = st.date_input("📅 조회 일자", value=today_date)

daily_df = df[df['등록 요청일자'].dt.date == selected_date]

if daily_df.empty:
    st.info(f"{selected_date}에 기록된 작업 데이터가 없습니다.")
else:
    cols = st.columns(3)
    for idx, manager in enumerate(TARGET_MANAGERS):
        with cols[idx]:
            m_daily = daily_df[daily_df['리스트업 담당자'] == manager]
            st.markdown(f"#### 🧑‍💻 {manager}")
            if not m_daily.empty:
                st.metric("금일 SKU", f"{m_daily['SKU'].sum():,} 개")
                st.dataframe(m_daily.groupby('브랜드')['SKU'].sum().reset_index().sort_values('SKU', ascending=False), 
                             hide_index=True, use_container_width=True)
            else:
                st.caption("금일 작업 내역 없음")

st.markdown("---")

# ==========================================
# 5. 담당자별 상세 분석 (Deep Dive)
# ==========================================
st.markdown("## 🔍 담당자별 심층 분석")

for manager in TARGET_MANAGERS:
    m_df = df[df['리스트업 담당자'] == manager]
    if m_df.empty: continue

    st.markdown(f"### 👤 {manager} Performance")
    
    # [1] 개인 지표 요약
    mc1, mc2, mc3 = st.columns(3)
    m_sku_sum = m_df['SKU'].sum()
    mc1.metric("개인 누적 SKU", f"{m_sku_sum:,} 개")
    mc2.metric("담당 브랜드 수", f"{m_df['브랜드'].nunique():,} 개")
    mc3.metric("누적 기여도", f"{(m_sku_sum/total_sku*100):.1f}%")
    
    # [2] 시각화 (다크 테마 차트 적용)
    ch1, ch2 = st.columns(2)
    with ch1:
        trend_data = m_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
        fig_trend = px.area(trend_data, x='등록 요청일자', y='SKU', title="처리 추이", 
                            height=250, template='plotly_dark')
        # 차트 내부 색상을 좀 더 선명하게 조정
        fig_trend.update_traces(line_color='#00D4FF', fillcolor='rgba(0, 212, 255, 0.2)')
        st.plotly_chart(fig_trend, use_container_width=True)
    with ch2:
        brand_data = m_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(5, 'SKU')
        fig_pie = px.pie(brand_data, values='SKU', names='브랜드', title="주요 브랜드 Top 5", 
                         hole=0.4, height=250, template='plotly_dark')
        st.plotly_chart(fig_pie, use_container_width=True)

    # [3] 상세 로그 접기 (깔끔한 인터페이스)
    with st.expander(f"📑 {manager} 전체 상세 운영 로그 (클릭 시 전개)"):
        st.dataframe(
            m_df.sort_values('등록 요청일자', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

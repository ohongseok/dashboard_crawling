import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# ==========================================
# 1. 페이지 설정 및 UI 고정 (폰트 묻힘 방지 CSS)
# ==========================================
st.set_page_config(page_title="운영 로그 대시보드 | KREAM Famous", page_icon="📊", layout="wide")

# 임원진용 UI: 테마와 상관없이 글자가 잘 보이도록 배경과 글자색을 명시적으로 설정합니다.
st.markdown("""
    <style>
    /* 전체 앱 배경 흰색 고정 */
    .stApp { background-color: #FFFFFF; }
    
    /* 모든 텍스트를 어두운 색으로 고정하여 하얀 배경에서 잘 보이게 함 */
    h1, h2, h3, h4, h5, p, span, div, .stMarkdown {
        color: #1E1E1E !important;
    }
    
    /* 지표(Metric) 카드 숫자 색상 강조 (파란색) */
    [data-testid="stMetricValue"] {
        color: #007BFF !important;
    }
    
    /* 지표 라벨 색상 */
    [data-testid="stMetricLabel"] {
        color: #555555 !important;
    }

    /* 상세 로그(Expander) 배경 조절 */
    .streamlit-expanderHeader {
        background-color: #F1F3F5 !important;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 로드 및 전처리 (3명 전용)
# ==========================================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7DmLGZwUTOY36vcC1aBgxsPwciNa5nYOYyODgCAPGWN_hR_LF-WXiYsHEdwa9uapI_M610WKtdF3S/pub?gid=808922108&single=true&output=csv"
TARGET_MANAGERS = ['전현희', '유지윤', '손영우']

@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url, header=1)
        df['등록 요청일자'] = pd.to_datetime(df['등록 요청일자'], errors='coerce')
        df['SKU'] = pd.to_numeric(df['SKU'], errors='coerce').fillna(0).astype(int)
        # 지정된 3명의 데이터만 필터링
        return df[df['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

df = load_data(CSV_URL)

if df.empty:
    st.warning("데이터가 없거나 URL 확인이 필요합니다.")
    st.stop()

# ==========================================
# 3. 최상단: 통합 성과 (Executive Summary)
# ==========================================
st.title("📊 리스트업 운영 그룹 Dashboard")
st.caption(f"최종 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M')} (KST)")

total_sku = df['SKU'].sum()
c1, c2, c3 = st.columns(3)
c1.metric("3인 누적 처리 SKU", f"{total_sku:,} 개")
c2.metric("전체 담당 브랜드", f"{df['브랜드'].nunique():,} 개")
c3.metric("누적 작업 건수", f"{len(df):,} 건")

st.markdown("---")

# ==========================================
# 4. 실시간 일간 현황 (Live Tracker)
# ==========================================
st.markdown("### ⚡ Live: 일일 작업 현황")
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()
selected_date = st.date_input("📅 작업 일자 선택", value=today_date)

daily_df = df[df['등록 요청일자'].dt.date == selected_date]

if daily_df.empty:
    st.info(f"{selected_date} 일자의 작업 내역이 없습니다.")
else:
    cols = st.columns(3)
    for idx, manager in enumerate(TARGET_MANAGERS):
        with cols[idx]:
            m_daily = daily_df[daily_df['리스트업 담당자'] == manager]
            st.markdown(f"#### 🧑‍💻 {manager}")
            if not m_daily.empty:
                st.metric("금일 SKU", f"{m_daily['SKU'].sum():,} 개")
                st.dataframe(m_daily.groupby('브랜드')['SKU'].sum().reset_index(), 
                             hide_index=True, use_container_width=True)
            else:
                st.caption("금일 내역 없음")

st.markdown("---")

# ==========================================
# 5. 담당자별 상세 분석 (로그만 접기)
# ==========================================
st.markdown("## 🔍 담당자별 심층 분석")

for manager in TARGET_MANAGERS:
    m_df = df[df['리스트업 담당자'] == manager]
    if m_df.empty: continue

    st.markdown(f"### 👤 {manager} 성과 현황")
    
    # 지표 및 차트 상시 노출
    mc1, mc2, mc3 = st.columns(3)
    m_sku_sum = m_df['SKU'].sum()
    mc1.metric("개인 누적 SKU", f"{m_sku_sum:,} 개")
    mc2.metric("담당 브랜드 수", f"{m_df['브랜드'].nunique():,} 개")
    mc3.metric("기여도", f"{(m_sku_sum/total_sku*100):.1f}%")
    
    ch1, ch2 = st.columns(2)
    with ch1:
        trend_data = m_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
        fig_trend = px.area(trend_data, x='등록 요청일자', y='SKU', title="일자별 처리 추이", height=250)
        st.plotly_chart(fig_trend, use_container_width=True)
    with ch2:
        brand_data = m_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(5, 'SKU')
        fig_pie = px.pie(brand_data, values='SKU', names='브랜드', title="주요 브랜드 Top 5", hole=0.4, height=250)
        st.plotly_chart(fig_pie, use_container_width=True)

    # 상세 로그만 접기 (이 부분만 클릭으로 확인 가능)
    with st.expander(f"📑 {manager} 전체 상세 운영 로그 보기"):
        st.dataframe(
            m_df.sort_values('등록 요청일자', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    
    st.markdown("---")

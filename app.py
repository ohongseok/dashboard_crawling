import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# ==========================================
# 1. 페이지 설정 및 다크 테마 UI
# ==========================================
st.set_page_config(page_title="운영 로그 대시보드 | KREAM Famous", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4, p, span, div, label, .stMarkdown { color: #FAFAFA !important; }
    
    /* 메인 지표(KPI) 강조 스타일 */
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: 800; font-size: 2.5rem !important; }
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; font-size: 1.1rem !important; }
    
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

if df.empty:
    st.stop()

# ==========================================
# 3. 최상단: 메인 주차별 데이터 (Main Focus)
# ==========================================
st.title("📊 리스트업 운영 그룹 Dashboard")
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()

# 날짜 선택이 상단 지표를 결정합니다.
c_date, c_empty = st.columns([2, 3])
with c_date:
    selected_date = st.date_input("📅 조회 기준일 선택", value=today_date)

# 타겟 주차 및 월 계산
target_month = selected_date.strftime('%Y-%m')
target_week = f"{selected_date.strftime('%y')}W{selected_date.isocalendar()[1]:02d}"

# 데이터 필터링
weekly_total_df = df[df['주차'] == target_week]
monthly_total_df = df[df['Month'] == target_month]
cumulative_total_sku = df['SKU'].sum()

st.markdown(f"### 🏆 {target_week} 주차 통합 성과 (Main)")
m1, m2, m3 = st.columns(3)
with m1:
    st.metric(f"{target_week} 주차 SKU 합계", f"{weekly_total_df['SKU'].sum():,}")
with m2:
    st.metric(f"{target_month} 월간 SKU 합계", f"{monthly_total_df['SKU'].sum():,}")
with m3:
    st.metric("전체 누적 SKU 합계", f"{cumulative_total_sku:,}")

st.markdown("---")

# ==========================================
# 4. 실시간 인원별 현황 (일간/주간/월간 집계)
# ==========================================
st.markdown(f"### ⚡ 인원별 성과 트래커 ({target_week} / {target_month})")

manager_cols = st.columns(3)

for idx, manager in enumerate(TARGET_MANAGERS):
    with manager_cols[idx]:
        st.markdown(f"#### 🧑‍💻 {manager}")
        m_df = df[df['리스트업 담당자'] == manager]
        
        # 각 기간별 SKU 계산
        d_sku = m_df[m_df['등록 요청일자'].dt.date == selected_date]['SKU'].sum()
        w_sku = m_df[m_df['주차'] == target_week]['SKU'].sum()
        m_sku = m_df[m_df['Month'] == target_month]['SKU'].sum()
        
        # 카드형 지표 표시
        st.metric("금일 실적", f"{d_sku:,} SKU")
        st.metric("주간 실적", f"{w_sku:,} SKU")
        st.metric("월간 실적", f"{m_sku:,} SKU")
        
        # 오늘 어떤 브랜드를 작업했는지 즉시 확인
        st.markdown("**[금일 작업 브랜드]**")
        today_brands = m_df[m_df['등록 요청일자'].dt.date == selected_date].groupby('브랜드')['SKU'].sum().reset_index()
        if not today_brands.empty:
            st.dataframe(today_brands.sort_values('SKU', ascending=False), hide_index=True, use_container_width=True)
        else:
            st.caption("해당일 작업 내역 없음")

st.markdown("---")

# ==========================================
# 5. 담당자별 심층 분석 (Deep Dive)
# ==========================================
st.markdown("## 🔍 담당자별 심층 분석")

for manager in TARGET_MANAGERS:
    m_df = df[df['리스트업 담당자'] == manager]
    if m_df.empty: continue

    st.markdown(f"### 👤 {manager} Performance History")
    
    # 누적 성과 지표
    mc1, mc2, mc3 = st.columns(3)
    m_sku_sum = m_df['SKU'].sum()
    mc1.metric("개인 총 누적 SKU", f"{m_sku_sum:,}")
    mc2.metric("누적 담당 브랜드", f"{m_df['브랜드'].nunique():,}")
    mc3.metric("팀 내 SKU 기여도", f"{(m_sku_sum/cumulative_total_sku*100):.1f}%")
    
    # 시각화 (추이 및 비중)
    ch1, ch2 = st.columns(2)
    with ch1:
        trend_data = m_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
        fig_trend = px.area(trend_data, x='등록 요청일자', y='SKU', title="전체 기간 처리 추이", 
                            height=250, template='plotly_dark')
        fig_trend.update_traces(line_color='#00D4FF', fillcolor='rgba(0, 212, 255, 0.2)')
        st.plotly_chart(fig_trend, use_container_width=True)
    with ch2:
        brand_data = m_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(5, 'SKU')
        fig_pie = px.pie(brand_data, values='SKU', names='브랜드', title="누적 주요 브랜드 Top 5", 
                         hole=0.4, height=250, template='plotly_dark')
        st.plotly_chart(fig_pie, use_container_width=True)

    # 상세 데이터 로그 (Expander)
    with st.expander(f"📑 {manager} 전체 상세 로그 확인"):
        st.dataframe(
            m_df.sort_values('등록 요청일자', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

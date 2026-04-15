import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz

# ==========================================
# 1. 페이지 기본 설정 및 Custom CSS (깔끔한 UI)
# ==========================================
st.set_page_config(page_title="운영 로그 대시보드 | KREAM Famous", page_icon="📊", layout="wide")

# UI 가독성을 높이는 Custom CSS
st.markdown("""
    <style>
    .reportview-container .main .block-container{ max-width: 1200px; }
    h1, h2, h3 { color: #1E1E1E; }
    .metric-card { background-color: #F8F9FA; border-radius: 10px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 로드 및 전처리 (3명 전용)
# ==========================================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7DmLGZwUTOY36vcC1aBgxsPwciNa5nYOYyODgCAPGWN_hR_LF-WXiYsHEdwa9uapI_M610WKtdF3S/pub?gid=808922108&single=true&output=csv"
TARGET_MANAGERS = ['전현희', '유지윤', '손영우']

@st.cache_data(ttl=300) # 5분 주기 캐시
def load_and_filter_data(url):
    df = pd.read_csv(url, header=1)
    
    # 날짜 데이터 전처리
    df['등록 요청일자'] = pd.to_datetime(df['등록 요청일자'], errors='coerce')
    
    # 숫자형 변환 및 결측치 처리
    df['SKU'] = pd.to_numeric(df['SKU'], errors='coerce').fillna(0).astype(int)
    
    # 🌟 핵심: 지정된 3명의 데이터만 추출
    filtered_df = df[df['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()
    return filtered_df

try:
    df = load_and_filter_data(CSV_URL)
except Exception as e:
    st.error(f"데이터 연동 오류: {e}")
    st.stop()

# ==========================================
# 3. 최상단: 3인 총 누적 성과 (Executive Summary)
# ==========================================
st.title("📊 리스트업 운영 그룹 Dashboard")
st.markdown("전현희, 유지윤, 손영우 담당자의 실시간 처리 현황 및 누적 성과 지표입니다.")

# 전체 누적 데이터 계산
total_sku = df['SKU'].sum()
total_brands = df['브랜드'].nunique()
total_logs = len(df)
top_brand = df.groupby('브랜드')['SKU'].sum().idxmax() if not df.empty else "N/A"

st.markdown("### 🏆 3인 통합 누적 성과")
col1, col2, col3, col4 = st.columns(4)
col1.metric("누적 처리 SKU", f"{total_sku:,} 개")
col2.metric("다룬 브랜드 수", f"{total_brands:,} 개")
col3.metric("최다 처리 브랜드", top_brand)
col4.metric("총 작업 건수", f"{total_logs:,} 건")

st.markdown("---")

# ==========================================
# 4. 일간 실시간 트래커 (Team Lead's Request)
# ==========================================
st.markdown("### ⚡ Live: 일일 작업 현황 (조회일 기준)")
st.caption("오늘 날짜를 기준으로 당일 진행된 브랜드와 SKU 현황을 실시간으로 보여줍니다.")

# 한국 시간 기준 '오늘' 설정, 조회일 변경 기능 제공 (기본값: 오늘)
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()

selected_date = st.date_input("조회 일자 선택", value=today_date)
daily_df = df[df['등록 요청일자'].dt.date == selected_date]

if daily_df.empty:
    st.info(f"{selected_date} 일자에 진행된 작업 내역이 없습니다.")
else:
    # 3명을 가로로 배치하여 한눈에 비교
    lead_cols = st.columns(3)
    
    for idx, manager in enumerate(TARGET_MANAGERS):
        with lead_cols[idx]:
            st.markdown(f"#### 🧑‍💻 {manager}")
            m_daily_df = daily_df[daily_df['리스트업 담당자'] == manager]
            
            if m_daily_df.empty:
                st.write("작업 내역 없음")
            else:
                daily_sku_sum = m_daily_df['SKU'].sum()
                st.metric("금일 처리 SKU", f"{daily_sku_sum:,} 개")
                
                # 금일 작업한 브랜드 리스트업
                st.markdown("**[작업 브랜드 및 SKU]**")
                brand_summary = m_daily_df.groupby('브랜드')['SKU'].sum().reset_index()
                brand_summary = brand_summary.sort_values(by='SKU', ascending=False)
                st.dataframe(brand_summary, hide_index=True, use_container_width=True)

st.markdown("---")

# ==========================================
# 5. 개인별 심층 분석 (Tabs 활용)
# ==========================================
st.markdown("### 🔍 담당자별 심층 분석 (Deep Dive)")
st.caption("각 담당자별 누적 기여도와 브랜드 처리 비중을 분석합니다.")

# 스크롤을 줄이기 위해 Tab 사용
tabs = st.tabs([f"👨‍💻 {manager} 데이터" for manager in TARGET_MANAGERS])

for idx, manager in enumerate(TARGET_MANAGERS):
    with tabs[idx]:
        m_df = df[df['리스트업 담당자'] == manager]
        
        if m_df.empty:
            st.warning(f"{manager} 담당자의 데이터가 없습니다.")
            continue
            
        m_total_sku = m_df['SKU'].sum()
        m_total_brands = m_df['브랜드'].nunique()
        
        # 담당자 요약 지표
        c1, c2, c3 = st.columns(3)
        c1.metric("개인 누적 SKU", f"{m_total_sku:,} 개")
        c2.metric("개인 담당 브랜드 수", f"{m_total_brands:,} 개")
        c3.metric("팀 내 SKU 기여도", f"{(m_total_sku / total_sku * 100):.1f}%")
        
        st.write("") # 여백
        
        # 차트 영역: 시계열 & 파이 차트
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("**일자별 SKU 처리 추이**")
            m_trend = m_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
            fig_trend = px.area(m_trend, x='등록 요청일자', y='SKU', 
                                template='plotly_white', color_discrete_sequence=['#2E3192'])
            fig_trend.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300)
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with chart_col2:
            st.markdown("**주요 처리 브랜드 비중 (Top 7)**")
            m_brand = m_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(7, 'SKU')
            fig_pie = px.pie(m_brand, values='SKU', names='브랜드', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        # 담당자 전체 Raw Data (숨김/펼침 기능으로 깔끔하게 처리)
        with st.expander(f"📁 {manager} 상세 운영 로그 (클릭하여 펼치기)"):
            st.dataframe(m_df.sort_values('등록 요청일자', ascending=False), use_container_width=True, hide_index=True)

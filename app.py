import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==========================================
# 1. 페이지 설정 및 디자인
# ==========================================
st.set_page_config(page_title="운영 로그 실시간 대시보드", page_icon="📈", layout="wide")

st.title("🚀 크롤링 운영 로그 실시간 대시보드")
st.markdown("구글 스프레드시트와 실시간 연동되어 담당자별 성과와 브랜드 현황을 분석합니다.")

# ==========================================
# 2. 데이터 로드 (실시간 반영 설정)
# ==========================================
# 제공해주신 웹 게시 CSV URL
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7DmLGZwUTOY36vcC1aBgxsPwciNa5nYOYyODgCAPGWN_hR_LF-WXiYsHEdwa9uapI_M610WKtdF3S/pub?gid=808922108&single=true&output=csv"

@st.cache_data(ttl=300) # 5분마다 데이터를 새로고침하여 실시간성을 유지합니다.
def load_data(url):
    # 상단 헤더 구조(2개 행)를 고려하여 두 번째 줄을 컬럼명으로 사용합니다.
    df = pd.read_csv(url, header=1)
    
    # 날짜 데이터 전처리
    df['등록 요청일자'] = pd.to_datetime(df['등록 요청일자'], errors='coerce')
    df['등록 완료 일자'] = pd.to_datetime(df['등록 완료 일자'], errors='coerce')
    
    # 결측치 처리 및 데이터 타입 변환
    df['리스트업 담당자'] = df['리스트업 담당자'].fillna('미배정')
    df['SKU'] = pd.to_numeric(df['SKU'], errors='coerce').fillna(0).astype(int)
    
    return df

try:
    df = load_data(CSV_URL)
except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    st.stop()

# ==========================================
# 3. 사이드바 필터링
# ==========================================
st.sidebar.header("🔍 대시보드 필터")

# 담당자 선택 필터
all_managers = ["전체"] + sorted(df['리스트업 담당자'].unique().tolist())
selected_manager = st.sidebar.selectbox("👨‍💻 리스트업 담당자 선택", all_managers)

# 날짜 범위 선택 필터 (등록 요청일자 기준)
min_date = df['등록 요청일자'].min().date() if pd.notnull(df['등록 요청일자'].min()) else datetime.today().date()
max_date = df['등록 요청일자'].max().date() if pd.notnull(df['등록 요청일자'].max()) else datetime.today().date()

date_range = st.sidebar.date_input(
    "조회 기간 선택",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# 데이터 필터링 적용
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = df[(df['등록 요청일자'].dt.date >= start_date) & (df['등록 요청일자'].dt.date <= end_date)]
else:
    filtered_df = df

if selected_manager != "전체":
    filtered_df = filtered_df[filtered_df['리스트업 담당자'] == selected_manager]

# ==========================================
# 4. 핵심 팔로잉 Dashboard (KPI)
# ==========================================
st.subheader(f"📌 {selected_manager} 성과 요약")

# 지표 계산
# 1) 전체 누적 SKU (날짜 필터와 관계없이 해당 담당자의 총 성과)
if selected_manager != "전체":
    cumulative_sku = df[df['리스트업 담당자'] == selected_manager]['SKU'].sum()
else:
    cumulative_sku = df['SKU'].sum()

# 2) 선택 기간 내 지표
period_sku = filtered_df['SKU'].sum()
brand_count = filtered_df['브랜드'].nunique()
request_count = len(filtered_df)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📦 담당자 총 누적 SKU", f"{cumulative_sku:,}")
with col2:
    st.metric("📅 선택 기간 SKU 합계", f"{period_sku:,}")
with col3:
    st.metric("🏢 요청 브랜드 수", f"{brand_count:,}")
with col4:
    st.metric("📝 등록 요청 건수", f"{request_count:,}")

st.markdown("---")

# ==========================================
# 5. 시각화 분석
# ==========================================
c1, c2 = st.columns(2)

with c1:
    st.subheader("📈 일자별 SKU 등록 추이")
    if not filtered_df.empty:
        daily_sku = filtered_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
        fig_line = px.line(daily_sku, x='등록 요청일자', y='SKU', markers=True, 
                           template="plotly_white", color_discrete_sequence=['#007BFF'])
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

with c2:
    st.subheader("📊 브랜드별 SKU 비중 (Top 10)")
    if not filtered_df.empty:
        brand_sku = filtered_df.groupby('브랜드')['SKU'].sum().reset_index().sort_values('SKU', ascending=False).head(10)
        fig_bar = px.bar(brand_sku, x='SKU', y='브랜드', orientation='h', 
                         color='SKU', color_continuous_scale='Blues')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

# ==========================================
# 6. 상세 데이터 로그
# ==========================================
st.subheader("📋 상세 데이터 리스트")
st.dataframe(filtered_df.sort_values('등록 요청일자', ascending=False), use_container_width=True)

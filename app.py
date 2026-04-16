import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# ==========================================
# 1. 페이지 설정 및 다크 테마 + 완벽 CSS 고정
# ==========================================
st.set_page_config(page_title="운영 로그 대시보드 | KREAM Famous", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, div:not([data-testid="stIcon"]), label {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    .stApp { background-color: #0E1117; }
    
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; }
    h1, h2, h3, h4 { color: #FFFFFF !important; font-weight: 700 !important; }
    
    /* 텍스트 겹침 완벽 방지 */
    .streamlit-expanderHeader span:contains("arrow_right"), 
    .streamlit-expanderHeader [data-testid="stIcon"] { display: none !important; }

    [data-testid="stExpander"] details summary p {
        margin-left: 1.5rem !important;
        color: #FFFFFF !important;
    }
    
    .streamlit-expanderHeader {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        padding-left: 15px !important;
    }
    
    .streamlit-expanderHeader svg { color: #FFFFFF !important; margin-right: 10px !important; }

    .author-text {
        text-align: right; color: #FFFFFF !important; font-size: 0.85rem; line-height: 1.4; opacity: 0.9;
    }
    .author-text b { color: #FFFFFF !important; font-weight: 700; }

    .stTabs [data-baseweb="tab"] { color: #A0A0A0; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #00D4FF !important; border-bottom: 2px solid #00D4FF !important; }
    hr { border-color: #30363D !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 상단 헤더
# ==========================================
header_left, header_right = st.columns([3, 1])
with header_left:
    st.title("📊 리스트업 운영 그룹 Dashboard")
with header_right:
    st.markdown(f"""
        <div class="author-text">
            Created & Maintained by <b>오홍석</b><br>
            운영 및 유지보완 담당
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 데이터 로드 (에러 방어 및 자동 감지)
# ==========================================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7DmLGZwUTOY36vcC1aBgxsPwciNa5nYOYyODgCAPGWN_hR_LF-WXiYsHEdwa9uapI_M610WKtdF3S/pub?gid=808922108&single=true&output=csv"
TARGET_MANAGERS = ['전현희', '유지윤', '손영우', '고희영', '오홍석']

COLOR_MAP = {
    '전현희': '#00D4FF', '유지윤': '#B554FF', '손영우': '#00FFA3',
    '고희영': '#FF5482', '오홍석': '#FFD166'
}

def hex_to_rgba(hex_str, opacity=0.2):
    hex_str = hex_str.lstrip('#')
    r, g, b = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {opacity})"

@st.cache_data(ttl=300)
def load_data(url):
    try:
        try:
            df = pd.read_csv(url, header=1)
            if '등록 요청일자' not in df.columns and '리스트업 담당자' not in df.columns:
                df = pd.read_csv(url, header=0)
        except ValueError:
            df = pd.read_csv(url, header=0)

        has_required_columns = any(col in df.columns for col in ['등록 요청일자', '리스트업 담당자', '주차'])
        if not has_required_columns:
            st.error("🚨 **[데이터 접근 오류]** 구글 시트 게시 권한을 확인해주세요.")
            return pd.DataFrame(), pd.DataFrame()
        
        # [1] 크롤링
        df_c = df.copy()
        df_c['등록 요청일자'] = pd.to_datetime(df_c['등록 요청일자'], errors='coerce')
        df_c['Month'] = df_c['등록 요청일자'].dt.strftime('%Y-%m')
        df_c['SKU'] = pd.to_numeric(df_c['SKU'], errors='coerce').fillna(0).astype(int)
        df_c['리스트업 담당자'] = df_c['리스트업 담당자'].astype(str).str.strip()
        df_c['주차'] = df_c['주차'].astype(str).str.strip()
        df_crawl = df_c[df_c['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()

        # [2] 벌크
        if df.shape[1] >= 21:
            df_b = df.iloc[:, 16:21].copy()
            df_b.dropna(how='all', inplace=True)
            df_b.columns = ['주차', '등록 요청일자', '브랜드', 'SKU', '리스트업 담당자']
            df_b['등록 요청일자'] = pd.to_datetime(df_b['등록 요청일자'], errors='coerce')
            df_b['Month'] = df_b['등록 요청일자'].dt.strftime('%Y-%m')
            df_b['SKU'] = pd.to_numeric(df_b['SKU'], errors='coerce').fillna(0).astype(int)
            df_b['리스트업 담당자'] = df_b['리스트업 담당자'].astype(str).str.strip()
            df_b['주차'] = df_b['주차'].astype(str).str.strip()
            df_bulk = df_b[df_b['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()
        else:
            df_bulk = pd.DataFrame(columns=['주차', '등록 요청일자', '브랜드', 'SKU', '리스트업 담당자', 'Month'])
            
        return df_crawl, df_bulk
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_crawl, df_bulk = load_data(CSV_URL)
if df_crawl.empty and df_bulk.empty: st.stop()

# ==========================================
# 4. 통합 성과 (크롤링/벌크 차트 분리)
# ==========================================
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()

c_date, _ = st.columns([2, 3])
with c_date:
    selected_date = st.date_input("📅 조회 기준일 선택", value=today_date)

target_month = selected_date.strftime('%Y-%m')
target_week = f"{selected_date.strftime('%y')}W{selected_date.isocalendar()[1]:02d}"

df_week_c, df_week_b = df_crawl[df_crawl['주차'] == target_week], df_bulk[df_bulk['주차'] == target_week]
df_month_c, df_month_b = df_crawl[df_crawl['Month'] == target_month], df_bulk[df_bulk['Month'] == target_month]
df_day_c, df_day_b = df_crawl[df_crawl['등록 요청일자'].dt.date == selected_date], df_bulk[df_bulk['등록 요청일자'].dt.date == selected_date]

st.markdown("### 🏆 팀 통합 성과 (Team Performance)")
t_tab_w, t_tab_m, t_tab_d = st.tabs([f"🎯 {target_week} 주차", f"📅 {target_month} 월간", f"⚡ {selected_date} 일간"])

def render_team_summary(target_df_c, target_df_b, label):
    c1, c2 = st.columns(2)
    c1.metric(f"🔍 {label} 크롤링 총합", f"{target_df_c['SKU'].sum():,} 개")
    c2.metric(f"📦 {label} 벌크작업 총합", f"{target_df_b['SKU'].sum():,} 개")
    
    if target_df_c.empty and target_df_b.empty:
        st.info("해당 기간의 작업 내역이 없습니다.")
        return

    # [수정] 1. 크롤링 성과 차트 (도넛 + 막대)
    if not target_df_c.empty:
        st.markdown(f"**[🔍 {label} 크롤링 상세]**")
        col1, col2 = st.columns(2)
        with col1:
            fig_pie_c = px.pie(target_df_c.groupby('리스트업 담당자')['SKU'].sum().reset_index(), 
                             values='SKU', names='리스트업 담당자', hole=0.4, template='plotly_dark',
                             color='리스트업 담당자', color_discrete_map=COLOR_MAP, title="크롤링 기여도")
            st.plotly_chart(fig_pie_c, use_container_width=True)
        with col2:
            top_brands_c = target_df_c.groupby('브랜드')['SKU'].sum().nlargest(7).index
            top_df_c = target_df_c[target_df_c['브랜드'].isin(top_brands_c)]
            bar_data_c = top_df_c.groupby(['브랜드', '리스트업 담당자'])['SKU'].sum().reset_index()
            fig_bar_c = px.bar(bar_data_c, y='브랜드', x='SKU', color='리스트업 담당자', 
                             orientation='h', template='plotly_dark', title="크롤링 탑 브랜드",
                             color_discrete_map=COLOR_MAP)
            fig_bar_c.update_layout(yaxis={'categoryorder':'total ascending'}, barmode='stack')
            st.plotly_chart(fig_bar_c, use_container_width=True)

    # [수정] 2. 벌크작업 성과 차트 (도넛 + 막대)
    if not target_df_b.empty:
        st.markdown(f"**[📦 {label} 벌크작업 상세]**")
        col3, col4 = st.columns(2)
        with col3:
            fig_pie_b = px.pie(target_df_b.groupby('리스트업 담당자')['SKU'].sum().reset_index(), 
                             values='SKU', names='리스트업 담당자', hole=0.4, template='plotly_dark',
                             color='리스트업 담당자', color_discrete_map=COLOR_MAP, title="벌크작업 기여도")
            st.plotly_chart(fig_pie_b, use_container_width=True)
        with col4:
            top_brands_b = target_df_b.groupby('브랜드')['SKU'].sum().nlargest(7).index
            top_df_b = target_df_b[target_df_b['브랜드'].isin(top_brands_b)]
            bar_data_b = top_df_b.groupby(['브랜드', '리스트업 담당자'])['SKU'].sum().reset_index()
            fig_bar_b = px.bar(bar_data_b, y='브랜드', x='SKU', color='리스트업 담당자', 
                             orientation='h', template='plotly_dark', title="벌크작업 탑 브랜드",
                             color_discrete_map=COLOR_MAP)
            fig_bar_b.update_layout(yaxis={'categoryorder':'total ascending'}, barmode='stack')
            st.plotly_chart(fig_bar_b, use_container_width=True)

with t_tab_w: render_team_summary(df_week_c, df_week_b, "주간")
with t_tab_m: render_team_summary(df_month_c, df_month_b, "월간")
with t_tab_d: render_team_summary(df_day_c, df_day_b, "일간")

st.markdown("---")

# ==========================================
# 5. 인원별 실시간 트래커 (가시성/정렬 완벽 해결)
# ==========================================
st.markdown("### ⚡ 인원별 실시간 트래커")
m_cols = st.columns(5)

for i, manager in enumerate(TARGET_MANAGERS):
    with m_cols[i]:
        st.markdown(f"#### 🧑‍💻 {manager}")
        m_tab_w, m_tab_m, m_tab_d = st.tabs(["주간", "월", "일"])
        
        def render_m_tab(df_c, df_b, p_label):
            c_data = df_c[df_c['리스트업 담당자'] == manager]
            b_data = df_b[df_b['리스트업 담당자'] == manager]
            
            c_sum = c_data['SKU'].sum() if not c_data.empty else 0
            b_sum = b_data['SKU'].sum() if not b_data.empty else 0
            
            if c_sum == 0 and b_sum == 0:
                st.metric("🔍 크롤링 실적", "-")
                st.metric("📦 벌크작업 실적", "-")
                st.caption("내역 없음")
                return

            # [수정] 크롤링: 세부 지표를 expander(클릭)로 숨겨 라인 정렬 확보
            if c_sum > 0:
                st.metric("🔍 크롤링 실적", f"{c_sum:,}")
                with st.expander("상세 브랜드 보기"):
                    st.dataframe(c_data.groupby('브랜드')['SKU'].sum().reset_index().sort_values('SKU', ascending=False), 
                                 hide_index=True, use_container_width=True)
            else:
                st.metric("🔍 크롤링 실적", "-")

            # [수정] 벌크작업: 세부 지표를 expander(클릭)로 숨겨 라인 정렬 확보
            if b_sum > 0:
                st.metric("📦 벌크작업 실적", f"{b_sum:,}")
                with st.expander("상세 브랜드 보기"):
                    st.dataframe(b_data.groupby('브랜드')['SKU'].sum().reset_index().sort_values('SKU', ascending=False), 
                                 hide_index=True, use_container_width=True)
            else:
                st.metric("📦 벌크작업 실적", "-")
        
        with m_tab_w: render_m_tab(df_week_c, df_week_b, "주간")
        with m_tab_m: render_m_tab(df_month_c, df_month_b, "월간")
        with m_tab_d: render_m_tab(df_day_c, df_day_b, "일간")

st.markdown("---")

# ==========================================
# 6. 담당자별 데이터 (크롤링 vs 벌크 탭 분리)
# ==========================================
st.markdown("## 🔍 담당자별 데이터")

def render_deep_dive(f_df, m_df, team_total, manager, p_choice, task_name):
    if m_df.empty:
        c1, c2, c3 = st.columns(3)
        for metric in ["기간 SKU", "브랜드 수", "팀 내 기여도"]: c1.metric(metric, "-") if metric == "기간 SKU" else c2.metric(metric, "-") if metric == "브랜드 수" else c3.metric(metric, "-")
        st.info(f"누적된 {task_name} 데이터가 없습니다.")
        return

    if f_df.empty:
        c1, c2, c3 = st.columns(3)
        for metric in ["기간 SKU", "브랜드 수", "팀 내 기여도"]: c1.metric(metric, "-") if metric == "기간 SKU" else c2.metric(metric, "-") if metric == "브랜드 수" else c3.metric(metric, "-")
        st.info("선택하신 기간의 데이터가 없습니다.")
        return

    contrib_str = f"{(f_df['SKU'].sum() / team_total * 100):.1f}%" if team_total > 0 else "0.0%"

    c1, c2, c3 = st.columns(3)
    c1.metric("기간 SKU", f"{f_df['SKU'].sum():,}")
    c2.metric("브랜드 수", f"{f_df['브랜드'].nunique():,}")
    c3.metric("팀 내 기여도", contrib_str)

    ch1, ch2 = st.columns(2)
    with ch1:
        if "일간" not in p_choice:
            t_data = f_df.groupby('등록 요청일자')['SKU'].sum().reset_index()
            fig = px.area(t_data, x='등록 요청일자', y='SKU', template='plotly_dark', title=f"{task_name} 처리 추이")
            fig.update_traces(line_color=COLOR_MAP[manager], fillcolor=hex_to_rgba(COLOR_MAP[manager], 0.2))
            st.plotly_chart(fig, use_container_width=True)
    with ch2:
        b_data = f_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(5, 'SKU')
        fig = px.pie(b_data, values='SKU', names='브랜드', hole=0.4, template='plotly_dark', title=f"{task_name} 탑 브랜드")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander(f"📑 {manager} {task_name} 상세 로그"):
        st.dataframe(f_df.sort_values('등록 요청일자', ascending=False), use_container_width=True, hide_index=True)

for manager in TARGET_MANAGERS:
    st.markdown(f"### 👤 {manager}")
    p_choice = st.radio("범위 선택:", ["전체 누적", f"{target_month} 월간", f"{target_week} 주간", f"{selected_date} 일간"], horizontal=True, key=f"r_{manager}")
    
    m_df_c = df_crawl[df_crawl['리스트업 담당자'] == manager]
    m_df_b = df_bulk[df_bulk['리스트업 담당자'] == manager]
    
    f_df_c, f_df_b = m_df_c.copy(), m_df_b.copy()
    team_tot_c, team_tot_b = 0, 0
    
    if "월간" in p_choice:
        f_df_c, f_df_b = m_df_c[m_df_c['Month'] == target_month], m_df_b[m_df_b['Month'] == target_month]
        team_tot_c, team_tot_b = df_month_c['SKU'].sum(), df_month_b['SKU'].sum()
    elif "주간" in p_choice:
        f_df_c, f_df_b = m_df_c[m_df_c['주차'] == target_week], m_df_b[m_df_b['주차'] == target_week]
        team_tot_c, team_tot_b = df_week_c['SKU'].sum(), df_week_b['SKU'].sum()
    elif "일간" in p_choice:
        f_df_c, f_df_b = m_df_c[m_df_c['등록 요청일자'].dt.date == selected_date], m_df_b[m_df_b['등록 요청일자'].dt.date == selected_date]
        team_tot_c, team_tot_b = df_day_c['SKU'].sum(), df_day_b['SKU'].sum()
    else:
        team_tot_c, team_tot_b = df_crawl['SKU'].sum(), df_bulk['SKU'].sum()

    tab_crawl, tab_bulk = st.tabs(["🔍 크롤링 작업", "📦 벌크 작업"])
    
    with tab_crawl: render_deep_dive(f_df_c, m_df_c, team_tot_c, manager, p_choice, "크롤링")
    with tab_bulk: render_deep_dive(f_df_b, m_df_b, team_tot_b, manager, p_choice, "벌크작업")
    
    st.markdown("---")

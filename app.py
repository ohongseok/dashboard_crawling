import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re
import pytz

# ==========================================
# 1. 페이지 설정 및 다크 테마 고정 (비율 최적화 포함)
# ==========================================
st.set_page_config(page_title="1P OPS DASHBOARD", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, div:not([data-testid="stIcon"]), label {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    .stApp { background-color: #0E1117; }
    
    /* 해상도 방어: 와이드 모니터에서 차트가 무한정 늘어나는 현상 방지 */
    .block-container {
        max-width: 1600px !important;
        margin: 0 auto !important;
        padding-top: 2rem !important;
    }
    
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; }
    h1, h2, h3, h4 { color: #FFFFFF !important; font-weight: 700 !important; }
    
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

    /* 글로벌 토글 라디오 버튼 스타일링 */
    div[data-testid="stRadio"] > div {
        background-color: #161B22;
        padding: 10px 20px;
        border-radius: 8px;
        border: 1px solid #30363D;
        display: inline-flex;
    }

    /* 제작자 텍스트 잘림 현상 방지 (margin-top 추가) */
    .author-text {
        text-align: right; 
        color: #FFFFFF !important; 
        font-size: 0.85rem; 
        line-height: 1.5; 
        opacity: 0.9;
        margin-top: 1.5rem; 
        padding-right: 5px;
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
    st.title("📊 1P OPS DASHBOARD")
with header_right:
    st.markdown(f"""
        <div class="author-text">
            Created & Maintained by <b>오홍석</b><br>
            운영 및 유지보완 담당
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 데이터 로드 (시트 확장 및 Q~U열 매핑 완벽 대응)
# ==========================================
CSV_URL = "https://docs.google.com/spreadsheets/d/1EAd3NlieMsCmx44PmazLjNscUEYHWLkj8rhcahznsog/export?format=csv&gid=808922108"
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
            df_raw = pd.read_csv(url, header=1, low_memory=False)
            if '등록 요청일자' not in df_raw.columns and '리스트업 담당자' not in df_raw.columns:
                df_raw = pd.read_csv(url, header=0, low_memory=False)
        except ValueError:
            df_raw = pd.read_csv(url, header=0, low_memory=False)

        # [1] 크롤링: 컬럼 이름 기반 추출 (시트에 열이 추가되어도 안전함)
        df_c = df_raw.copy()
        if '등록 요청일자' in df_c.columns:
            df_c['등록 요청일자'] = pd.to_datetime(df_c['등록 요청일자'], errors='coerce')
            df_c = df_c.dropna(subset=['등록 요청일자'])
            df_c['Month'] = df_c['등록 요청일자'].dt.strftime('%Y-%m')
        if 'SKU' in df_c.columns:
            df_c['SKU'] = pd.to_numeric(df_c['SKU'], errors='coerce').fillna(0).astype(int)
        if '리스트업 담당자' in df_c.columns:
            df_c['리스트업 담당자'] = df_c['리스트업 담당자'].astype(str).str.strip()
        if '주차' in df_c.columns:
            df_c['주차'] = df_c['주차'].astype(str).str.strip()
            
        # 필요한 담당자 필터링
        df_crawl = df_c[df_c['리스트업 담당자'].isin(TARGET_MANAGERS)].copy() if '리스트업 담당자' in df_c.columns else pd.DataFrame()

        # [2] 벌크: Q~U열 (인덱스 16~20) 고정 매핑
        df_b_base = pd.DataFrame(columns=['주차', '등록 요청일자', '브랜드', 'SKU', '리스트업 담당자'])
        # 크롤링 열이 추가되어도 16번째 인덱스부터는 벌크작업으로 안전하게 파싱
        if df_raw.shape[1] > 16:
            bulk_slice = df_raw.iloc[:, 16:21].copy()
            for i in range(5 - bulk_slice.shape[1]):
                bulk_slice[f'missing_{i}'] = None
            bulk_slice.columns = df_b_base.columns
            df_b = bulk_slice
        else:
            df_b = df_b_base.copy()

        df_b['등록 요청일자'] = pd.to_datetime(df_b['등록 요청일자'], errors='coerce')
        df_b = df_b.dropna(subset=['등록 요청일자']).copy()
        df_b['Month'] = df_b['등록 요청일자'].dt.strftime('%Y-%m')
        df_b['SKU'] = pd.to_numeric(df_b['SKU'], errors='coerce').fillna(0).astype(int)
        df_b['리스트업 담당자'] = df_b['리스트업 담당자'].astype(str).str.strip()
        df_b['주차'] = df_b['주차'].astype(str).str.strip()
        df_bulk = df_b[df_b['리스트업 담당자'].isin(TARGET_MANAGERS)].copy()
            
        return df_crawl, df_bulk
        
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        empty_df = pd.DataFrame(columns=['주차', '등록 요청일자', '브랜드', 'SKU', '리스트업 담당자', 'Month'])
        return empty_df.copy(), empty_df.copy()

df_crawl, df_bulk = load_data(CSV_URL)
if df_crawl.empty and df_bulk.empty: st.stop()

BASE_COLUMNS = ['주차', '등록 요청일자', '브랜드', 'SKU', '리스트업 담당자', 'Month']
RAW_DISPLAY_COLUMNS = BASE_COLUMNS + ['작업 구분']

def with_work_type(df, work_type):
    if df.empty:
        typed_df = pd.DataFrame(columns=BASE_COLUMNS + ['작업 구분'])
        return typed_df
    typed_df = df.copy()
    typed_df['작업 구분'] = work_type
    return typed_df

def combine_work_data(crawl_df, bulk_df):
    frames = []
    if not crawl_df.empty:
        frames.append(with_work_type(crawl_df, '크롤링'))
    if not bulk_df.empty:
        frames.append(with_work_type(bulk_df, '벌크'))
    if not frames:
        return pd.DataFrame(columns=BASE_COLUMNS + ['작업 구분'])
    return pd.concat(frames, ignore_index=True, sort=False)

df_total = combine_work_data(df_crawl, df_bulk)

def parse_week_label(week_label):
    match = re.search(r'(\d{2})W(\d{1,2})', str(week_label).strip())
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))

def add_week_sort_columns(df):
    if df.empty:
        return df.copy()
    result = df.copy()
    week_parts = result['주차'].apply(parse_week_label)
    result['_week_year'] = week_parts.apply(lambda value: value[0])
    result['_week_no'] = week_parts.apply(lambda value: value[1])
    return result

def filter_until_target_week(df, year_int, week_str):
    if df.empty:
        return df.copy()
    week_year, week_no = parse_week_label(week_str)
    result = add_week_sort_columns(df)
    result = result[result['등록 요청일자'].dt.year == year_int]
    if week_year is not None and week_no is not None:
        result = result[(result['_week_year'] == week_year) & (result['_week_no'] <= week_no)]
    return result

def build_work_pivot(df, index_cols):
    output_cols = index_cols + ['크롤링', '벌크', '크롤링+벌크']
    if df.empty:
        return pd.DataFrame(columns=output_cols)
    pivot_df = df.groupby(index_cols + ['작업 구분'])['SKU'].sum().unstack(fill_value=0).reset_index()
    for col in ['크롤링', '벌크']:
        if col not in pivot_df.columns:
            pivot_df[col] = 0
    pivot_df['크롤링+벌크'] = pivot_df['크롤링'] + pivot_df['벌크']
    return pivot_df[output_cols]

def raw_display_df(df):
    if df.empty:
        return pd.DataFrame(columns=RAW_DISPLAY_COLUMNS)
    visible_cols = [col for col in RAW_DISPLAY_COLUMNS if col in df.columns]
    display_df = df[visible_cols].copy()
    if '등록 요청일자' in display_df.columns:
        display_df['등록 요청일자'] = pd.to_datetime(
            display_df['등록 요청일자'], errors='coerce'
        ).dt.strftime('%Y-%m-%d')
    return display_df

def format_dates_for_display(df):
    display_df = df.copy()
    if '등록 요청일자' in display_df.columns:
        display_df['등록 요청일자'] = pd.to_datetime(
            display_df['등록 요청일자'], errors='coerce'
        ).dt.strftime('%Y-%m-%d')
    return display_df

# ==========================================
# 4. 통합 성과
# ==========================================
kst = pytz.timezone('Asia/Seoul')
today_date = datetime.now(kst).date()

c_date, _ = st.columns([2, 3])
with c_date:
    selected_date = st.date_input("📅 조회 기준일 선택", value=today_date)

target_year = selected_date.year
target_month = selected_date.strftime('%Y-%m')
target_week = f"{selected_date.strftime('%y')}W{selected_date.isocalendar()[1]:02d}"

def filter_by_date(df, date_obj, week_str, month_str, year_int):
    if df.empty:
        return df.copy(), df.copy(), df.copy(), df.copy()
    d_w = df[(df['주차'] == week_str) & (df['등록 요청일자'].dt.year == year_int)]
    d_m = df[df['Month'] == month_str]
    d_d = df[df['등록 요청일자'].dt.date == date_obj]
    d_y = df[df['등록 요청일자'].dt.year == year_int]
    return d_w, d_m, d_d, d_y

df_week_c, df_month_c, df_day_c, df_year_c = filter_by_date(df_crawl, selected_date, target_week, target_month, target_year)
df_week_b, df_month_b, df_day_b, df_year_b = filter_by_date(df_bulk, selected_date, target_week, target_month, target_year)
df_week_t, df_month_t, df_day_t, df_year_t = filter_by_date(df_total, selected_date, target_week, target_month, target_year)

st.markdown("### 🏆 팀 통합 성과 (Team Performance)")
t_tab_w, t_tab_m, t_tab_d, t_tab_y = st.tabs([f"🎯 {target_week} 주차", f"📅 {target_month} 월간", f"⚡ {selected_date} 일간", f"🏆 {target_year}년 누적"])

def render_team_summary(target_df_c, target_df_b, target_df_total, label):
    c1, c2, c3 = st.columns(3)
    c1.metric(f"🔍 {label} 크롤링 총합", f"{target_df_c['SKU'].sum() if not target_df_c.empty else 0:,} 개")
    c2.metric(f"📦 {label} 벌크작업 총합", f"{target_df_b['SKU'].sum() if not target_df_b.empty else 0:,} 개")
    c3.metric(f"🔗 {label} 크롤링+벌크 총합", f"{target_df_total['SKU'].sum() if not target_df_total.empty else 0:,} 개")
    
    if target_df_c.empty and target_df_b.empty and target_df_total.empty:
        st.info("해당 기간의 작업 내역이 없습니다.")
        return

    col1, col2 = st.columns(2)
    with col1:
        if not target_df_c.empty:
            fig_pie_c = px.pie(target_df_c.groupby('리스트업 담당자')['SKU'].sum().reset_index(), 
                             values='SKU', names='리스트업 담당자', hole=0.4, template='plotly_dark',
                             color='리스트업 담당자', color_discrete_map=COLOR_MAP, title=f"{label} 크롤링 기여도")
            fig_pie_c.update_layout(height=350)
            st.plotly_chart(fig_pie_c, use_container_width=True)
        if not target_df_b.empty:
            fig_pie_b = px.pie(target_df_b.groupby('리스트업 담당자')['SKU'].sum().reset_index(), 
                             values='SKU', names='리스트업 담당자', hole=0.4, template='plotly_dark',
                             color='리스트업 담당자', color_discrete_map=COLOR_MAP, title=f"{label} 벌크 기여도")
            fig_pie_b.update_layout(height=350)
            st.plotly_chart(fig_pie_b, use_container_width=True)
    with col2:
        if not target_df_c.empty:
            top_brands_c = target_df_c.groupby('브랜드')['SKU'].sum().nlargest(7).index
            top_df_c = target_df_c[target_df_c['브랜드'].isin(top_brands_c)]
            bar_data_c = top_df_c.groupby(['브랜드', '리스트업 담당자'])['SKU'].sum().reset_index()
            fig_bar_c = px.bar(bar_data_c, y='브랜드', x='SKU', color='리스트업 담당자', orientation='h', template='plotly_dark', 
                               title=f"{label} 크롤링 탑 브랜드", color_discrete_map=COLOR_MAP)
            fig_bar_c.update_layout(height=350, yaxis={'categoryorder':'total ascending'}, barmode='stack')
            st.plotly_chart(fig_bar_c, use_container_width=True)
        if not target_df_b.empty:
            top_brands_b = target_df_b.groupby('브랜드')['SKU'].sum().nlargest(7).index
            top_df_b = target_df_b[target_df_b['브랜드'].isin(top_brands_b)]
            bar_data_b = top_df_b.groupby(['브랜드', '리스트업 담당자'])['SKU'].sum().reset_index()
            fig_bar_b = px.bar(bar_data_b, y='브랜드', x='SKU', color='리스트업 담당자', orientation='h', template='plotly_dark', 
                               title=f"{label} 벌크 탑 브랜드", color_discrete_map=COLOR_MAP)
            fig_bar_b.update_layout(height=350, yaxis={'categoryorder':'total ascending'}, barmode='stack')
            st.plotly_chart(fig_bar_b, use_container_width=True)

    if not target_df_total.empty:
        st.markdown(f"#### 🔗 {label} 크롤링+벌크 작업")
        total_col1, total_col2 = st.columns(2)
        with total_col1:
            fig_pie_t = px.pie(target_df_total.groupby('리스트업 담당자')['SKU'].sum().reset_index(),
                             values='SKU', names='리스트업 담당자', hole=0.4, template='plotly_dark',
                             color='리스트업 담당자', color_discrete_map=COLOR_MAP, title=f"{label} 크롤링+벌크 기여도")
            fig_pie_t.update_layout(height=350)
            st.plotly_chart(fig_pie_t, use_container_width=True)
        with total_col2:
            top_brands_t = target_df_total.groupby('브랜드')['SKU'].sum().nlargest(7).index
            top_df_t = target_df_total[target_df_total['브랜드'].isin(top_brands_t)]
            bar_data_t = top_df_t.groupby(['브랜드', '리스트업 담당자'])['SKU'].sum().reset_index()
            fig_bar_t = px.bar(bar_data_t, y='브랜드', x='SKU', color='리스트업 담당자', orientation='h', template='plotly_dark',
                               title=f"{label} 크롤링+벌크 탑 브랜드", color_discrete_map=COLOR_MAP)
            fig_bar_t.update_layout(height=350, yaxis={'categoryorder':'total ascending'}, barmode='stack')
            st.plotly_chart(fig_bar_t, use_container_width=True)
        with st.expander(f"📊 {label} 크롤링+벌크 주차/브랜드 상세"):
            detail_cols = ['주차', '브랜드', '작업 구분']
            detail_df = target_df_total.groupby(detail_cols)['SKU'].sum().reset_index().sort_values(['주차', 'SKU'], ascending=[False, False])
            st.dataframe(detail_df, hide_index=True, use_container_width=True)

with t_tab_w: render_team_summary(df_week_c, df_week_b, df_week_t, "주간")
with t_tab_m: render_team_summary(df_month_c, df_month_b, df_month_t, "월간")
with t_tab_d: render_team_summary(df_day_c, df_day_b, df_day_t, "일간")
with t_tab_y: render_team_summary(df_year_c, df_year_b, df_year_t, f"{target_year}년")

st.markdown("---")

st.sidebar.header("인원별 상세 분석")
st.sidebar.caption("이름을 선택하면 해당 담당자의 작업 상세를 확인할 수 있습니다.")
selected_manager = st.sidebar.radio(
    "담당자 선택",
    TARGET_MANAGERS,
    index=0,
    key="selected_manager"
)

# ==========================================
# 5. 담당자별 데이터 (Deep Dive)
# ==========================================
st.markdown("## 🔍 담당자별 데이터")

def render_manager_period_summary(manager_df, manager, period_column, period_label, caption, key_prefix):
    if manager_df.empty:
        st.info(f"{manager} 담당자의 {period_label} 작업 데이터가 없습니다.")
        return

    period_df = manager_df.copy()
    if period_column == '등록 요청일자':
        period_df['기간'] = period_df[period_column].dt.strftime('%Y-%m-%d')
    else:
        period_df['기간'] = period_df[period_column].astype(str)

    period_pivot = build_work_pivot(period_df, ['기간'])
    brand_counts = (
        period_df.groupby('기간')['브랜드']
        .nunique()
        .reset_index(name='브랜드 수')
    )
    period_summary = period_pivot.merge(brand_counts, on='기간', how='left')
    if period_column == '주차':
        sort_df = period_summary.rename(columns={'기간': '주차'})
        sort_df = add_week_sort_columns(sort_df).sort_values(['_week_year', '_week_no'])
        period_summary = sort_df.rename(columns={'주차': '기간'}).drop(columns=['_week_year', '_week_no'], errors='ignore')
    else:
        period_summary = period_summary.sort_values('기간')
    period_summary = period_summary[['기간', '브랜드 수', '크롤링', '벌크', '크롤링+벌크']]

    st.caption(caption)
    period_options = period_summary['기간'].tolist()
    if len(period_options) > 1:
        period_chart_data = period_summary.melt(
            id_vars='기간',
            value_vars=['크롤링', '벌크'],
            var_name='작업 구분',
            value_name='SKU'
        )
        fig_period = px.bar(
            period_chart_data,
            x='기간',
            y='SKU',
            color='작업 구분',
            barmode='group',
            template='plotly_dark',
            color_discrete_map={'크롤링': '#38BDF8', '벌크': '#F59E0B'},
            title=f"{manager} {period_label} 작업 SKU"
        )
        fig_period.update_layout(
            height=320,
            legend_title_text='',
            bargap=0.55,
            bargroupgap=0.12
        )
        fig_period.update_xaxes(type='category', title=period_label)
        fig_period.update_traces(
            width=0.36,
            hovertemplate=f"{period_label}=%{{x}}<br>SKU=%{{y}}<extra></extra>"
        )
        st.plotly_chart(fig_period, use_container_width=True)
        st.dataframe(period_summary.rename(columns={'기간': period_label}), hide_index=True, use_container_width=True)
        selected_period = st.selectbox(
            f"상세를 볼 {period_label}",
            period_options,
            index=len(period_options) - 1,
            key=f"{key_prefix}_{manager}"
        )
    else:
        selected_period = period_options[0]
    selected_period_df = period_df[period_df['기간'] == selected_period].copy()
    selected_period_summary = period_summary[period_summary['기간'] == selected_period].iloc[0]

    st.markdown(f"#### {selected_period} 작업 상세")
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("브랜드 수", f"{int(selected_period_summary['브랜드 수']):,}개")
    metric2.metric("SKU 합계", f"{int(selected_period_summary['크롤링+벌크']):,}개")
    metric3.metric("크롤링 SKU", f"{int(selected_period_summary['크롤링']):,}개")
    metric4.metric("벌크 SKU", f"{int(selected_period_summary['벌크']):,}개")

    brand_summary = build_work_pivot(selected_period_df, ['브랜드']).sort_values('크롤링+벌크', ascending=True)
    work_summary = selected_period_df.groupby('작업 구분')['SKU'].sum().reset_index()
    chart_left, chart_right = st.columns(2)
    with chart_left:
        fig_work_mix = px.pie(
            work_summary,
            values='SKU',
            names='작업 구분',
            hole=0.52,
            template='plotly_dark',
            color='작업 구분',
            color_discrete_map={'크롤링': '#38BDF8', '벌크': '#F59E0B'},
            title=f"{selected_period} 작업 구성"
        )
        fig_work_mix.update_layout(height=340, legend_title_text='')
        st.plotly_chart(fig_work_mix, use_container_width=True)
    with chart_right:
        brand_chart_data = brand_summary.melt(
            id_vars='브랜드',
            value_vars=['크롤링', '벌크'],
            var_name='작업 구분',
            value_name='SKU'
        )
        fig_brand = px.bar(
            brand_chart_data,
            x='SKU',
            y='브랜드',
            color='작업 구분',
            orientation='h',
            barmode='stack',
            template='plotly_dark',
            color_discrete_map={'크롤링': '#38BDF8', '벌크': '#F59E0B'},
            category_orders={'브랜드': brand_summary['브랜드'].tolist()},
            title=f"{selected_period} 브랜드별 SKU"
        )
        fig_brand.update_layout(height=340, legend_title_text='')
        st.plotly_chart(fig_brand, use_container_width=True)

    st.markdown("**브랜드별 작업 요약**")
    st.dataframe(
        brand_summary.sort_values('크롤링+벌크', ascending=False),
        hide_index=True,
        use_container_width=True
    )
    with st.expander(f"📑 {selected_period} 원본 작업 로그"):
        st.dataframe(
            raw_display_df(selected_period_df).sort_values(
                ['작업 구분', '브랜드', '등록 요청일자'],
                ascending=[True, True, False]
            ),
            hide_index=True,
            use_container_width=True
        )

def render_manager_cumulative_summary(manager_df, manager):
    if manager_df.empty:
        st.info(f"{manager} 담당자의 누적 작업 데이터가 없습니다.")
        return

    crawl_sku = manager_df.loc[manager_df['작업 구분'] == '크롤링', 'SKU'].sum()
    bulk_sku = manager_df.loc[manager_df['작업 구분'] == '벌크', 'SKU'].sum()
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("브랜드 수", f"{manager_df['브랜드'].nunique():,}개")
    metric2.metric("SKU 누적", f"{manager_df['SKU'].sum():,}개")
    metric3.metric("크롤링 SKU", f"{crawl_sku:,}개")
    metric4.metric("벌크 SKU", f"{bulk_sku:,}개")

    brand_summary = build_work_pivot(manager_df, ['브랜드']).sort_values('크롤링+벌크', ascending=True)
    work_summary = manager_df.groupby('작업 구분')['SKU'].sum().reset_index()
    chart_left, chart_right = st.columns(2)
    with chart_left:
        fig_work_mix = px.pie(
            work_summary,
            values='SKU',
            names='작업 구분',
            hole=0.52,
            template='plotly_dark',
            color='작업 구분',
            color_discrete_map={'크롤링': '#38BDF8', '벌크': '#F59E0B'},
            title=f"{manager} 누적 작업 구성"
        )
        fig_work_mix.update_layout(height=340, legend_title_text='')
        st.plotly_chart(fig_work_mix, use_container_width=True)
    with chart_right:
        brand_chart_data = brand_summary.melt(
            id_vars='브랜드',
            value_vars=['크롤링', '벌크'],
            var_name='작업 구분',
            value_name='SKU'
        )
        fig_brand = px.bar(
            brand_chart_data,
            x='SKU',
            y='브랜드',
            color='작업 구분',
            orientation='h',
            barmode='stack',
            template='plotly_dark',
            color_discrete_map={'크롤링': '#38BDF8', '벌크': '#F59E0B'},
            category_orders={'브랜드': brand_summary['브랜드'].tolist()},
            title=f"{manager} 누적 브랜드별 SKU"
        )
        fig_brand.update_layout(height=340, legend_title_text='')
        st.plotly_chart(fig_brand, use_container_width=True)

    st.markdown("**누적 브랜드별 작업 요약**")
    st.dataframe(
        brand_summary.sort_values('크롤링+벌크', ascending=False),
        hide_index=True,
        use_container_width=True
    )
    with st.expander("📑 누적 원본 작업 로그"):
        st.dataframe(
            raw_display_df(manager_df).sort_values(
                ['등록 요청일자', '작업 구분', '브랜드'],
                ascending=[False, True, True]
            ),
            hide_index=True,
            use_container_width=True
        )

def render_deep_dive(f_df, m_df, team_total, manager, p_choice, task_name):
    if m_df.empty or f_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("기간 SKU", "-")
        c2.metric("브랜드 수", "-")
        c3.metric("팀 내 기여도", "-")
        st.info(f"{task_name} 데이터가 없습니다.")
        return

    contrib_str = f"{(f_df['SKU'].sum() / team_total * 100):.1f}%" if team_total > 0 else "0.0%"
    c1, c2, c3 = st.columns(3)
    c1.metric("기간 SKU", f"{f_df['SKU'].sum():,}")
    c2.metric("브랜드 수", f"{f_df['브랜드'].nunique():,}")
    c3.metric("팀 내 기여도", contrib_str)

    ch1, ch2 = st.columns(2)
    with ch1:
        if "일간" not in p_choice:
            t_data = f_df.groupby('등록 요청일자')['SKU'].sum().reset_index().sort_values('등록 요청일자')
            t_data['날짜'] = t_data['등록 요청일자'].dt.strftime('%Y-%m-%d')
            fig = px.area(t_data, x='날짜', y='SKU', template='plotly_dark', title=f"{task_name} 처리 추이")
            fig.update_layout(height=350, xaxis_title='등록요청일자')
            fig.update_xaxes(type='category')
            fig.update_traces(hovertemplate='등록요청일자=%{x}<br>SKU=%{y}<extra></extra>')
            fig.update_traces(line_color=COLOR_MAP[manager], fillcolor=hex_to_rgba(COLOR_MAP[manager], 0.2))
            st.plotly_chart(fig, use_container_width=True)
    with ch2:
        b_data = f_df.groupby('브랜드')['SKU'].sum().reset_index().nlargest(5, 'SKU')
        fig = px.pie(b_data, values='SKU', names='브랜드', hole=0.4, template='plotly_dark', title=f"{task_name} 탑 브랜드")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    with st.expander(f"📑 {manager} {task_name} 상세 로그"):
        detail_cols = ['주차', '브랜드']
        if '작업 구분' in f_df.columns:
            detail_cols.append('작업 구분')
        brand_detail = f_df.groupby(detail_cols)['SKU'].sum().reset_index().sort_values(['주차', 'SKU'], ascending=[False, False])
        st.markdown("**주차/브랜드별 요약**")
        st.dataframe(brand_detail, use_container_width=True, hide_index=True)
        st.markdown("**원본 로그**")
        st.dataframe(
            format_dates_for_display(f_df.sort_values('등록 요청일자', ascending=False)),
            use_container_width=True,
            hide_index=True
        )

for manager in [selected_manager]:
    st.markdown(f"### 👨‍💻 {manager}")
    period_choice = st.radio(
        "조회 범위",
        [f"{target_week} 주간", f"{target_month} 월간", f"{selected_date} 일간", f"{target_year}년 누적"],
        horizontal=True,
        key=f"period_{manager}",
        label_visibility="collapsed"
    )
    
    m_df_c = df_crawl[df_crawl['리스트업 담당자'] == manager] if not df_crawl.empty else df_crawl.copy()
    m_df_b = df_bulk[df_bulk['리스트업 담당자'] == manager] if not df_bulk.empty else df_bulk.copy()
    m_df_t = df_total[df_total['리스트업 담당자'] == manager] if not df_total.empty else df_total.copy()
    
    f_week_c, f_month_c, f_day_c, f_year_c = filter_by_date(m_df_c, selected_date, target_week, target_month, target_year)
    f_week_b, f_month_b, f_day_b, f_year_b = filter_by_date(m_df_b, selected_date, target_week, target_month, target_year)
    f_week_t, f_month_t, f_day_t, f_year_t = filter_by_date(m_df_t, selected_date, target_week, target_month, target_year)

    manager_year_to_date = m_df_t[
        (m_df_t['등록 요청일자'].dt.year == target_year) &
        (m_df_t['등록 요청일자'].dt.date <= selected_date)
    ].copy()
    manager_month_to_date = manager_year_to_date[manager_year_to_date['Month'] == target_month].copy()
    manager_year_to_date_c = m_df_c[
        (m_df_c['등록 요청일자'].dt.year == target_year) &
        (m_df_c['등록 요청일자'].dt.date <= selected_date)
    ].copy()
    manager_year_to_date_b = m_df_b[
        (m_df_b['등록 요청일자'].dt.year == target_year) &
        (m_df_b['등록 요청일자'].dt.date <= selected_date)
    ].copy()

    team_year_to_date_c = df_year_c[df_year_c['등록 요청일자'].dt.date <= selected_date]
    team_year_to_date_b = df_year_b[df_year_b['등록 요청일자'].dt.date <= selected_date]
    team_year_to_date_t = df_year_t[df_year_t['등록 요청일자'].dt.date <= selected_date]

    if "월간" in period_choice:
        cur_c, cur_b, cur_t = f_month_c, f_month_b, f_month_t
        tot_c = df_month_c['SKU'].sum() if not df_month_c.empty else 0
        tot_b = df_month_b['SKU'].sum() if not df_month_b.empty else 0
        tot_t = df_month_t['SKU'].sum() if not df_month_t.empty else 0
        render_manager_period_summary(
            f_month_t,
            manager,
            'Month',
            '월',
            f"{target_month}의 작업입니다.",
            'monthly_detail'
        )
    elif "주간" in period_choice:
        cur_c, cur_b, cur_t = f_week_c, f_week_b, f_week_t
        tot_c = df_week_c['SKU'].sum() if not df_week_c.empty else 0
        tot_b = df_week_b['SKU'].sum() if not df_week_b.empty else 0
        tot_t = df_week_t['SKU'].sum() if not df_week_t.empty else 0
        render_manager_period_summary(
            f_week_t,
            manager,
            '주차',
            '주차',
            f"{target_week}의 작업입니다.",
            'weekly_detail'
        )
    elif "일간" in period_choice:
        cur_c, cur_b, cur_t = f_day_c, f_day_b, f_day_t
        tot_c = df_day_c['SKU'].sum() if not df_day_c.empty else 0
        tot_b = df_day_b['SKU'].sum() if not df_day_b.empty else 0
        tot_t = df_day_t['SKU'].sum() if not df_day_t.empty else 0
        render_manager_period_summary(
            f_day_t,
            manager,
            '등록 요청일자',
            '일자',
            f"{selected_date}의 작업입니다.",
            'daily_detail'
        )
    else:
        cur_c, cur_b, cur_t = manager_year_to_date_c, manager_year_to_date_b, manager_year_to_date
        tot_c = team_year_to_date_c['SKU'].sum() if not team_year_to_date_c.empty else 0
        tot_b = team_year_to_date_b['SKU'].sum() if not team_year_to_date_b.empty else 0
        tot_t = team_year_to_date_t['SKU'].sum() if not team_year_to_date_t.empty else 0
        st.caption(f"{target_year}년 1월 1일부터 {selected_date}까지의 누적 작업입니다.")
        render_manager_cumulative_summary(manager_year_to_date, manager)

    st.markdown("#### 작업 유형별 상세")
    tab_c, tab_b, tab_t = st.tabs(["🔍 크롤링", "📦 벌크", "🔗 크롤링+벌크"])
    with tab_c: render_deep_dive(cur_c, m_df_c, tot_c, manager, period_choice, "크롤링")
    with tab_b: render_deep_dive(cur_b, m_df_b, tot_b, manager, period_choice, "벌크")
    with tab_t: render_deep_dive(cur_t, m_df_t, tot_t, manager, period_choice, "크롤링+벌크")
    st.markdown("---")

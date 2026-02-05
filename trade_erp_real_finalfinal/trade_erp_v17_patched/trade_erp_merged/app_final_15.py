# -*- coding: utf-8 -*-

import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta, date
import sys, os, re, json, logging, pickle, base64, html
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any, Optional, Tuple

# 시스템 경로 설정
sys.path.insert(0, str(Path(__file__).parent))

# 모듈 임포트 (기존 유지)
try:
    from config.settings import settings, RAW_DATA_DIR, DATA_DIR
    from modules.auth import authenticate, init_default_admin
except ImportError:
        # 모듈 없을 시 더미 처리 (실행 에러 방지용)
    def authenticate(u, p): return True, {"name": "Admin", "role": "admin"}
    def init_default_admin(): pass
    class Settings:
        def validate_api_keys(self): return {}
from openai import OpenAI

# 신규: 캐시 기반 마스터 데이터 관리
from modules.master_data.column_mapper import ColumnMapper
from modules.master_data.cached_manager import CachedMasterDataManager
from modules.master_data.sync_scheduler import start_periodic_sync
from modules.master_data.file_watcher import start_file_watcher

st.set_page_config(page_title="자동 eDay", page_icon="💼", layout="wide")
logger = logging.getLogger(__name__)

# 커스텀 CSS 적용
def apply_custom_css():
    st.markdown("""
    <style>
    /* 폰트 정의 */
    @font-face {
        font-family: 'AtoZ';
        src: url('./trade_erp_merged/font/atoz_4.ttf') format('truetype');
    }
    
    /* 메인 콘텐츠에만 폰트 적용 */
    .main, .block-container, 
    h1, h2, h3, h4, h5, h6, p, 
    label, input, textarea, select, 
    .stMarkdown, .stText {
        font-family: 'AtoZ', sans-serif !important;
    }
    
    /* 사이드바 텍스트에만 폰트 적용 (아이콘 제외) */
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1 {
        font-family: 'AtoZ', sans-serif !important;
        color: #ffffff !important;
    }
    
    /* 배경화면: 하늘색 */
    .stApp {
        background-color: #dfe6eb !important;
    }
    
    /* 상단바: 흰색 */
    header[data-testid="stHeader"] {
        background-color: #ffffff !important;
    }
                
    /* 사이드바: 네이비색 */
    [data-testid="stSidebar"] {
        background-color: #2e6185 !important;
    }
    
    /* 사이드바 버튼 스타일 */
    [data-testid="stSidebar"] .stButton button {
        font-family: 'AtoZ', sans-serif !important;
        background-color: transparent !important;
        border: 2px transparent !important;
        color: #ffffff !important;
        width: 100% !important;
        margin: 1px 0 !important;
        padding: 0.5rem 1rem !important;
        border-radius: 5px !important;
        transition: all 0.3s ease !important;
    }
    
    /* 사이드바 버튼 호버 효과 - background는 버튼에만, color는 전체에 */
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: rgba(220, 228, 230, 0.8) !important;
        border-color: rgba(255, 255, 255, 1) !important;
    }

    [data-testid="stSidebar"] .stButton button:hover,
    [data-testid="stSidebar"] .stButton button:hover * {
        color: #000000 !important;
    }

    /* 선택된 버튼 스타일 - background는 버튼에만, color는 전체에 */
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: #dfe6eb !important;
        border-color: #dfe6eb !important;
        font-weight: bold !important;
    }

    [data-testid="stSidebar"] .stButton button[kind="primary"],
    [data-testid="stSidebar"] .stButton button[kind="primary"] * {
        color: #000000 !important;
    }
    
    /* 메인 콘텐츠 영역 배경 */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 10px !important;
        padding: 2rem !important;
        margin: 1rem !important;
    }
    /* 메인 콘텐츠 primary 버튼 색상 - 사이드바와 동일 (네이비) */

    /* 기본 상태 */
    .stButton > button[kind="primary"],
    .stButton button[kind="primary"],
    button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primary"],
    div[data-testid="stButton"] > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"],
    .stFormSubmitButton button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stFormSubmitButton"] button[kind="primary"] {
        background-color: #2e6185 !important;   /* 배경색: 네이비 */
        border-color: #2e6185 !important;       /* 테두리: 네이비 */
        color: #ffffff !important;              /* 글자색: 흰색 */
    }

    /* 호버 상태 (마우스 올렸을 때) */
    .stButton > button[kind="primary"]:hover,
    .stButton button[kind="primary"]:hover,
    button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover,
    div[data-testid="stButton"] > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primary"]:hover,
    .stFormSubmitButton button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
        background-color: #245170 !important;   /* 더 어두운 네이비 */
        border-color: #245170 !important;
    }
    /* ========== 대시보드 카드 스타일 ========== */
    .dashboard-card {
        background-color: rgba(255, 255, 255, 0.8) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.5rem !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    }
    
    /* 대시보드 컬럼 간격 조정 */
    .main [data-testid="column"] {
        padding-left: 1px !important;
        padding-right: 1px !important;
    }
    
    /* 환율 추이/계산기만 카드 스타일 (메트릭은 제외) */
    .main [data-testid="stHorizontalBlock"]:not(:has([data-testid="stMetric"])) > div[data-testid="column"] {
        background-color: rgba(255, 255, 255, 0.8) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        margin-bottom: 0 !important;
    }
    
    /* 개별 메트릭 카드 스타일 - 더 단순한 선택자 */
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.8) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        min-height: 100px !important;
    }
    
    /* 메트릭 라벨 스타일 */
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #666 !important;
    }
    
    /* 메트릭 값 스타일 */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        color: #1a1a1a !important;
    }
    
    /* 메트릭 델타 스타일 */
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }
    
    /* ========== 메인보드 모든 버튼 색깔 통일 ========== */
    .main .stButton button {
        background-color: #2e6185 !important;
        color: white !important;
        border: 2px solid #2e6185 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    /* 버튼 호버 효과 */
    .main .stButton button:hover {
        background-color: #1e4a66 !important;
        border-color: #1e4a66 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    }
    
    /* Primary 버튼 (저장, 삭제 등) */
    .main .stButton button[kind="primary"] {
        background-color: #e74c3c !important;
        border-color: #e74c3c !important;
    }
    
    .main .stButton button[kind="primary"]:hover {
        background-color: #c0392b !important;
        border-color: #c0392b !important;
    }
    
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# 글로벌: HS 엑셀 경로 및 OpenAI 클라이언트
# ============================================================
# 데이터 경로 설정
HS_EXCEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "data", "raw",
    "hscode.xlsx"
)

# Open AI 클라이언트
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass  # secrets.toml 파일이 없어도 계속 진행

client = OpenAI(api_key=api_key) if api_key else None

# =================================================================
# 헬퍼 함수: OpenAI 기반 스마트 필드 매칭
# =================================================================
@st.cache_data(ttl=3600)
def _get_field_mapping(data_keys: tuple) -> dict:
    """OpenAI를 사용해 데이터 키와 표준 필드명 매핑 생성"""
    if not client:
        return {}

    standard_fields = [
        "hs_code", "payment_terms", "bl_number", "item_name", "exporter_name",
        "importer_name", "currency", "quantity", "unit_price", "incoterms",
        "origin_country", "vessel_name", "tariff_amount", "item_value"
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Match these data keys to standard field names based on similarity.
Data keys: {list(data_keys)}
Standard fields: {standard_fields}

Return ONLY a JSON object mapping data_key -> standard_field for matches with high similarity.
Example: {{"hscode": "hs_code", "bl_no": "bl_number"}}
Only include keys that have a clear match. Return empty {{}} if no matches."""
            }],
            temperature=0,
            max_tokens=500
        )
        import json
        result = response.choices[0].message.content.strip()
        # JSON 파싱 시 코드블록 제거
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result)
    except:
        return {}

def smart_get(data: dict, field: str, default=''):
    """스마트 필드 조회 - 직접 매칭 후 유사 필드 매칭"""
    # 1. 직접 매칭
    if field in data and data[field]:
        return data[field]

    # 2. 캐시된 매핑으로 유사 필드 찾기
    mapping = _get_field_mapping(tuple(data.keys()))
    for data_key, std_field in mapping.items():
        if std_field == field and data_key in data and data[data_key]:
            return data[data_key]

    return default

# =================================================================
# 헬퍼 함수 2: 엑셀에서 HS Code 매칭 (스코어링)
# =================================================================
@st.cache_data
def load_hs_excel(filepath):
    """
    'hscode.xlsx' 파일을 로드합니다.
    시트별(HS4단위, HS6단위, HS8단위(7,9포함), HS10단위)로 나누어진 데이터를 읽어 하나로 통합합니다.
    """
    if not os.path.exists(filepath):
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(filepath)
        dfs = []
        
        # 로드할 시트 키워드 정의 (8단위 시트 추가: 7,8,9단위 포함)
        target_sheets = {
            "4단위": 4,
            "6단위": 6,
            "8단위": 8,  # 7, 8, 9단위 포함
            "10단위": 10
        }

        for sheet_name in xls.sheet_names:
            matched_len = None
            for key, length in target_sheets.items():
                if key in sheet_name:
                    matched_len = length
                    break
            
            if matched_len:
                # 모든 데이터를 문자열로 로드
                df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str)
                
                # 컬럼명 매핑 (유연하게 처리)
                rename_map = {}
                for col in df.columns:
                    c = str(col).strip().replace(" ", "").replace("\n", "")
                    
                    if "영문" in c:
                        rename_map[col] = "영문품목명"
                    elif "한글" in c:
                        rename_map[col] = "한글품목명"
                    elif "품목명" in c: 
                        rename_map[col] = "한글품목명"
                    elif ("HS" in c or "부호" in c or "코드" in c) and "성질" not in c:
                        rename_map[col] = "HS부호"
                
                df = df.rename(columns=rename_map)
                
                # 중복 컬럼 제거 (매핑 오류 방지)
                df = df.loc[:, ~df.columns.duplicated()]
                
                # 필수 컬럼 확인
                if "HS부호" in df.columns and "한글품목명" in df.columns:
                    # 결측치 처리 및 문자열 변환
                    df["HS부호"] = df["HS부호"].fillna("").astype(str).str.strip()
                    df["한글품목명"] = df["한글품목명"].fillna("").astype(str).str.strip()
                    
                    # 코드 길이 컬럼 (실제 코드 길이 기준)
                    df["code_len"] = df["HS부호"].str.len()
                    
                    # 검색용 정규화 컬럼
                    df["품목명_norm"] = df["한글품목명"].str.replace(" ", "")
                    
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        master_df = pd.concat(dfs, ignore_index=True)
        master_df.drop_duplicates(subset=["HS부호"], inplace=True)
        
        return master_df

    except Exception as e:
        print(f"데이터 로드 에러: {e}")
        return pd.DataFrame()

# 전역 데이터 로드
hs_df = load_hs_excel(HS_EXCEL_PATH)


# =================================================================
# 헬퍼 함수 3: 환율 데이터 생성 (샘플 데이터)
# =================================================================
def get_exchange_rate_data(days=30):
    """
    yfinance를 사용하여 실제 환율 데이터 가져오기
    실패 시 현재 환율 기준 fallback 데이터 제공
    
    Parameters:
    - days: 조회할 일수 (30, 365, 1825(5년), 3650(10년))
    """
    from datetime import datetime, timedelta
    import pandas as pd
    import numpy as np
    
    try:
        import yfinance as yf
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 환율 심볼 (Yahoo Finance)
        symbols = {
            'USD': 'USDKRW=X',
            'JPY': 'JPYKRW=X',
            'CNY': 'CNYKRW=X',
            'EUR': 'EURKRW=X',
            'GBP': 'GBPKRW=X'
        }
        
        result_data = []
        
        # 각 통화별 데이터 다운로드
        for currency, symbol in symbols.items():
            try:
                data = yf.download(symbol, start=start_date, end=end_date, progress=False)
                if not data.empty:
                    temp_df = pd.DataFrame({
                        'date': data.index,
                        'currency': currency,
                        'rate': data['Close'].values
                    })
                    result_data.append(temp_df)
            except:
                continue
        
        if result_data:
            # 데이터 병합
            combined = pd.concat(result_data, ignore_index=True)
            df = combined.pivot(index='date', columns='currency', values='rate').reset_index()
            
            # JPY는 100엔 기준으로 변환
            if 'JPY' in df.columns:
                df['JPY'] = df['JPY'] * 100
            
            # 결측치 채우기 (주말/공휴일)
            for col in ['USD', 'JPY', 'CNY', 'EUR', 'GBP']:
                if col in df.columns:
                    df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
            
            return df
        else:
            raise Exception("데이터를 가져올 수 없습니다")
    
    except Exception as e:
        # Fallback: 현재 실제 환율 기준 생성
        print(f"환율 API 오류 ({e}). Fallback 데이터를 사용합니다.")
        
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        
        # 2025년 2월 3일 기준 실제 환율
        current_rates = {
            'USD': 1355.48,
            'JPY': 1029.51,  # 100엔 기준
            'CNY': 194.02,
            'EUR': 1527.44,
            'GBP': 1772.27
        }
        
        np.random.seed(42)
        data = {'date': dates}
        
        for currency, current_rate in current_rates.items():
            # 기간에 따른 추세 생성
            if days <= 30:
                # 1개월: 약간의 변동
                trend = np.linspace(current_rate * 0.98, current_rate, days)
                volatility_scale = 0.005
            elif days <= 365:
                # 1년: 중간 변동
                trend = np.linspace(current_rate * 0.95, current_rate, days)
                volatility_scale = 0.008
            else:
                # 장기: 큰 변동
                trend = np.linspace(current_rate * 0.90, current_rate, days)
                volatility_scale = 0.01
            
            # 통화별 변동성
            volatility = np.random.randn(days) * current_rate * volatility_scale
            
            # 계절성 추가
            seasonal = np.sin(np.linspace(0, days/365 * 2 * np.pi, days)) * (current_rate * 0.01)
            
            rates = trend + volatility + seasonal
            
            # 마지막 값은 정확히 현재 환율
            rates[-1] = current_rate
            
            data[currency] = rates
        
        df = pd.DataFrame(data)
        
        # 음수 방지
        for col in ['USD', 'JPY', 'CNY', 'EUR', 'GBP']:
            df[col] = df[col].clip(lower=0)
        
        return df

# =================================================================
# 3. 로직 헬퍼 함수 ('기타' 처리 및 AI)
# =================================================================
def get_parent_code(code):
    """HS코드의 직계 상위 코드를 반환"""
    if len(code) >= 7: # 10단위 -> 6단위
        return code[:6]
    elif len(code) >= 5: # 6단위 -> 4단위
        return code[:4]
    return None

def resolve_description(row, full_df, parent_desc_cache=None):
    """
    [롤백 반영] '기타' 항목의 경우에도 상위 설명을 조합하지 않고
    엑셀에 저장된 한글품목명을 그대로 반환합니다.
    """
    return row['한글품목명']

def search_candidates_by_ai(keyword):
    """
    [v3.0] 스마트 검색 — 키워드/HS코드 통합 처리
    """
    try:
        from modules.hs_code.search import full_search
        result = full_search(keyword, max_results=3)
        return result
    except Exception as e:
        st.error(f"검색 중 오류 발생: {e}")
        return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0, 'ranking': None}

# =================================================================
# 헬퍼 함수 4: 수입/수출 실적 데이터 생성 (PAGE2 연동)
# =================================================================
def get_trade_performance_data():
    """
    월별 거래 실적 데이터 생성 (최근 12개월)
    - trade_erp_master_template.xlsx의 PAGE1_DATA에서 데이터 로드
    - PAGE2_VIEW 스타일 집계 수행
    """
    from modules.master_data import load_master_data
    
    try:
        # 마스터 데이터 로드 (PAGE1_DATA)
        df = load_master_data()
        
        if df.empty:
            raise Exception("마스터 데이터가 비어있습니다")
        
        # 날짜 컬럼 확인 및 변환 (PAGE1_DATA: trade_date)
        date_column = None
        for col in ['trade_date', 'date', 'created_at', 'updated_at', 'created_date']:
            if col in df.columns:
                date_column = col
                break
        
        if date_column is None:
            raise Exception("날짜 컬럼을 찾을 수 없습니다")
        
        # 날짜 형식 변환
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        df = df.dropna(subset=[date_column])
        
        # 최근 12개월 필터링
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        df = df[df[date_column] >= start_date]
        
        # 월별 그룹화
        df['month'] = df[date_column].dt.to_period('M').dt.to_timestamp()
        
        # 금액 컬럼 확인 (PAGE1_DATA: line_amount)
        amount_column = None
        for col in ['line_amount', 'amount', 'item_value', 'trade_amount']:
            if col in df.columns:
                amount_column = col
                break
        
        if amount_column is None:
            raise Exception("금액 컬럼을 찾을 수 없습니다")
        
        df[amount_column] = pd.to_numeric(df[amount_column], errors='coerce').fillna(0)
        
        # trade_type 컬럼 확인 (PAGE1_DATA: direction)
        type_column = None
        for col in ['trade_type', 'direction']:
            if col in df.columns:
                type_column = col
                break
        
        if type_column is None:
            raise Exception("거래유형 컬럼을 찾을 수 없습니다")
        
        # 수입/수출 값 정규화
        df['_trade_type'] = df[type_column].apply(
            lambda x: 'import' if x in ['import', '수입'] else ('export' if x in ['export', '수출'] else x)
        )
        
        # 수입/수출별 집계
        monthly_data = df.groupby(['month', '_trade_type'])[amount_column].sum().unstack(fill_value=0)
        monthly_data = monthly_data.reset_index()
        
        # 컬럼명 정리
        if 'import' not in monthly_data.columns:
            monthly_data['import'] = 0
        if 'export' not in monthly_data.columns:
            monthly_data['export'] = 0
        
        # 최근 12개월 전체 월 생성
        all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
        result_df = pd.DataFrame({'month': all_months})
        
        # 데이터 병합
        result_df = result_df.merge(monthly_data[['month', 'import', 'export']], on='month', how='left')
        result_df['import'] = result_df['import'].fillna(0)
        result_df['export'] = result_df['export'].fillna(0)
        
        return result_df
        
    except Exception as e:
        print(f"거래 실적 데이터 로드 실패: {e}")
        
        # Fallback: 더미 데이터 생성
        from datetime import datetime, timedelta
        import pandas as pd
        import numpy as np
        
        end_date = datetime.now()
        months = pd.date_range(end=end_date, periods=12, freq='MS')
        
        np.random.seed(42)
        
        data = {
            'month': months,
            'import': np.random.randint(50000000, 150000000, size=12),
            'export': np.random.randint(80000000, 200000000, size=12)
        }
        
        return pd.DataFrame(data)
# ==================================================================
# 관세율 관련 상수 및 함수 (app_docu.py에서 가져옴)
# ==================================================================

TARIFF_KIND_MAP = {
    'A':'기본관세','U':'특혜(WTO양허)','W':'WTO협정','P':'잠정세율','F':'FTA','C':'조정관세',
    'E':'APTA(아태무역)','L':'최빈국특혜','R':'보복관세','D':'덤핑방지관세',
    'G':'긴급관세(세이프가드)','T':'농긴급관세','I':'국제협력관세',
    'B':'잠정세율','H':'할당관세','S':'계절관세','Q':'상계관세',
}

FTA_CODE_TO_NAME = {
    "FAS":"한-아세안","FAU":"한-호주","FCA":"한-캐나다","FCE":"한-중미",
    "FCL":"한-칠레","FCN":"한-중국","FCO":"한-콜롬비아","FEF":"한-EFTA",
    "FEU":"한-EU","FGB":"한-영국","FID":"한-인도네시아","FIL":"한-이스라엘",
    "FIN":"한-인도","FKH":"한-캄보디아","FNZ":"한-뉴질랜드","FPE":"한-페루",
    "FPH":"한-필리핀","FRC":"RCEP","FSG":"한-싱가포르","FTR":"한-터키",
    "FUS":"한-미국","FVN":"한-베트남",
}

FTA_COUNTRIES = {
    "FCL":["CL"],"FSG":["SG"],"FEF":["CH","NO","IS","LI"],
    "FAS":["BN","KH","ID","LA","MY","MM","PH","SG","TH","VN"],"FIN":["IN"],
    "FEU":["AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"],
    "FPE":["PE"],"FUS":["US"],"FTR":["TR"],"FAU":["AU"],"FCA":["CA"],
    "FCN":["CN"],"FNZ":["NZ"],"FVN":["VN"],"FCO":["CO"],
    "FCE":["CR","SV","HN","NI","PA"],"FGB":["GB"],
    "FRC":["AU","BN","KH","CN","ID","JP","LA","MY","MM","NZ","PH","SG","TH","VN"],
    "FIL":["IL"],"FKH":["KH"],"FID":["ID"],"FPH":["PH"],
}

COUNTRY_TO_FTA: Dict[str, List[str]] = {}
for _fc, _cs in FTA_COUNTRIES.items():
    for _c in _cs:
        COUNTRY_TO_FTA.setdefault(_c, []).append(_fc)

MAJOR_COUNTRIES = {
    "전체 (Global MIN)":"",
    "🇺🇸 미국":"US","🇨🇳 중국":"CN","🇯🇵 일본":"JP","🇻🇳 베트남":"VN","🇩🇪 독일":"DE",
    "🇮🇩 인도네시아":"ID","🇹🇭 태국":"TH","🇦🇺 호주":"AU","🇮🇳 인도":"IN","🇬🇧 영국":"GB",
    "🇨🇦 캐나다":"CA","🇲🇾 말레이시아":"MY","🇸🇬 싱가포르":"SG","🇵🇭 필리핀":"PH",
    "🇰🇭 캄보디아":"KH","🇳🇿 뉴질랜드":"NZ","🇨🇱 칠레":"CL","🇵🇪 페루":"PE",
    "🇨🇴 콜롬비아":"CO","🇹🇷 터키":"TR","🇮🇱 이스라엘":"IL","🇫🇷 프랑스":"FR",
    "🇮🇹 이탈리아":"IT","🇪🇸 스페인":"ES",
}

def _sanitize_data_key(val) -> str:
    s = re.sub(r'[^0-9]', '', str(val).strip())
    return s.zfill(10) if len(s) >= 4 else s

def _sanitize_query_key(val) -> str:
    return re.sub(r'[^0-9]', '', str(val).strip())

BASIC_KIND_SET = {'기본관세','FTA','특혜(WTO양허)'}

def _tariff_kind_kr(code: str) -> str:
    if not code: return '기타'
    if code[0] == 'F': return 'FTA'
    return TARIFF_KIND_MAP.get(code[0], TARIFF_KIND_MAP.get(code, '기타'))

def _fta_agreement_name(code: str) -> str:
    alpha = re.sub(r'[^A-Z]', '', code)
    for pl in range(len(alpha), 1, -1):
        if alpha[:pl] in FTA_CODE_TO_NAME:
            return f"{FTA_CODE_TO_NAME[alpha[:pl]]} ({code})"
    return f"FTA ({code})"

def _tariff_display_name(code: str) -> str:
    if not code: return '기타'
    if code[0] == 'F': return _fta_agreement_name(code)
    return f"{TARIFF_KIND_MAP.get(code[0], code)} ({code})"

@st.cache_data(ttl=3600, show_spinner="📦 HS부호 데이터 로딩...")
def load_hs_data() -> pd.DataFrame:
    path = _find_data_file("HS부호")
    if path is None:
        st.error("❌ HS부호 파일을 찾을 수 없습니다.")
        return pd.DataFrame()
    df = pd.read_excel(path, engine='openpyxl')
    df = df.reset_index(drop=True)
    df['hs_key'] = df['HS부호'].apply(_sanitize_data_key)
    for col in ['한글품목명','영문품목명','HS부호내용','성질통합분류코드명']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str).replace('nan','')
    ctx = df.get('성질통합분류코드명', pd.Series(['']*len(df)))
    df['search_text'] = (ctx.str.strip()+' '+df['한글품목명'].str.strip()+' '+
                         df['영문품목명'].str.strip()+' '+
                         df.get('HS부호내용', pd.Series(['']*len(df))).str.strip())
    df['search_text'] = df['search_text'].str.strip().str.replace(r'\s+', ' ', regex=True)
    logger.info(f"[DATA] HS부호 로드: {len(df)}건 (Context Injection)")
    return df

@st.cache_data(ttl=3600, show_spinner="📦 관세율표 데이터 로딩...")
def load_tariff_data() -> pd.DataFrame:
    path = _find_data_file("관세율표")
    if path is None:
        st.error("❌ 관세율표 파일을 찾을 수 없습니다.")
        return pd.DataFrame()
    df = pd.read_excel(path, engine='openpyxl')
    df = df.reset_index(drop=True)
    df['hs_key'] = df['품목번호'].apply(_sanitize_data_key)
    df['관세율구분'] = df['관세율구분'].fillna('').astype(str)
    df['관세율'] = pd.to_numeric(df['관세율'], errors='coerce').fillna(0).astype(float)
    df['세율종류'] = df['관세율구분'].apply(_tariff_kind_kr)
    df['세율명'] = df['관세율구분'].apply(_tariff_display_name)
    logger.info(f"[DATA] 관세율표 로드: {len(df)}건")
    return df

def _find_data_file(keyword: str) -> Optional[Path]:
    if not RAW_DATA_DIR.exists(): return None
    for f in RAW_DATA_DIR.iterdir():
        if f.suffix == '.xlsx' and keyword in f.name: return f
    for f in RAW_DATA_DIR.iterdir():
        if f.suffix == '.xlsx' and f.name.startswith('#U'):
            try:
                decoded = f.name.replace('#U','\\u').encode().decode('unicode_escape')
                if keyword in decoded: return f
            except: pass
    return None

# ==================================================================
# 간이세액환급대상 데이터 로드 및 조회 함수
# ==================================================================

@st.cache_data(ttl=3600, show_spinner="📦 간이세액환급률표 로딩...")
def load_refund_rate_data() -> pd.DataFrame:
    """간이세액환급률표 데이터 로드 (2026_refund_rate_table.xlsx)"""
    refund_file = RAW_DATA_DIR / "2026_refund_rate_table.xlsx"
    if not refund_file.exists():
        logger.warning(f"[DATA] 간이세액환급률표 파일 없음: {refund_file}")
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(refund_file, engine='openpyxl', dtype=str)
        # 세번 정규화 (점, 하이픈 제거)
        if '세번' in df.columns:
            df['세번_clean'] = df['세번'].apply(lambda x: re.sub(r'[^0-9]', '', str(x).strip()) if pd.notna(x) else '')
            df['1만원당 환급액'] = pd.to_numeric(df['1만원당 환급액'], errors='coerce').fillna(0)
        logger.info(f"[DATA] 간이세액환급률표 로드: {len(df)}건")
        return df
    except Exception as e:
        logger.error(f"[DATA] 간이세액환급률표 로드 실패: {e}")
        return pd.DataFrame()

def check_simple_refund_eligibility(hs_code: str) -> Dict:
    """
    간이세액환급대상 여부 확인
    
    Returns:
        {
            'is_eligible': bool,
            'hs_code': str,
            'item_name': str,
            'refund_rate': float (1만원당 환급액),
            'message': str
        }
    """
    refund_df = load_refund_rate_data()
    
    if refund_df.empty:
        return {
            'is_eligible': False,
            'hs_code': hs_code,
            'item_name': '',
            'refund_rate': 0,
            'message': '간이세액환급률표 데이터를 찾을 수 없습니다.'
        }
    
    # HS코드 정규화
    clean_code = re.sub(r'[^0-9]', '', str(hs_code).strip())
    
    # 정확히 일치하는 세번 찾기 (10자리)
    exact_match = refund_df[refund_df['세번_clean'] == clean_code]
    
    if not exact_match.empty:
        row = exact_match.iloc[0]
        return {
            'is_eligible': True,
            'hs_code': row.get('세번', hs_code),
            'item_name': row.get('품명', ''),
            'refund_rate': float(row.get('1만원당 환급액', 0)),
            'message': f"간이세액환급대상 품목 (1만원당 {int(row.get('1만원당 환급액', 0))}원 환급)"
        }
    
    # 앞자리 매칭 시도 (8자리, 6자리 등)
    for prefix_len in [8, 6, 4]:
        if len(clean_code) >= prefix_len:
            prefix = clean_code[:prefix_len]
            prefix_match = refund_df[refund_df['세번_clean'].str.startswith(prefix)]
            if not prefix_match.empty:
                # 매칭된 품목 수와 대표 정보 반환
                row = prefix_match.iloc[0]
                return {
                    'is_eligible': True,
                    'hs_code': row.get('세번', hs_code),
                    'item_name': row.get('품명', ''),
                    'refund_rate': float(row.get('1만원당 환급액', 0)),
                    'message': f"간이세액환급대상 품목 가능성 있음 (유사 {len(prefix_match)}건, 1만원당 {int(row.get('1만원당 환급액', 0))}원~)"
                }
    
    return {
        'is_eligible': False,
        'hs_code': hs_code,
        'item_name': '',
        'refund_rate': 0,
        'message': '간이세액환급대상 품목이 아닙니다.'
    }

# ==================================================================
# 임베딩 벡터 인덱스 관련 함수
# ==================================================================

EMBEDDINGS_PATH = DATA_DIR / "hs_embeddings_v2.pkl"

@st.cache_resource(show_spinner="🧠 임베딩 벡터 준비 중...")
def get_embedding_index() -> Tuple[np.ndarray, List[str]]:
    hs_df = load_hs_data()
    if hs_df.empty: return np.array([]), []
    hs_keys = hs_df['hs_key'].tolist()
    texts = hs_df['search_text'].tolist()
    if EMBEDDINGS_PATH.exists():
        try:
            with open(EMBEDDINGS_PATH,'rb') as f: cache = pickle.load(f)
            if cache.get('count')==len(hs_keys) and cache.get('version',0)>=2:
                return np.array(cache['vectors']), cache['keys']
        except: pass
    api_key = settings.openai_api_key
    if not api_key: return np.array([]), []
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        BATCH=2000; all_vecs=[]
        for i in range(0,len(texts),BATCH):
            bt=[t[:500] for t in texts[i:i+BATCH]]
            resp=client.embeddings.create(model="text-embedding-3-small",input=bt)
            for item in resp.data: all_vecs.append(item.embedding)
        cache={'vectors':all_vecs,'keys':hs_keys,'count':len(hs_keys),'version':2}
        with open(EMBEDDINGS_PATH,'wb') as f: pickle.dump(cache,f)
        return np.array(all_vecs), hs_keys
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {e}")
        return np.array([]), []

def search_hscode(query: str, top_k: int = 5, use_ai: bool = True) -> List[Dict]:
    """3단계 검색: (1) 숫자 직접 매칭 → (2) 키워드 → (3) AI 임베딩"""
    hs_df = load_hs_data()
    if hs_df.empty: return []
    
    # Step 1: HS Code 숫자 직접 매칭
    clean = _sanitize_query_key(query)
    if len(clean) >= 4:
        exact = hs_df[hs_df['hs_key'].str.startswith(clean)]
        if not exact.empty:
            out = []
            for _, r in exact.head(top_k).iterrows():
                out.append({
                    'hs_code': r['HS부호'],
                    'name_kr': r['한글품목명'],
                    'name_en': r.get('영문품목명',''),
                    'similarity': 1.0
                })
            return out
    
    # Step 2: 키워드 검색
    kw_lower = query.lower().strip()
    mask = hs_df['search_text'].str.lower().str.contains(kw_lower, na=False, regex=False)
    kw_match = hs_df[mask]
    if not kw_match.empty:
        out = []
        for _, r in kw_match.head(top_k).iterrows():
            out.append({
                'hs_code': r['HS부호'],
                'name_kr': r['한글품목명'],
                'name_en': r.get('영문품목명',''),
                'similarity': 0.85
            })
        return out
    
    # Step 3: AI 임베딩 검색
    if not use_ai: return []
    vecs, keys = get_embedding_index()
    if vecs.size == 0: return []
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.embeddings.create(model="text-embedding-3-small", input=[query[:500]])
        qv = np.array(resp.data[0].embedding)
        sims = np.dot(vecs, qv) / (np.linalg.norm(vecs, axis=1) * np.linalg.norm(qv) + 1e-10)
        top_idx = np.argsort(sims)[::-1][:top_k]
        out = []
        for idx in top_idx:
            hk = keys[idx]
            row = hs_df[hs_df['hs_key'] == hk].iloc[0]
            out.append({
                'hs_code': row['HS부호'],
                'name_kr': row['한글품목명'],
                'name_en': row.get('영문품목명',''),
                'similarity': float(sims[idx])
            })
        return out
    except Exception as e:
        logger.error(f"AI 검색 실패: {e}")
        return []

def compute_tariff_analysis(hs_code: str, country_code: str = '') -> Dict:
    """관세율 분석"""
    tariff_df = load_tariff_data()
    if tariff_df.empty: return {'found': False}
    
    clean = _sanitize_query_key(hs_code)
    if len(clean) < 4: return {'found': False}
    
    matched = tariff_df[tariff_df['hs_key'].str.startswith(clean[:10])]
    if matched.empty: return {'found': False}
    
    basic = matched[matched['세율종류'] == '기본관세']['관세율'].min()
    wto = matched[matched['세율종류'] == '특혜(WTO양허)']['관세율'].min()
    
    result = {'found': True, 'basic_rate': basic if pd.notna(basic) else None, 'wto_rate': wto if pd.notna(wto) else None}
    
    # 최저 세율 찾기
    min_rate = None
    if country_code:
        fta_codes = COUNTRY_TO_FTA.get(country_code, [])
        for fc in fta_codes:
            fta_rows = matched[matched['관세율구분'].str.contains(fc, na=False)]
            if not fta_rows.empty:
                fr = fta_rows['관세율'].min()
                if pd.notna(fr) and (min_rate is None or fr < min_rate):
                    min_rate = fr
                    result['min_rate'] = {'rate': fr, 'name': _fta_agreement_name(fc)}
    
    if min_rate is None:
        candidates = [basic, wto]
        candidates = [c for c in candidates if pd.notna(c)]
        if candidates:
            min_rate = min(candidates)
            if min_rate == basic:
                result['min_rate'] = {'rate': basic, 'name': '기본관세'}
            else:
                result['min_rate'] = {'rate': wto, 'name': '특혜(WTO양허)'}
    
    return result

def analyze_image_with_vision(file_bytes: bytes) -> str:
    """이미지 분석하여 품목 설명 추출"""
    try:
        api_key = settings.openai_api_key
        if not api_key: return ""
        
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        b64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        prompt = """이 이미지에 보이는 물품을 정확하게 설명하세요.
- 물품의 종류, 재질, 용도를 포함하세요.
- 관세청 HS Code 검색에 활용할 수 있도록 상세하게 작성하세요.
- 50단어 이내로 간결하게 작성하세요."""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a trade specialist analyzing products."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}", "detail": "high"}}
                ]}
            ],
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"이미지 분석 실패: {e}")
        return ""

def extract_trade_data_from_doc(file_bytes: bytes, filename: str, trade_type: str) -> Dict:
    """문서에서 거래 데이터 추출 (AI 기반)"""
    try:
        api_key = settings.openai_api_key
        if not api_key: return {'error': 'OpenAI API 키가 설정되지 않았습니다.'}
        
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        b64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        # ★★★ SUPER-DETECTIVE PROMPT ★★★
        prompt = f"""
        Act as a Trade Document Detective. Analyze the image (Invoice/BL) for '{'Import' if trade_type=='import' else 'Export'}' transaction.
        
        CRITICAL INSTRUCTION:
        1. **Incoterms**: Hunt for 3-letter codes like FOB, CIF, EXW, CFR near the Total Amount, Unit Price, or Port names. If found, extract it.
        2. **Country**: If 'Destination Country' or 'Origin Country' is not explicitly labeled, INFER it from the addresses (Exporter/Importer) or Ports (Loading/Discharge).
        3. **Numbers**: Extract HS Code, Amounts, and Weights as clean numbers.
        
        [Target Fields to Extract]
        1. invoice_no: Document No.
        2. date_info: Date (YYYY-MM-DD).
        3. exporter_name: Seller/Shipper.
        4. importer_name: Buyer/Consignee.
        5. notify_party: Notify Party.
        6. item_name: Goods Description.
        7. hs_code: HS Code (Remove dots, numbers only).
        8. country: Origin (if Import) / Destination (if Export). *Infer if missing.*
        9. incoterms: Terms of Delivery (FOB, CIF, etc.). *Look closely.*
        10. currency: Currency (USD, KRW, etc.).
        11. total_amount: Total Value.
        12. quantity: Quantity.
        13. unit: Unit (KG, EA, SET).
        14. unit_price: Unit Price.
        15. gross_weight: G.W.
        16. net_weight: N.W.
        17. bl_number: B/L No.
        18. vessel_name: Vessel/Flight.
        19. loading_port: POL.
        20. discharge_port: POD.
        21. payment_terms: Payment (L/C, T/T).
        
        Return ONLY the JSON object.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a specialized JSON parser for trade docs."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}", "detail": "high"}}
                ]}
            ],
            max_tokens=2000,
            temperature=0.0
        )
        
        raw_text = response.choices[0].message.content.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        return json.loads(raw_text)

    except Exception as e:
        logger.error(f"Analysis Error: {e}")
        return {'error': str(e)}

# ==================================================================
# ONE-STOP SYNC 함수
# ==================================================================

def one_stop_sync(trade_type: str, data: Dict[str, Any]):
    """
    DB 등록 + 캘린더 연동 + 알림
    """
    from modules.master_data import create_trade, get_margin_rate
    from modules.calendar import set_export_deadline, set_import_deadline
    
    try:
        # 1. 마진율 자동 조회 및 저장
        hsc = data.get('hs_code', '')
        mi = get_margin_rate(hsc)
        data['base_margin_rate'] = mi['rate']
        
        # 2. 거래 생성 (DB)
        tid = create_trade(trade_type, data)
        
        if tid:
            st.toast(f"✅ 거래 데이터베이스 등록 완료: {tid}", icon="💾")
            
            # 3. 캘린더 연동
            ref_date = data.get('ref_date')
            cal_res = None
            if trade_type == 'import' and ref_date:
                ft = int(data.get('free_time', 7))
                cal_res = set_import_deadline(tid, datetime.combine(ref_date, datetime.min.time()), ft)
            elif trade_type == 'export' and ref_date:
                cal_res = set_export_deadline(tid, datetime.combine(ref_date, datetime.min.time()))
            
            # 캘린더 결과 처리
            if cal_res:
                safe_title = cal_res.get('title', f"[{trade_type.upper()}] {tid} 일정")
                safe_dl = cal_res.get('deadline', '확인 필요')
                st.toast(f"📅 캘린더 등록: {safe_title}", icon="🗓️")
                st.success(f"**등록 완료!**\n\n- 거래번호: `{tid}`\n- 마감일: `{safe_dl}`\n- 총액: `{data.get('currency')} {data.get('item_value',0):,.0f}`")
            else:
                st.warning("거래는 등록되었으나, 날짜 정보 부족으로 캘린더에는 반영되지 않았습니다.")
            
            return True
    except Exception as e:
        st.error(f"동기화 중 오류 발생: {e}")
        return False

# ==================================================================
# SESSION / AUTH
# ==================================================================

def init_session():
    """세션 상태 초기화 - staging_data와 staging_type을 반드시 포함"""
    # CSS 적용
    apply_custom_css()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None

    # ★ CRITICAL: Staging Area를 위한 상태 초기화
    if 'staging_data' not in st.session_state:
        st.session_state.staging_data = None
    if 'staging_type' not in st.session_state:
        st.session_state.staging_type = None

# HS Code 검색용 상태 변수 (from trade-helper v3.0)
    if 'hs_sel_4' not in st.session_state: st.session_state.hs_sel_4 = None
    if 'hs_sel_6' not in st.session_state: st.session_state.hs_sel_6 = None
    if 'hs_sel_789' not in st.session_state: st.session_state.hs_sel_789 = None  # 7,8,9단위 추가
    if 'hs_sel_10' not in st.session_state: st.session_state.hs_sel_10 = None
    if 'hs_last_query' not in st.session_state: st.session_state.hs_last_query = ""
    if 'hs_desc_4' not in st.session_state: st.session_state.hs_desc_4 = ""
    if 'hs_search_result' not in st.session_state: st.session_state.hs_search_result = None

    # ★ NEW: 캐시 기반 마스터 데이터 관리자 초기화 (1회만)
    if 'cached_manager' not in st.session_state:
        try:
            logger.info("[INIT] 캐시 매니저 초기화 시작...")

            # Excel 템플릿 경로
            template_path = Path(__file__).parent.parent / "trade_erp_master_template.xlsx"

            if not template_path.exists():
                logger.warning(f"[INIT] 템플릿 파일 없음: {template_path}")
                st.session_state.cached_manager = None
                st.session_state.sync_scheduler = None
                st.session_state.file_watcher = None
                return

            # 1. ColumnMapper 생성
            if settings.openai_api_key:
                mapper = ColumnMapper(api_key=settings.openai_api_key)

                # 2. CachedMasterDataManager 생성
                st.session_state.cached_manager = CachedMasterDataManager(
                    excel_filepath=str(template_path),
                    column_mapper=mapper,
                    auto_load=True
                )

                # 3. 정기 동기화 스케줄러 시작 (5분마다)
                st.session_state.sync_scheduler = start_periodic_sync(
                    st.session_state.cached_manager,
                    interval_minutes=5
                )

                # 4. 파일 모니터링 시작
                st.session_state.file_watcher = start_file_watcher(
                    st.session_state.cached_manager,
                    debounce_seconds=2.0
                )

                logger.info("[INIT] 캐시 매니저 초기화 완료")
            else:
                logger.warning("[INIT] OpenAI API 키 없음 - 캐시 매니저 비활성화")
                st.session_state.cached_manager = None
                st.session_state.sync_scheduler = None
                st.session_state.file_watcher = None

        except Exception as e:
            logger.error(f"[INIT] 캐시 매니저 초기화 실패: {e}", exc_info=True)
            st.session_state.cached_manager = None
            st.session_state.sync_scheduler = None
            st.session_state.file_watcher = None

def login_page():
    st.markdown(
        "<h1 style='text-align: center;'>💼 자동 eDay</h1>",
        unsafe_allow_html=True
    )
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.subheader("로그인")
        with st.form("login"):
            uid = st.text_input("아이디", placeholder="admin")
            pwd = st.text_input("비밀번호", type="password", placeholder="admin123")
            if st.form_submit_button("로그인", use_container_width=True):
                ok, user = authenticate(uid, pwd)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호를 확인해주세요.")

# ==================================================================
# MAIN APP + SIDEBAR
# ==================================================================

def main_app():
    # 세션 상태에 선택된 메뉴가 없으면 기본값 설정
    if 'selected_menu' not in st.session_state:
        st.session_state.selected_menu = "대시보드"
    
    with st.sidebar:
        st.title("Menu")
        
        # 메뉴 버튼 리스트
        menu_items = [
            "대시보드", 
            "캘린더", 
            "HS Code 검색", 
            "수입 관리", 
            "수출 관리", 
            "서류 생성", 
            "거래 목록", 
            "⚙️ 설정"
        ]
        
        # 각 메뉴를 버튼으로 표시
        for menu_item in menu_items:
            # 현재 선택된 메뉴인지 확인
            is_selected = st.session_state.selected_menu == menu_item
            button_type = "primary" if is_selected else "secondary"
            
            if st.button(
                menu_item, 
                key=f"menu_{menu_item}",
                use_container_width=True,
                type=button_type
            ):
                st.session_state.selected_menu = menu_item
                st.rerun()
        
        st.divider()
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # 선택된 메뉴에 따라 페이지 표시
    menu = st.session_state.selected_menu
    
    if menu == "대시보드":
        page_dashboard()
    elif menu == "캘린더":
        page_calendar()
    elif menu == "HS Code 검색":
        page_hs_search()
    elif menu == "수입 관리":
        page_import()
    elif menu == "수출 관리":
        page_export()
    elif menu == "서류 생성":
        page_documents()
    elif menu == "거래 목록":
        page_trades()
    elif menu == "⚙️ 설정":
        page_settings()

# ==================================================================
# PAGE: 대시보드
# ==================================================================


def page_dashboard():
    st.title("대시보드")
    st.divider()
    # =================================================================
    # 0. 대시보드 상단 요약 메트릭
    # =================================================================
    from modules.master_data import load_master_data
    from modules.calendar import DeadlineTracker

    try:
        df = load_master_data()
        
        if not df.empty:
            # 총 거래 건수
            total_trades = len(df)
            
            # 수입 건수
            import_count = len(df[df['trade_type'] == 'import'])
            
            # 수출 건수
            export_count = len(df[df['trade_type'] == 'export'])
        else:
            total_trades = 0
            import_count = 0
            export_count = 0
    except:
        total_trades = 0
        import_count = 0
        export_count = 0
    
    # 메트릭 카드 표시 (CSS로 자동 카드 스타일 적용)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총 거래 건수", f"{total_trades}건")
    with col2:
        st.metric("총 수입", f"{import_count}건")
    with col3:
        st.metric("총 수출", f"{export_count}건")
    
    st.divider()
    
    # =================================================================
    # 1. 현재 환율 (위치 변경: 환율 추이보다 먼저 표시)
    # =================================================================
    
    # 통화 정보 정의
    currencies = {
        'USD': {'name': 'USD (달러)', 'color': '#1f77b4'},
        'JPY': {'name': 'JPY (100엔)', 'color': '#ff7f0e'},
        'CNY': {'name': 'CNY (위안)', 'color': '#2ca02c'},
        'EUR': {'name': 'EUR (유로)', 'color': '#d62728'},
        'GBP': {'name': 'GBP (파운드)', 'color': '#9467bd'}    }
    
    # 기본값 설정
    if 'exchange_period' not in st.session_state:
        st.session_state.exchange_period = 30
    if 'selected_currency' not in st.session_state:
        st.session_state.selected_currency = 'USD'  # USD를 기본 통화로 설정
    
    # 데이터 로드 (현재 환율 표시를 위해 먼저 로드)
    exchange_df = get_exchange_rate_data(days=st.session_state.exchange_period)
    latest = exchange_df.iloc[-1]
    previous = exchange_df.iloc[-2] if len(exchange_df) > 1 else latest
    
    # 현재 환율 (CSS로 자동 카드 스타일 적용)
    st.subheader("📊 현재 환율")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # 선택된 통화를 강조 표시
    selected_curr = st.session_state.selected_currency
    
    with col1:
        delta_usd = latest['USD'] - previous['USD']
        st.metric("USD", f"₩{latest['USD']:,.2f}", f"{delta_usd:+.2f}")
    with col2:
        delta_jpy = latest['JPY'] - previous['JPY']
        st.metric("JPY (100엔)", f"₩{latest['JPY']:,.2f}", f"{delta_jpy:+.2f}")
    with col3:
        delta_cny = latest['CNY'] - previous['CNY']
        st.metric("CNY", f"₩{latest['CNY']:,.2f}", f"{delta_cny:+.2f}")
    with col4:
        delta_eur = latest['EUR'] - previous['EUR']
        st.metric("EUR", f"₩{latest['EUR']:,.2f}", f"{delta_eur:+.2f}")
    with col5:
        delta_gbp = latest['GBP'] - previous['GBP']
        st.metric("GBP", f"₩{latest['GBP']:,.2f}", f"{delta_gbp:+.2f}")
    
    st.divider()
    
    # =================================================================
    # 2. 환율 추이 그래프 & 환율 계산기 (한 행에 배치)
    # =================================================================
    
    # 한 행에 2개 컬럼으로 나누기 (왼쪽: 환율 추이, 오른쪽: 환율 계산기)
    exchange_col, calc_col = st.columns([1, 1], gap="large")
    
    # ========== 왼쪽: 환율 추이 그래프 ==========
    with exchange_col:
        st.subheader("💱 환율 추이")
        
        # 통화 선택 버튼
        st.markdown("**통화 선택**")
        curr_col1, curr_col2, curr_col3, curr_col4, curr_col5 = st.columns(5)
        
        with curr_col1:
            if st.button("USD", key="curr_usd", use_container_width=True,
                        type="primary" if st.session_state.selected_currency == 'USD' else "secondary"):
                st.session_state.selected_currency = 'USD'
                st.rerun()
        with curr_col2:
            if st.button("JPY", key="curr_jpy", use_container_width=True,
                        type="primary" if st.session_state.selected_currency == 'JPY' else "secondary"):
                st.session_state.selected_currency = 'JPY'
                st.rerun()
        with curr_col3:
            if st.button("CNY", key="curr_cny", use_container_width=True,
                        type="primary" if st.session_state.selected_currency == 'CNY' else "secondary"):
                st.session_state.selected_currency = 'CNY'
                st.rerun()
        with curr_col4:
            if st.button("EUR", key="curr_eur", use_container_width=True,
                        type="primary" if st.session_state.selected_currency == 'EUR' else "secondary"):
                st.session_state.selected_currency = 'EUR'
                st.rerun()
        with curr_col5:
            if st.button("GBP", key="curr_gbp", use_container_width=True,
                        type="primary" if st.session_state.selected_currency == 'GBP' else "secondary"):
                st.session_state.selected_currency = 'GBP'
                st.rerun()
        
        # 기간 선택 버튼
        st.markdown("**기간 선택**")
        period_col1, period_col2, period_col3, period_col4 = st.columns([1, 1, 1, 1])
        
        current_period = st.session_state.exchange_period
        
        with period_col1:
            if st.button("1M", key="period_1m", use_container_width=True,
                        type="primary" if current_period == 30 else "secondary"):
                st.session_state.exchange_period = 30
                st.rerun()
        with period_col2:
            if st.button("3M", key="period_3m", use_container_width=True,
                        type="primary" if current_period == 90 else "secondary"):
                st.session_state.exchange_period = 90
                st.rerun()
        with period_col3:
            if st.button("1Y", key="period_1y", use_container_width=True,
                        type="primary" if current_period == 365 else "secondary"):
                st.session_state.exchange_period = 365
                st.rerun()
        with period_col4:
            if st.button("3Y", key="period_3y", use_container_width=True,
                        type="primary" if current_period == 365 * 3 else "secondary"):
                st.session_state.exchange_period = 365 * 3
                st.rerun()
        
        # 선택된 기간 표시
        period_days = st.session_state.exchange_period
        if period_days == 30:
            period_text = "1개월"
        elif period_days == 90:
            period_text = "3개월"
        elif period_days == 365:
            period_text = "1년"
        elif period_days == 365 * 3:
            period_text = "3년"
        
        curr_info = currencies[selected_curr]
        
        # 선택된 통화만 표시하는 차트 생성
        fig_exchange = go.Figure()
        
        # Y축 범위 계산 (데이터 기반 동적 범위 - 변동폭 강조)
        y_data = exchange_df[selected_curr]
        y_min = y_data.min()
        y_max = y_data.max()
        y_range = y_max - y_min
        
        # 변동폭의 5% 여유 적용 (좁은 범위로 변동 강조)
        if y_range < 5:
            y_padding = 2  # 변동폭이 매우 작을 때
        else:
            y_padding = y_range * 0.05
        
        y_axis_min = y_min - y_padding
        y_axis_max = y_max + y_padding
        
        # 메인 라인 차트
        fig_exchange.add_trace(go.Scatter(
            x=exchange_df['date'], 
            y=exchange_df[selected_curr],
            mode='lines',
            name=curr_info['name'],
            line=dict(color=curr_info['color'], width=2.5),
            hovertemplate='%{x}<br>%{y:,.2f}원<extra></extra>'
        ))
        
        # 배경 채움 영역 (Y축 최소값 기준)
        fig_exchange.add_trace(go.Scatter(
            x=list(exchange_df['date']) + list(exchange_df['date'][::-1]),
            y=list(exchange_df[selected_curr]) + [y_axis_min] * len(exchange_df),
            fill='toself',
            fillcolor=f"rgba{tuple(list(int(curr_info['color'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.12])}",
            line=dict(width=0),
            hoverinfo='skip',
            showlegend=False
        ))
        
        # 증권사 스타일 레이아웃 (Y축 범위 적용)
        fig_exchange.update_layout(
            height=400,
            hovermode='x unified',
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            showlegend=False,
            yaxis=dict(
                title=f'{curr_info["name"]} 환율 (원)',
                gridcolor='#E8E8E8',
                showline=True,
                linewidth=1,
                linecolor='#E0E0E0',
                tickformat=',.0f',
                range=[y_axis_min, y_axis_max],  # 동적 Y축 범위
                autorange=False
            ),
            xaxis=dict(
                title='',
                gridcolor='#E8E8E8',
                showline=True,
                linewidth=1,
                linecolor='#E0E0E0'
            ),
            margin=dict(l=60, r=30, t=30, b=40)
        )
        
        st.plotly_chart(fig_exchange, use_container_width=True)
    
    # ========== 오른쪽: 환율 계산기 ==========
    with calc_col:
        st.subheader("💰 환율 계산기")
        
        # 통화 선택
        selected_currency = st.selectbox(
            "통화 선택",
            options=['USD', 'JPY', 'CNY', 'EUR', 'GBP'],
            format_func=lambda x: currencies.get(x, {}).get('name', x),
            key="calc_currency"
        )

        # 기준 환율 가져오기
        base_rate = latest[selected_currency]
        
        # 계산 방향 선택 (통화 선택 바로 아래로 이동)
        calc_direction = st.radio(
            "계산 방향",
            options=['외화 → 원화', '원화 → 외화'],
            horizontal=True,
            key="calc_direction"
        )
        
        # 금액 입력 (통화 선택 아래, 계산 방향 다음)
        if calc_direction == '외화 → 원화':
            # 외화 입력
            foreign_amount = st.number_input(
                f"{selected_currency} 금액",
                min_value=0.0,
                value=100.0,
                step=10.0,
                key="foreign_input"
            )
        else:
            # 원화 입력
            krw_amount = st.number_input(
                "원화 (KRW) 금액",
                min_value=0.0,
                value=100000.0,
                step=10000.0,
                key="krw_input"
            )
        
        # 환전 우대율 입력
        preferential_rate = st.number_input(
            "환전 우대율 (%)",
            min_value=0.0,
            max_value=100.0,
            value=90.0,
            step=0.1,
            help="은행 환전 우대율을 입력하세요. (일반적으로 80~100%)",
            key="pref_rate"
        )
        
        # 거래 유형 선택
        transaction_type = st.radio(
            "거래 유형 선택",
            options=['송금 보낼 때', '송금 받을 때', '현찰 살 때', '현찰 팔 때'],
            horizontal=True,
            key="trans_type"
        )
        
        # 거래 유형별 환율 스프레드 (은행 수수료)
        spread_rates = {
            '송금 보낼 때': 0.015,   # 1.5%
            '송금 받을 때': 0.015,   # 1.5%
            '현찰 살 때': 0.0175,    # 1.75%
            '현찰 팔 때': 0.0175     # 1.75%
        }
        
        spread = spread_rates.get(transaction_type, 0.015)
        
        # 실제 적용 환율 계산
        if transaction_type in ['송금 보낼 때', '현찰 살 때']:
            # 외화를 사는 경우 (더 비싸게)
            spread_amount = base_rate * spread
            preferential_discount = spread_amount * (preferential_rate / 100)
            applied_rate = base_rate + spread_amount - preferential_discount
        else:
            # 외화를 파는 경우 (더 싸게)
            spread_amount = base_rate * spread
            preferential_discount = spread_amount * (preferential_rate / 100)
            applied_rate = base_rate - spread_amount + preferential_discount
        
        # JPY는 100엔 기준이므로 계산 조정
        if selected_currency == 'JPY':
            display_rate = applied_rate
            calc_multiplier = 1 / 100
        else:
            display_rate = applied_rate
            calc_multiplier = 1
        
        # 계산 결과 표시
        if calc_direction == '외화 → 원화':
            # 원화 계산
            if selected_currency == 'JPY':
                krw_amount = foreign_amount * (applied_rate / 100)
            else:
                krw_amount = foreign_amount * applied_rate
            
            result_text = f"{foreign_amount:,.2f} {selected_currency} = ₩{krw_amount:,.0f}"
            
        else:
            # 외화 계산
            if selected_currency == 'JPY':
                foreign_amount = krw_amount / (applied_rate / 100)
            else:
                foreign_amount = krw_amount / applied_rate
            
            result_text = f"₩{krw_amount:,.0f} = {foreign_amount:,.2f} {selected_currency}"
        
        # 커스텀 스타일 결과 박스
        st.markdown(f"""
        <div style="
            background-color: rgba(255, 255, 255, 0.8);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            margin: 1rem 0;
        ">
            <p style="font-size: 1.5rem; font-weight: 600; color: #1a1a1a; margin: 0;">
                {result_text}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 상세 정보 표시
        with st.expander("환율 계산 상세 정보"):
            st.write(f"**기준 환율:** ₩{base_rate:,.2f}")
            st.write(f"**스프레드:** {spread*100}% (₩{base_rate * spread:,.2f})")
            st.write(f"**우대 할인:** {preferential_rate}% (₩{base_rate * spread * (preferential_rate / 100):,.2f})")
            st.write(f"**최종 적용 환율:** ₩{applied_rate:,.2f}")
    
    st.divider()
    
    # =================================================================
    # 3. 수입/수출 실적 및 전체 매출 실적
    # =================================================================
    st.subheader("📈 거래 실적 (최근 12개월)")

    trade_df = get_trade_performance_data()

    # 전체 매출 실적 계산 (수출 - 수입)
    trade_df['net_sales'] = trade_df['export'] - trade_df['import']

    # 월 라벨 생성 (1월, 2월, ..., 12월)
    trade_df['month_label'] = trade_df['month'].dt.month.apply(lambda x: f"{x}월")

    # 그래프 생성
    fig_trade = go.Figure()
    
    # 수출 실적
    fig_trade.add_trace(go.Bar(
        x=trade_df['month_label'],
        y=trade_df['export'],
        name='수출 실적',
        marker_color="#73b383",
        text=trade_df['export'].apply(lambda x: f"₩{x/1000000:.0f}M"),
        textposition='outside'
    ))

    # 수입 실적
    fig_trade.add_trace(go.Bar(
        x=trade_df['month_label'],
        y=trade_df['import'],
        name='수입 실적',
        marker_color="#c76060",
        text=trade_df['import'].apply(lambda x: f"₩{x/1000000:.0f}M"),
        textposition='outside'
    ))


    # 전체 매출 실적 (무역 수지)
    fig_trade.add_trace(go.Scatter(
        x=trade_df['month_label'],
        y=trade_df['net_sales'],
        name='무역 수지 (수출-수입)',
        mode='lines+markers',
        line=dict(color="#000000", width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))

    # 레이아웃 설정
    fig_trade.update_layout(
        height=500,
        barmode='group',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        yaxis=dict(title='금액 (원)'),
        yaxis2=dict(
            title='무역 수지 (원)',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        xaxis=dict(title='월')
    )
    
    st.plotly_chart(fig_trade, use_container_width=True)
    
    # 요약 통계 (CSS로 자동 카드 스타일 적용)
    col1, col2, col3 = st.columns(3)
    
    total_import = trade_df['import'].sum()
    total_export = trade_df['export'].sum()
    total_net = total_export - total_import
    
    with col1:
        st.metric("총 수입", f"₩{total_import:,.0f}")
    with col2:
        st.metric("총 수출", f"₩{total_export:,.0f}")
    with col3:
        st.metric("무역 수지", f"₩{total_net:,.0f}", 
                 delta=f"{(total_net/total_import*100) if total_import > 0 else 0:.1f}%")
    
    st.divider()
    
    # =================================================================
    # 4. 월별 상세 데이터 테이블
    # =================================================================
    st.subheader("📋 월별 상세 실적")
    
    display_df = trade_df.copy()
    display_df['month'] = display_df['month'].dt.strftime('%Y-%m')
    display_df['import'] = display_df['import'].apply(lambda x: f"₩{x:,.0f}")
    display_df['export'] = display_df['export'].apply(lambda x: f"₩{x:,.0f}")
    display_df['net_sales'] = display_df['net_sales'].apply(lambda x: f"₩{x:,.0f}")

    #c month_label 컬럼 제거 (이미 month로 표시)
    display_df = display_df[['month', 'import', 'export', 'net_sales']]
    display_df.columns = ['월', '수입 실적', '수출 실적', '무역 수지']
    
    display_df.columns = ['월', '수입 실적', '수출 실적', '무역 수지']
    
    # =================================================================
    # 엑셀 다운로드 버튼 (2가지)
    # =================================================================
    from io import BytesIO
    import pandas as pd
    from modules.master_data import get_template_file_path
    
    dl_col1, dl_col2 = st.columns(2)
    
    with dl_col1:
        # 1. 월별 상세 실적 다운로드
        excel_df = trade_df.copy()
        excel_df['month'] = excel_df['month'].dt.strftime('%Y-%m')
        excel_df = excel_df[['month', 'import', 'export', 'net_sales']]
        excel_df.columns = ['월', '수입 실적', '수출 실적', '무역 수지']
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            excel_df.to_excel(writer, sheet_name='월별 상세 실적', index=False)
        
        buffer.seek(0)
        
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        
        st.download_button(
            label="📥 월별 실적 다운로드",
            data=buffer,
            file_name=f"월별_상세_실적_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with dl_col2:
        # 2. trade_erp_master_template.xlsx 전체 다운로드
        template_path = get_template_file_path()
        if template_path:
            try:
                with open(template_path, 'rb') as f:
                    template_data = f.read()
                
                st.download_button(
                    label="📊 마스터 템플릿 다운로드",
                    data=template_data,
                    file_name=f"trade_erp_master_{today}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help="PAGE1(데이터) + PAGE2(집계) 포함"
                )
            except Exception as e:
                st.caption(f"템플릿 다운로드 불가: {e}")
        else:
            st.caption("템플릿 파일이 설정되지 않았습니다.")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# =================================================================
# 헬퍼 함수: 환율 데이터 생성 (기간 파라미터 추가)
# =================================================================

def get_exchange_rate_data(days=30):
    """
    yfinance를 사용하여 실제 환율 데이터 가져오기
    실패 시 현재 환율 기준 fallback 데이터 제공
    
    Parameters:
    - days: 조회할 일수 (30, 365, 1825(5년), 3650(10년))
    """
    from datetime import datetime, timedelta
    import pandas as pd
    import numpy as np
    
    try:
        import yfinance as yf
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 환율 심볼 (Yahoo Finance)
        symbols = {
            'USD': 'USDKRW=X',
            'JPY': 'JPYKRW=X',
            'CNY': 'CNYKRW=X',
            'EUR': 'EURKRW=X',
            'GBP': 'GBPKRW=X'
        }
        
        result_data = []
        
        # 각 통화별 데이터 다운로드
        for currency, symbol in symbols.items():
            try:
                data = yf.download(symbol, start=start_date, end=end_date, progress=False)
                if not data.empty:
                    temp_df = pd.DataFrame({
                        'date': data.index,
                        'currency': currency,
                        'rate': data['Close'].values
                    })
                    result_data.append(temp_df)
            except:
                continue
        
        if result_data:
            # 데이터 병합
            combined = pd.concat(result_data, ignore_index=True)
            df = combined.pivot(index='date', columns='currency', values='rate').reset_index()
            
            # JPY는 100엔 기준으로 변환
            if 'JPY' in df.columns:
                df['JPY'] = df['JPY'] * 100
            
            # 결측치 채우기 (주말/공휴일)
            for col in ['USD', 'JPY', 'CNY', 'EUR', 'GBP']:
                if col in df.columns:
                    df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
            
            return df
        else:
            raise Exception("데이터를 가져올 수 없습니다")
    
    except Exception as e:
        # Fallback: 실시간 환율 가져오기 시도
        print(f"환율 API 오류 ({e}). Fallback 데이터를 사용합니다.")
        
        # 최신 환율 가져오기
        try:
            current_rates = get_current_exchange_rates()
        except:
            # 완전 Fallback: 2026년 2월 예상 환율
            current_rates = {
                'USD': 1380.00,
                'JPY': 1050.00,
                'CNY': 198.00,
                'EUR': 1560.00,
                'GBP': 1800.00
            }
        
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        
        np.random.seed(42)
        data = {'date': dates}
        
        for currency, current_rate in current_rates.items():
            # 기간에 따른 추세 생성
            if days <= 30:
                # 1개월: 약간의 변동
                trend = np.linspace(current_rate * 0.98, current_rate, days)
                volatility_scale = 0.005
            elif days <= 365:
                # 1년: 중간 변동
                trend = np.linspace(current_rate * 0.95, current_rate, days)
                volatility_scale = 0.008
            else:
                # 장기: 큰 변동
                trend = np.linspace(current_rate * 0.90, current_rate, days)
                volatility_scale = 0.01
            
            # 통화별 변동성
            volatility = np.random.randn(days) * current_rate * volatility_scale
            
            # 계절성 추가
            seasonal = np.sin(np.linspace(0, days/365 * 2 * np.pi, days)) * (current_rate * 0.01)
            
            rates = trend + volatility + seasonal
            
            # 마지막 값은 정확히 현재 환율
            rates[-1] = current_rate
            
            data[currency] = rates
        
        df = pd.DataFrame(data)
        
        # 음수 방지
        for col in ['USD', 'JPY', 'CNY', 'EUR', 'GBP']:
            df[col] = df[col].clip(lower=0)
        
        return df


def get_current_exchange_rates():
    """현재 환율을 실시간으로 가져오기"""
    import yfinance as yf
    from datetime import datetime, timedelta
    
    # 최근 5일 데이터 가져오기 (주말 대비)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)
    
    rates = {}
    symbols = {
        'USD': 'USDKRW=X',
        'JPY': 'JPYKRW=X',
        'CNY': 'CNYKRW=X',
        'EUR': 'EURKRW=X',
        'GBP': 'GBPKRW=X'
    }
    
    for currency, symbol in symbols.items():
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if not data.empty:
            rate = data['Close'].iloc[-1]
            if currency == 'JPY':
                rate = rate * 100  # 100엔 기준
            rates[currency] = float(rate)
    
    return rates

# =================================================================
# PAGE: HS Code 검색 v3.0 (from trade-helper)
# =================================================================
def page_hs_search():
    st.title("🔍 HS Code 검색")
    st.divider()

    # HS코드 포맷 변환 함수
    def format_hs_code(code: str) -> str:
        """HS코드를 표준 양식으로 변환
        - 6자리: 871200 → 8712.00
        - 10자리: 8712009090 → 8712.00-9090
        """
        code = code.strip()
        if len(code) == 6:
            return f"{code[:4]}.{code[4:]}"
        elif len(code) == 10:
            return f"{code[:4]}.{code[4:6]}-{code[6:]}"
        else:
            return code

    try:
        from modules.hs_code import analyze_tariff_rates
    except ImportError:
        def analyze_tariff_rates(c, n): return {}

    try:
        from modules.hs_code.search import check_customs_confirmation, is_gita_code, get_searcher
    except ImportError:
        def check_customs_confirmation(c): return {'is_subject': False, 'categories': []}
        def is_gita_code(c): return (False, None, 'none')

    if hs_df.empty:
        st.warning(f"데이터 파일이 로드되지 않았습니다. '{HS_EXCEL_PATH}' 경로를 확인해주세요.")
        return

    if 'hs_search_result' not in st.session_state:
        st.session_state.hs_search_result = None
    
    # 대상국 설정 초기화
    if 'target_country' not in st.session_state:
        st.session_state.target_country = ""

    # ══════════════════════════════════════════
    # 대상국 설정 (검색란 위에 배치)
    # ══════════════════════════════════════════
    MAJOR_COUNTRIES = {
        "전체": "",
        "US 미국": "US", "CN 중국": "CN", "JP 일본": "JP", "VN 베트남": "VN",
        "DE 독일": "DE", "ID 인도네시아": "ID", "TH 태국": "TH", "AU 호주": "AU",
        "IN 인도": "IN", "GB 영국": "GB", "CA 캐나다": "CA", "MY 말레이시아": "MY",
        "SG 싱가포르": "SG", "PH 필리핀": "PH", "KH 캄보디아": "KH", "NZ 뉴질랜드": "NZ",
        "CL 칠레": "CL", "PE 페루": "PE", "CO 콜롬비아": "CO", "TR 터키": "TR",
        "IL 이스라엘": "IL", "AE 아랍에미리트": "AE", "FR 프랑스": "FR", "IT 이탈리아": "IT", "ES 스페인": "ES",
    }
    
    selected_country_name = st.selectbox(
        "수입 대상국 선택",
        options=list(MAJOR_COUNTRIES.keys()),
        index=0,
        help="수입하려는 물품의 원산지 국가를 선택하세요. FTA 협정세율 적용 여부에 영향을 줍니다."
    )
    st.session_state.target_country = MAJOR_COUNTRIES[selected_country_name]

    # ── 검색 입력 ──
    query = st.text_input(
        "HS Code 조회",
        placeholder="품목명, 키워드 또는 HS 코드를 입력하세요."
    )

    if query != st.session_state.hs_last_query:
        st.session_state.hs_last_query = query
        st.session_state.hs_sel_4 = None
        st.session_state.hs_sel_6 = None
        st.session_state.hs_sel_789 = None  # 7,8,9단위 추가
        st.session_state.hs_sel_10 = None
        st.session_state.hs_search_result = None

    if not query:
        return

    # ══════════════════════════════════════════
    # 10자리 HS Code 직접 매칭 (선택 과정 생략)
    # ══════════════════════════════════════════
    clean_query = query.replace(".", "").replace("-", "").replace(" ", "").strip()
    
    if clean_query.isdigit() and len(clean_query) == 10:
        # 10자리 코드 직접 매칭 시도
        exact_match = hs_df[hs_df['HS부호'] == clean_query]
        
        if not exact_match.empty:
            matched_row = exact_match.iloc[0]
            st.success(f"✅ **10자리 HS Code 정확 매치!**")
            
            # 결과 표시
            st.markdown("---")
            col_result1, col_result2 = st.columns([1, 2])
            
            with col_result1:
                formatted_code = format_hs_code(clean_query)
                st.markdown(f"### 🎯 {formatted_code}")
                st.caption(f"원본: {clean_query}")
            
            with col_result2:
                st.markdown(f"**품목명:** {matched_row['한글품목명']}")
                if '영문품목명' in matched_row and pd.notna(matched_row.get('영문품목명')):
                    st.caption(f"English: {matched_row['영문품목명']}")
            
            # 관세율 분석
            st.markdown("---")
            st.subheader("📊 관세율 분석")
            
            tariff_info = analyze_tariff_rates(clean_query, st.session_state.target_country)
            
            if tariff_info:
                t_col1, t_col2, t_col3 = st.columns(3)
                with t_col1:
                    st.metric("기본세율", f"{tariff_info.get('basic_rate', '-')}%")
                with t_col2:
                    st.metric("WTO 협정세율", f"{tariff_info.get('wto_rate', '-')}%")
                with t_col3:
                    fta_rate = tariff_info.get('fta_rate', '-')
                    st.metric("FTA 세율", f"{fta_rate}%" if fta_rate != '-' else '-')
                
                # 적용 세율 표시
                applied_rate = tariff_info.get('applied_rate', tariff_info.get('basic_rate', 0))
                st.info(f"💡 **적용 권장 세율: {applied_rate}%** (가장 낮은 세율 자동 적용)")
            else:
                st.warning("관세율 정보를 찾을 수 없습니다.")
            
            # 세관장 확인 대상 여부
            customs_check = check_customs_confirmation(clean_query)
            if customs_check.get('is_subject'):
                st.error(f"⚠️ **세관장확인대상품목** - 카테고리: {', '.join(customs_check.get('categories', []))}")
            
            # 기타코드 여부
            is_gita, gita_type, gita_level = is_gita_code(clean_query)
            if is_gita:
                st.warning(f"📌 **기타코드**: {gita_type} ({gita_level})")
            
            return  # 10자리 직접 매칭 시 여기서 종료

    # ══════════════════════════════════════════
    # 스마트 검색 실행 (기존 로직)
    # ══════════════════════════════════════════
    if st.session_state.hs_search_result is None:
        with st.spinner("🔍 스마트 검색 중..."):
            search_result = search_candidates_by_ai(query)
            st.session_state.hs_search_result = search_result
    else:
        search_result = st.session_state.hs_search_result

    match_type = search_result.get('match_type', 'not_found')
    confidence = search_result.get('confidence', 0)
    ranking = search_result.get('ranking')

    if match_type == 'not_found' or ranking is None:
        st.warning("❌ 관련된 HS Code를 찾을 수 없습니다.")
        if search_result.get('error'):
            st.caption(f"사유: {search_result['error']}")
        return

    # ── 검색 상태 표시 (신뢰도 제거) ──
    if match_type == 'exact':
        st.success(f"✅ **'{query}'** 정확 매치")
    elif match_type == 'keyword':
        st.info(f"🔍 **'{query}'** 키워드+동의어 매치")
    elif match_type == 'prefix':
        st.info(f"📋 **HS코드 '{query}'** 접두사 매칭")
    elif match_type == 'ai_corrected':
        orig = search_result.get('original_input', query)
        corrected = search_result.get('corrected_code', '')
        st.warning(f"🔄 **'{orig}'** → AI 보정: **{corrected}**")

    # AI 분석 결과 표시 (HS코드 직접 입력 제외하고 모든 경우에 표시)
    ai_info = search_result.get('ai_analysis', {})
    if ai_info and match_type not in ['prefix', 'ai_corrected']:
        with st.expander("물품 분석 결과", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**한글명:** {ai_info.get('product_name_kr', '-')}")
                st.write(f"**영문명:** {ai_info.get('product_name_en', '-')}")
                st.write(f"**주요 기능:** {ai_info.get('primary_function', '-')}")
            with c2:
                st.write(f"**주요 재질:** {ai_info.get('primary_material', '-')}")
                st.write(f"**추정 류:** 제{ai_info.get('chapter_hint', '?')}류")
                st.write(f"**분류 참고:** {ai_info.get('classification_notes', '-')}")

    # ══════════════════════════════════════════
    # 4단 컬럼 UI (7,8,9단위 추가)
    # ══════════════════════════════════════════
    ranked_4 = ranking.get('ranked_4', [])
    ranked_6_map = ranking.get('ranked_6', {})
    ranked_10_map = ranking.get('ranked_10', {})
    skip_6_codes = ranking.get('skip_6_codes', [])

    col1, col2, col3, col4 = st.columns(4)

    # ── [Column 1] 4단위 ──
    with col1:
        st.markdown("### 1️⃣ 4단위 (호)")
        if not ranked_4:
            st.write("결과 없음")
        else:
            for idx, item in enumerate(ranked_4[:3]):
                code = item['hs_code']
                name = item['name_kr']
                score = item.get('score', 0)
                label = f"[{code}] {name}"

                is_selected = (st.session_state.hs_sel_4 == code)
                btn_type = "primary" if is_selected else "secondary"

                if st.button(label, key=f"btn_4_{code}", type=btn_type, use_container_width=True):
                    if is_selected:
                        st.session_state.hs_sel_4 = None
                        st.session_state.hs_sel_6 = None
                        st.session_state.hs_sel_789 = None
                        st.session_state.hs_sel_10 = None
                    else:
                        st.session_state.hs_sel_4 = code
                        st.session_state.hs_sel_6 = None
                        st.session_state.hs_sel_789 = None
                        st.session_state.hs_sel_10 = None
                        st.session_state.hs_desc_4 = name
                    st.rerun()

    # ── [Column 2] 5,6단위 ──
    with col2:
        st.markdown("### 2️⃣ 5,6단위 (소호)")
        sel_4 = st.session_state.hs_sel_4

        if sel_4:
            if sel_4 in skip_6_codes:
                st.caption(f"ⓘ 해당 품목은 6단위 분류가 없으며, 4단위에서 8단위로 직접 분기됩니다.")
            else:
                items_6 = ranked_6_map.get(sel_4, [])
                if not items_6:
                    mask = (hs_df['HS부호'].str[:4] == sel_4) & (hs_df['code_len'].isin([5, 6]))
                    df_6 = hs_df[mask].sort_values('HS부호')
                    for _, row in df_6.iterrows():
                        items_6.append({
                            'hs_code': row['HS부호'],
                            'name_kr': row['한글품목명'],
                            'is_gita': row['한글품목명'].strip() == '기타',
                        })

                if not items_6:
                    st.write("하위 코드 없음")
                else:
                    for item in items_6:
                        code = item['hs_code']
                        name = item['name_kr']
                        is_gita = item.get('is_gita', False)

                        # HS코드 양식 적용 (예: 871200 → 8712.00)
                        formatted_code = format_hs_code(code)
                        label = f"[{formatted_code}] {name}"

                        is_selected = (st.session_state.hs_sel_6 == code)
                        btn_type = "primary" if is_selected else "secondary"

                        if st.button(label, key=f"btn_6_{code}", type=btn_type, use_container_width=True):
                            if is_selected:
                                st.session_state.hs_sel_6 = None
                                st.session_state.hs_sel_789 = None
                                st.session_state.hs_sel_10 = None
                            else:
                                st.session_state.hs_sel_6 = code
                                st.session_state.hs_sel_789 = None
                                st.session_state.hs_sel_10 = None
                            st.rerun()
        else:
            st.write("← 4단위를 먼저 선택하세요.")

    # ── [Column 3] 7,8,9단위 (신규 추가) ──
    with col3:
        st.markdown("### 3️⃣ 7,8,9단위")
        sel_4 = st.session_state.hs_sel_4
        sel_6 = st.session_state.hs_sel_6
        
        # 7,8,9단위 존재 여부 확인을 위한 부모 코드 결정
        parent_for_789 = None
        if sel_4 and sel_4 in skip_6_codes:
            parent_for_789 = sel_4
        elif sel_6:
            parent_for_789 = sel_6
        
        if parent_for_789:
            # 7,8,9단위 데이터 조회
            p_len = len(parent_for_789)
            mask_789 = (hs_df['HS부호'].str[:p_len] == parent_for_789) & (hs_df['code_len'].isin([7, 8, 9]))
            df_789 = hs_df[mask_789].sort_values('HS부호')
            
            if df_789.empty:
                st.caption("ⓘ 해당 품목은 8단위 분류가 없으며, 6단위에서 10단위로 직접 분기됩니다.")

            else:
                items_789 = []
                for _, row in df_789.iterrows():
                    items_789.append({
                        'hs_code': row['HS부호'],
                        'name_kr': row['한글품목명'],
                        'code_len': row['code_len'],
                    })
                
                for item in items_789:
                    code = item['hs_code']
                    name = item['name_kr']
                    code_len = item['code_len']
                    
                    # HS코드 양식 적용
                    if code_len == 7:
                        formatted_code = f"{code[:4]}.{code[4:6]}.{code[6]}"
                    elif code_len == 8:
                        formatted_code = f"{code[:4]}.{code[4:6]}-{code[6:]}"
                    elif code_len == 9:
                        formatted_code = f"{code[:4]}.{code[4:6]}-{code[6:]}"
                    else:
                        formatted_code = code
                    
                    label = f"[{formatted_code}] {name}"
                    
                    is_selected = (st.session_state.hs_sel_789 == code)
                    btn_type = "primary" if is_selected else "secondary"
                    
                    if st.button(label, key=f"btn_789_{code}", type=btn_type, use_container_width=True):
                        if is_selected:
                            st.session_state.hs_sel_789 = None
                            st.session_state.hs_sel_10 = None
                        else:
                            st.session_state.hs_sel_789 = code
                            st.session_state.hs_sel_10 = None
                        st.rerun()
        else:
            if sel_4 and sel_4 not in skip_6_codes:
                st.write("← 6단위를 먼저 선택하세요.")
            elif not sel_4:
                st.write("← 4단위를 먼저 선택하세요.")

    # ── [Column 4] 10단위 ──
    with col4:
        st.markdown("### 4️⃣ 10단위 (세번)")
        sel_4 = st.session_state.hs_sel_4
        sel_6 = st.session_state.hs_sel_6
        sel_789 = st.session_state.hs_sel_789

        # 10단위 조회를 위한 부모 코드 결정 (우선순위: 789 > 6 > 4)
        parent_for_10 = None
        if sel_789:
            parent_for_10 = sel_789
        elif sel_6:
            # 7,8,9단위가 있는지 확인
            p_len = len(sel_6)
            mask_789_check = (hs_df['HS부호'].str[:p_len] == sel_6) & (hs_df['code_len'].isin([7, 8, 9]))
            if hs_df[mask_789_check].empty:
                # 7,8,9단위가 없으면 6단위에서 바로 10단위로
                parent_for_10 = sel_6
        elif sel_4 and sel_4 in skip_6_codes:
            parent_for_10 = sel_4

        if parent_for_10:
            items_10 = ranked_10_map.get(parent_for_10, [])
            if not items_10:
                p_len = len(parent_for_10)
                mask = (hs_df['HS부호'].str[:p_len] == parent_for_10) & (hs_df['code_len'] == 10)
                df_10 = hs_df[mask].sort_values('HS부호')
                for _, row in df_10.iterrows():
                    items_10.append({
                        'hs_code': row['HS부호'],
                        'name_kr': row['한글품목명'],
                        'is_gita': False,
                    })

            if not items_10:
                st.write("하위 코드 없음")
            else:
                # [2-5] 10단위 품목 키워드 추출 함수
                def extract_distinguishing_keyword(name: str, all_names: list) -> str:
                    """10단위 품목명에서 구분 키워드 추출"""
                    # 공통 키워드 목록 (제외할 단어)
                    common_words = {'것', '한정', '해당', '제외', '포함', '의', '및', '기타', '따른', '이외'}
                    
                    # 키워드 패턴 (우선순위 순)
                    keyword_patterns = [
                        # 상태/가공 관련
                        ('냉동', '🧊'), ('냉장', '❄️'), ('건조', '🌾'), ('훈제', '🔥'),
                        ('신선', '🌿'), ('생것', '🥬'), ('날것', '🥩'), ('조리', '🍳'),
                        ('가공', '⚙️'), ('미가공', '📦'), ('정제', '✨'), ('조제', '🧪'),
                        # 형태 관련
                        ('분쇄', '🔨'), ('분말', '🧂'), ('액상', '💧'), ('고체', '🧱'),
                        ('절단', '✂️'), ('통째', '🔵'), ('조각', '🧩'), ('필렛', '🐟'),
                        # 용도/특성 관련
                        ('식용', '🍽️'), ('사료용', '🐄'), ('공업용', '🏭'), ('의료용', '🏥'),
                        ('산업용', '🏗️'), ('가정용', '🏠'), ('휴대용', '📱'),
                        # 포장/단위 관련
                        ('소매용', '🛒'), ('벌크', '📦'), ('세트', '📦'),
                    ]
                    
                    name_lower = name.lower()
                    
                    # 패턴 매칭으로 키워드 추출
                    for pattern, emoji in keyword_patterns:
                        if pattern in name_lower or pattern in name:
                            return f"{emoji}{pattern}"
                    
                    # 패턴 매칭 실패 시 첫 번째 특징적 단어 추출
                    words = name.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
                    for word in words:
                        if len(word) >= 2 and word not in common_words:
                            # 다른 품목명에는 없는 고유 단어 찾기
                            unique = True
                            for other_name in all_names:
                                if other_name != name and word in other_name:
                                    unique = False
                                    break
                            if unique:
                                return f"📌{word}"
                    
                    return ""
                
                for item in items_10:
                    code = item['hs_code']
                    name = item['name_kr']
                    is_gita = item.get('is_gita', False)

                    # HS코드 양식 적용 (예: 8712009090 → 8712.00-9090)
                    formatted_code = format_hs_code(code)
                    label = f"[{formatted_code}] {name}"

                    is_selected = (st.session_state.hs_sel_10 == code)
                    btn_type = "primary" if is_selected else "secondary"

                    if st.button(label, key=f"btn_10_{code}", type=btn_type, use_container_width=True):
                        if is_selected:
                            st.session_state.hs_sel_10 = None
                        else:
                            st.session_state.hs_sel_10 = code
                        st.rerun()

                if st.session_state.hs_sel_10:
                    sel_10 = st.session_state.hs_sel_10
                    gita_check, gita_parent, gita_type = is_gita_code(sel_10)


        else:
            # 안내 메시지 개선
            if sel_6:
                # 7,8,9단위가 있는지 확인
                p_len = len(sel_6)
                mask_789_check = (hs_df['HS부호'].str[:p_len] == sel_6) & (hs_df['code_len'].isin([7, 8, 9]))
                if not hs_df[mask_789_check].empty:
                    st.write("← 7,8,9단위를 먼저 선택하세요.")
                else:
                    st.write("조회 중...")
            elif sel_4 and sel_4 not in skip_6_codes:
                st.write("← 6단위를 먼저 선택하세요.")
            elif not sel_4:
                st.write("← 4단위를 먼저 선택하세요.")

    # ══════════════════════════════════════════
    # 최종 결과 + 세관장확인 + 간이세액환급대상 + 관세율
    # ══════════════════════════════════════════
    if st.session_state.hs_sel_10:
        st.divider()
        final_code = st.session_state.hs_sel_10
        final_row = hs_df[hs_df['HS부호'] == final_code]
        final_name = final_row.iloc[0]['한글품목명'] if not final_row.empty else ''

        # HS코드 양식 적용 (예: 8712009090 → 8712.00-9090)
        formatted_final_code = format_hs_code(final_code)
        st.markdown(f"""
        <div style="
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 0.25rem;
            padding: 0.75rem 1.25rem;
            margin: 1rem 0;
        ">
            <span style="font-size: 1.25rem; color: #155724;">
                🎯 <strong>선택된 HS Code: {formatted_final_code} — {final_name}</strong>
            </span>
        </div>
        """, unsafe_allow_html=True)

        # 두 개의 컬럼으로 세관장확인 + 간이세액환급 표시
        info_col1, info_col2 = st.columns(2)
        
        # 세관장확인 대상 여부
        customs_result = check_customs_confirmation(final_code)
        
        with info_col1:
            st.markdown("#### 🛃 세관장확인 대상 여부")
            if customs_result.get('is_subject'):
                st.error("🔴 **세관장확인 대상 품목입니다!**")

                for cat_info in customs_result.get('categories', []):
                    with st.expander(f"📋 {cat_info['category']} — {cat_info['agency']}", expanded=True):
                        st.write(f"**확인기관:** {cat_info['agency']}")
                        st.write(f"**관련 법령:** {cat_info['law']}")

                        st.write("**필요 서류:**")
                        for doc in cat_info.get('documents', []):
                            st.write(f"  • {doc}")

                        if cat_info.get('conditions'):
                            st.info(f"📌 **조건/비고:** {cat_info['conditions']}")

                        if cat_info.get('contact'):
                            st.caption(f"📞 문의: {cat_info['contact']}")

                st.caption("※ 이 정보는 참고용이며, 정확한 요건은 관세청 또는 해당 기관에 확인하시기 바랍니다.")
            else:
                st.success("🟢 **세관장확인 대상 품목이 아닙니다.**")
                st.caption(customs_result.get('disclaimer', '※ 참고용 정보입니다.'))
        
        # 간이세액환급대상 여부
        with info_col2:
            st.markdown("#### 💰 간이세액환급대상 여부")
            refund_result = check_simple_refund_eligibility(final_code)
            
            if refund_result.get('is_eligible'):
                st.success(f"🟢 **{refund_result['message']}**")
                if refund_result.get('item_name'):
                    st.write(f"**환급률표 품명:** {refund_result['item_name']}")
                if refund_result.get('refund_rate', 0) > 0:
                    st.metric("1만원당 환급액", f"₩{int(refund_result['refund_rate']):,}")
                    st.caption("※ 수출 시 원재료 수입 관세 간이환급 대상")
            else:
                st.info(f"ℹ️ {refund_result['message']}")
                st.caption("※ 간이세액환급률표에 등재된 품목만 환급 대상입니다.")

        if st.button("📊 관세율 분석하기", key="btn_tariff_analysis", type="primary", use_container_width=True):
            # 대상국 정보 전달
            target_country = st.session_state.get('target_country', '')
            analysis = analyze_tariff_rates(final_code, target_country)
            st.session_state['temp_analysis'] = analysis
            st.session_state['temp_target_country'] = target_country

    if 'temp_analysis' in st.session_state:
        display_tariff_analysis(
            st.session_state['temp_analysis'],
            st.session_state.get('temp_target_country', '')
        )


def display_tariff_analysis(analysis, target_country=''):
    """
    관세율 분석 결과 표시 (무역 실무 기준 우선순위 적용)
    
    ★ 수정된 우선순위 ★
    - 1순위 (무조건 적용): 덤핑방지관세, 보복관세, 긴급관세, 상계관세 등
    - 2순위 (혜택 선택): FTA 협정세율 (원산지증명서 필수)
    - 3순위 (정책적 조정): 조정관세, 할당관세, 계절관세
    - 4순위 (기본): WTO 양허세율(C) vs 기본세율(A) 중 더 낮은 세율 자동 적용
    
    ★ 최저세율 계산 알고리즘 ★
    Step 1: 1순위(덤핑/보복/긴급) 있는가? → YES: 무조건 적용, 종료
    Step 2: 2,3,4순위 중 최저세율 찾기
    Step 3: 3순위(조정관세)가 2순위(FTA)보다 높으면 → 3순위 강제 적용
    """
    try:
        st.markdown("---")
        st.subheader("📊 관세율 분석 결과")
        
        if not analysis:
            st.warning("분석 데이터가 없습니다.")
            return
        
        # 대상국 정보 표시
        if target_country:
            st.info(f"🌍 분석 대상국: **{target_country}**")
        else:
            st.info("🌍 전체 국가 기준 (Global MIN)")
        
        # FTA 국가 매핑
        FTA_COUNTRIES = {
            "FCL": ["CL"], "FSG": ["SG"], "FEF": ["CH", "NO", "IS", "LI"],
            "FAS": ["BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN"],
            "FIN": ["IN"], "FPE": ["PE"], "FUS": ["US"], "FTR": ["TR"],
            "FAU": ["AU"], "FCA": ["CA"], "FCN": ["CN"], "FNZ": ["NZ"],
            "FVN": ["VN"], "FCO": ["CO"], "FGB": ["GB"], "FIL": ["IL"],
            "FKH": ["KH"], "FID": ["ID"], "FPH": ["PH"],
            "FEU": ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", 
                   "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", 
                   "PL", "PT", "RO", "SK", "SI", "ES", "SE"],
            "FRC": ["AU", "BN", "KH", "CN", "ID", "JP", "LA", "MY", "MM", "NZ", 
                   "PH", "SG", "TH", "VN"],
        }
        
        def is_fta_applicable(fta_code, country):
            """해당 FTA가 특정 국가에 적용되는지 확인"""
            if not country:
                return True  # 전체 국가면 모두 표시
            fta_base = ''.join([c for c in fta_code if not c.isdigit()])
            return country in FTA_COUNTRIES.get(fta_base, [])
        
        # ═══════════════════════════════════════════
        # 우선순위별 관세율 분류 (수정된 알고리즘)
        # ═══════════════════════════════════════════
        
        # 1순위: 덤핑방지관세(D), 보복관세(R), 긴급관세(G), 상계관세(Q), 농긴급관세(T)
        priority_1_mandatory = []
        
        # 2순위: FTA 협정관세 (원산지증명서 필수)
        priority_2_fta = []
        priority_2_fta_not_applicable = []
        
        # 3순위: 조정관세(C), 할당관세(H), 계절관세(S)
        priority_3_adjustment = []
        
        # 4순위: 기본세율(A), WTO양허세율(U/W)
        priority_4_basic = []
        
        # 기타 참고용
        other_tariffs = []
        
        # 기본세율 및 WTO 세율 추출
        basic_rate = None
        wto_rate = None
        
        if analysis.get('basic_tariff'):
            basic_rate = analysis['basic_tariff'].get('tariff_rate', 0)
            priority_4_basic.append({
                'name': '기본관세(A)',
                'rate': basic_rate,
                'type': 'A'
            })
        
        if analysis.get('wto_tariff'):
            wto_rate = analysis['wto_tariff'].get('tariff_rate', 0)
            priority_4_basic.append({
                'name': 'WTO양허세율(C)',
                'rate': wto_rate,
                'type': 'C'
            })
        
        # FTA 분석
        fta_list = analysis.get('fta_tariffs', [])
        for fta in fta_list:
            fta_code = fta.get('tariff_type', '')
            rate = fta.get('tariff_rate', 0)
            name = fta.get('tariff_type_name', fta_code)
            
            if is_fta_applicable(fta_code, target_country):
                priority_2_fta.append({
                    'name': name,
                    'code': fta_code,
                    'rate': rate,
                    'applicable': True
                })
            else:
                priority_2_fta_not_applicable.append({
                    'name': name,
                    'code': fta_code,
                    'rate': rate,
                    'applicable': False
                })
        
        # 특별관세 분류
        special_list = analysis.get('special_tariffs', [])
        for sp in special_list:
            sp_type = sp.get('tariff_type', '')
            rate = sp.get('tariff_rate', 0)
            name = sp.get('tariff_type_name', sp_type)
            
            # 1순위: 덤핑방지(D), 보복(R), 긴급(G), 상계(Q), 농긴급(T)
            # ★ 0% 가산관세는 "미적용"을 의미하므로 제외 ★
            if sp_type and sp_type[0] in ['D', 'R', 'G', 'Q', 'T']:
                # 0%인 가산관세는 실제로 적용되지 않으므로 1순위에서 제외
                if rate == 0 or rate == 0.0:
                    continue  # 0% 가산관세는 스킵
                priority_1_mandatory.append({
                    'name': name,
                    'rate': rate,
                    'type': sp_type
                })
            # 3순위: 조정(C - 단 FTA가 아닌 것), 할당(H), 계절(S)
            elif sp_type and sp_type[0] in ['C', 'H', 'S']:
                priority_3_adjustment.append({
                    'name': name,
                    'rate': rate,
                    'type': sp_type
                })
            # 기타: 잠정세율(P/B), 국제협력(I), 최빈국(L), APTA(E) 등
            else:
                other_tariffs.append({
                    'name': name,
                    'rate': rate,
                    'type': sp_type
                })
        
        # ═══════════════════════════════════════════
        # 최저 적용세율 계산 (수정된 알고리즘)
        # ═══════════════════════════════════════════
        
        applied_tariff = None
        applied_reason = ""
        has_mandatory = len(priority_1_mandatory) > 0
        
        # Step 1: 1순위 체크 (덤핑/보복/긴급 관세)
        if has_mandatory:
            # 1순위가 있으면 무조건 적용 (다른 비교 불가)
            mandatory_item = priority_1_mandatory[0]
            applied_tariff = {
                'name': mandatory_item['name'],
                'rate': mandatory_item['rate'],
                'reason': '1순위 무조건 적용 (법적 강제)'
            }
            applied_reason = "⚠️ 1순위 관세(덤핑방지/보복/긴급 등)가 존재하여 무조건 적용됩니다."
        else:
            # Step 2: 2,3,4순위 중 최저세율 찾기
            candidates = []
            
            # 2순위: FTA (원산지증명서 보유 가정)
            for fta in priority_2_fta:
                if isinstance(fta['rate'], (int, float)):
                    candidates.append({
                        'name': fta['name'],
                        'rate': fta['rate'],
                        'priority': 2,
                        'note': '원산지증명서(C/O) 필수'
                    })
            
            # 3순위: 조정/할당/계절 관세
            for adj in priority_3_adjustment:
                if isinstance(adj['rate'], (int, float)):
                    candidates.append({
                        'name': adj['name'],
                        'rate': adj['rate'],
                        'priority': 3,
                        'note': '정책적 조정세율'
                    })
            
            # 4순위: 기본(A) vs WTO(C) 중 낮은 것
            if basic_rate is not None and wto_rate is not None:
                if basic_rate <= wto_rate:
                    candidates.append({
                        'name': '기본관세(A)',
                        'rate': basic_rate,
                        'priority': 4,
                        'note': '기본세율 적용'
                    })
                else:
                    candidates.append({
                        'name': 'WTO양허세율(C)',
                        'rate': wto_rate,
                        'priority': 4,
                        'note': 'WTO 양허세율 적용'
                    })
            elif basic_rate is not None:
                candidates.append({
                    'name': '기본관세(A)',
                    'rate': basic_rate,
                    'priority': 4,
                    'note': '기본세율 적용'
                })
            elif wto_rate is not None:
                candidates.append({
                    'name': 'WTO양허세율(C)',
                    'rate': wto_rate,
                    'priority': 4,
                    'note': 'WTO 양허세율 적용'
                })
            
            if candidates:
                # 최저세율 찾기
                lowest = min(candidates, key=lambda x: x['rate'])
                
                # Step 3: 우선순위 역전 체크
                # 3순위(조정관세)가 2순위(FTA)보다 세율이 높으면 3순위 강제 적용
                fta_rates = [c['rate'] for c in candidates if c['priority'] == 2]
                adj_rates = [c['rate'] for c in candidates if c['priority'] == 3]
                
                if fta_rates and adj_rates:
                    min_fta = min(fta_rates)
                    max_adj = max(adj_rates)  # 조정관세 중 가장 높은 것
                    
                    if max_adj > min_fta:
                        # 조정관세가 FTA보다 높으면 조정관세 강제 적용
                        adj_item = next(c for c in candidates if c['priority'] == 3 and c['rate'] == max_adj)
                        applied_tariff = {
                            'name': adj_item['name'],
                            'rate': adj_item['rate'],
                            'reason': '3순위 강제 적용 (조정관세 > FTA)'
                        }
                        applied_reason = f"⚠️ 조정관세({max_adj}%)가 FTA({min_fta}%)보다 높아 법적으로 조정관세가 강제 적용됩니다."
                    else:
                        applied_tariff = {
                            'name': lowest['name'],
                            'rate': lowest['rate'],
                            'reason': lowest['note']
                        }
                        if lowest['priority'] == 2:
                            applied_reason = f"✅ FTA 협정세율 적용 (원산지증명서 필요)"
                        else:
                            applied_reason = f"✅ {lowest['note']}"
                else:
                    applied_tariff = {
                        'name': lowest['name'],
                        'rate': lowest['rate'],
                        'reason': lowest['note']
                    }
                    if lowest['priority'] == 2:
                        applied_reason = f"✅ FTA 협정세율 적용 (원산지증명서 필요)"
                    else:
                        applied_reason = f"✅ {lowest['note']}"
        
        # ═══════════════════════════════════════════
        # 결과 표시
        # ═══════════════════════════════════════════
        
        # 최저 적용세율 표시
        if applied_tariff:
            if has_mandatory:
                st.error(f"🚨 **적용 세율: {applied_tariff['name']} - {applied_tariff['rate']}%**")
                st.warning(applied_reason)
            else:
                st.success(f"⭐ **최저 적용세율: {applied_tariff['name']} - {applied_tariff['rate']}%**")
                st.info(applied_reason)
        
        st.markdown("#### 📋 관세율 상세 (우선순위순)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # 1순위: 가산관세 (무조건 적용)
        with col1:
            st.markdown("**🔴 1순위**")
            st.caption("덤핑방지/보복/긴급관세")
            if priority_1_mandatory:
                for item in priority_1_mandatory:
                    st.error(f"• {item['name']}: **{item['rate']}%**")
                st.caption("⚠️ 무조건 적용")
            else:
                st.success("해당 없음 ✓")
        
        # 2순위: FTA 협정관세
        with col2:
            st.markdown("**🟢 2순위**")
            st.caption("FTA 협정세율")
            if priority_2_fta:
                for item in priority_2_fta:
                    st.write(f"• {item['name']}: **{item['rate']}%**")
                st.caption("📋 원산지증명서(C/O) 필수")
            else:
                st.caption("적용 가능한 FTA 없음")
            
            if priority_2_fta_not_applicable:
                with st.expander(f"미적용 FTA ({len(priority_2_fta_not_applicable)}건)", expanded=False):
                    for item in priority_2_fta_not_applicable:
                        st.caption(f"• {item['name']}: {item['rate']}% (적용x)")
        
        # 3순위: 조정관세
        with col3:
            st.markdown("**🟡 3순위**")
            st.caption("조정/할당/계절관세")
            if priority_3_adjustment:
                for item in priority_3_adjustment:
                    st.write(f"• {item['name']}: **{item['rate']}%**")
                st.caption("📌 정부 정책 조정")
            else:
                st.caption("해당 없음")
        
        # 4순위: 기본세율
        with col4:
            st.markdown("**🔵 4순위**")
            st.caption("기본(A) vs WTO(C)")
            if priority_4_basic:
                for item in priority_4_basic:
                    st.write(f"• {item['name']}: **{item['rate']}%**")
                # 둘 중 낮은 것 표시
                if basic_rate is not None and wto_rate is not None:
                    lower = min(basic_rate, wto_rate)
                    st.caption(f"→ 낮은 세율 {lower}% 적용")
            else:
                st.caption("세율 정보 없음")
        
        # 기타 참고 세율
        if other_tariffs:
            with st.expander("📎 기타 참고 세율", expanded=False):
                for item in other_tariffs:
                    st.write(f"• {item['name']}: {item['rate']}%")
        
        st.divider()
        st.markdown("##### 📖 관세율 적용 규칙")
        st.markdown("""
        1. **1순위(덤핑방지/보복/긴급관세)** 가 있으면 → 무조건 해당 세율 적용 (다른 세율과 비교 불가)
        2. **1순위가 없으면** → 2순위(FTA), 3순위(조정관세), 4순위(기본/WTO) 중 **최저세율** 적용
        3. **단, 3순위(조정관세) > 2순위(FTA)** 인 경우 → 3순위 강제 적용 (법적 강제)
        4. **FTA 적용 시** → 원산지증명서(C/O) 반드시 필요
        """)
        st.caption("※ 정확한 세율은 관세청 UNI-PASS 또는 관세사에게 확인하세요.")
        
    except Exception as e:
        st.error(f"관세율 표시 중 오류: {e}")



def page_calendar():
    st.title("📅 캘린더 및 일정 관리")
    
    from modules.calendar import DeadlineTracker, set_export_deadline, set_import_deadline, get_dday
    from api.google_calendar import GoogleCalendarAPI
    import calendar
    from datetime import datetime, timedelta
    
    # Google Calendar API 초기화
    cal = GoogleCalendarAPI()
    
    # ================================================================
    # Session State 초기화
    # ================================================================
    if 'local_events' not in st.session_state:
        st.session_state.local_events = []
    
    if 'current_year' not in st.session_state:
        st.session_state.current_year = datetime.now().year
    
    if 'current_month' not in st.session_state:
        st.session_state.current_month = datetime.now().month
    
    # ================================================================
    # Google Calendar 연동 상태
    # ================================================================
    if not cal.is_connected():
        st.warning("⚠️ Google Calendar가 연결되어 있지 않습니다. (로컬 캘린더는 사용 가능)")

    # ================================================================
    # 탭 구성
    # ================================================================
    tab1, tab2 = st.tabs([
        "📆 캘린더 뷰",
        "➕ 일정 추가"
    ])
    
    # ================================================================
    # Tab 1: 캘린더 뷰
    # ================================================================
    with tab1:
        # ------ 상단: 월 네비게이션 ------
        col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 4, 1, 1])
        
        with col_nav1:
            if st.button("◀ 이전", key="prev_month", use_container_width=True):
                if st.session_state.current_month == 1:
                    st.session_state.current_month = 12
                    st.session_state.current_year -= 1
                else:
                    st.session_state.current_month -= 1
                st.rerun()
        
        with col_nav2:
            if st.button("📍 오늘", key="today_btn", use_container_width=True):
                st.session_state.current_year = datetime.now().year
                st.session_state.current_month = datetime.now().month
                st.rerun()
        
        with col_nav3:
            st.markdown(f"""
            <h2 style='
                text-align: center; 
                font-size: 32px; 
                font-weight: 700; 
                color: #1a1a1a;
                margin: 10px 0;
            '>
                {st.session_state.current_year}년 {st.session_state.current_month}월
            </h2>
            """, unsafe_allow_html=True)
        
        with col_nav5:
            if st.button("다음 ▶", key="next_month", use_container_width=True):
                if st.session_state.current_month == 12:
                    st.session_state.current_month = 1
                    st.session_state.current_year += 1
                else:
                    st.session_state.current_month += 1
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ------ 캘린더 데이터 준비 ------
        year = st.session_state.current_year
        month = st.session_state.current_month
        
        first_day = datetime(year, month, 1)
        last_day_num = calendar.monthrange(year, month)[1]
        first_weekday = first_day.weekday()
        
        # ------ CSS 스타일 ------
        st.markdown("""
        <style>
        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 2px;
            background-color: #e0e0e0;
            border: 2px solid #bdbdbd;
            border-radius: 8px;
            overflow: hidden;
        }
        .calendar-cell {
            background-color: white;
            min-height: 120px;
            padding: 12px;
            position: relative;
        }
        .calendar-header {
            background-color: #f5f5f5;
            padding: 12px;
            text-align: center;
            font-weight: 700;
            font-size: 16px;
            border-bottom: 2px solid #bdbdbd;
        }
        .day-number {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .today-cell {
            background-color: #fff3e0 !important;
            border: 2px solid #ff9800;
        }
        .event-badge {
            font-size: 13px;
            padding: 4px 8px;
            margin: 3px 0;
            border-radius: 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-weight: 500;
        }
        .dday-badge {
            font-size: 15px;
            font-weight: 700;
            padding: 0;
            display: inline-block;
            margin: 2px 0;
        }
        .dday-urgent { color: #d32f2f; }
        .dday-warning { color: #f57c00; }
        .dday-normal { color: #2e7d32; }
        /* 일정 라벨 색상은 event_type별 inline style로 처리 */
        </style>
        """, unsafe_allow_html=True)
        
        # ------ 요일 헤더 ------
        weekdays = ["일", "월", "화", "수", "목", "금", "토"]
        weekday_colors = ["#d32f2f", "#424242", "#424242", "#424242", "#424242", "#424242", "#1976d2"]
        
        # ------ 일정 데이터 수집 ------
        events_by_date = {}
        
        # Google Calendar 일정
        if cal.is_connected():
            try:
                google_events = cal.get_events(max_results=100)
                for e in google_events:
                    event_date = e['start'][:10]
                    if event_date not in events_by_date:
                        events_by_date[event_date] = []
                    events_by_date[event_date].append({
                        'title': e['title'],
                        'description': e.get('description', ''),
                        'source': 'google',
                        'event_type': _classify_event_type(e['title'])
                    })
            except:
                pass
        
        # 로컬 일정
        for local_evt in st.session_state.local_events:
            event_date = local_evt['date']
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append({
                'title': local_evt['title'],
                'description': local_evt.get('description', ''),
                'source': 'local',
                'event_type': local_evt.get('event_type', 'general')
            })
        
        # ------ 마감일 D-Day 계산용 (형광펜 범위 계산 제거됨) ------
        today = datetime.now().date()
        
        # ------ 캘린더 그리드 렌더링 ------
        header_html = "<div class='calendar-grid'>"
        
        # 요일 헤더
        for i, day_name in enumerate(weekdays):
            color = weekday_colors[i]
            header_html += f"<div class='calendar-header' style='color: {color};'>{day_name}</div>"
        
        # 첫 주의 빈 칸 (일요일 시작: weekday() + 1 mod 7)
        first_weekday_sunday = (first_weekday + 1) % 7
        for _ in range(first_weekday_sunday):
            header_html += "<div class='calendar-cell' style='background-color: #fafafa;'></div>"
        
        # 날짜 칸들
        for day_num in range(1, last_day_num + 1):
            current_date = datetime(year, month, day_num).date()
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 오늘 날짜 체크
            is_today = (current_date == today)
            
            # 기본 셀 클래스
            cell_class = "calendar-cell"
            if is_today:
                cell_class += " today-cell"
            
            # 형광펜 클래스 제거됨 - 라벨 색상으로 수입/수출 구분
            
            # 주말 체크 (일요일=빨강, 토요일=파랑)
            weekday_idx = current_date.weekday()
            day_color = "#d32f2f" if weekday_idx == 6 else "#1976d2" if weekday_idx == 5 else "#333"
            
            header_html += f"<div class='{cell_class}'>"
            header_html += f"<div class='day-number' style='color: {day_color};'>{day_num}</div>"
            
            # 해당 날짜의 일정 표시
            if date_str in events_by_date:
                for evt in events_by_date[date_str]:
                    # D-Day 계산 (마감일 당일만)
                    if evt['event_type'] in ['export', 'import']:
                        try:
                            dday = (current_date - today).days
                            
                            if dday < 0:
                                dday_text = f"D+{abs(dday)}"
                                dday_class = ""
                            elif dday == 0:
                                dday_text = "D-Day"
                                dday_class = "dday-urgent"
                            elif dday <= 3:
                                dday_text = f"D-{dday}"
                                dday_class = "dday-urgent"
                            elif dday <= 7:
                                dday_text = f"D-{dday}"
                                dday_class = "dday-warning"
                            else:
                                dday_text = f"D-{dday}"
                                dday_class = "dday-normal"
                            
                            # 형광펜 스타일 D-Day
                            header_html += f"<div class='dday-badge {dday_class}'>{dday_text}</div>"
                        except:
                            pass
                    
                    # 일정 제목
                    event_color = _get_event_color(evt['event_type'])
                    border_color = _get_event_border_color(evt['event_type'])
                    emoji = _get_event_emoji(evt['event_type'])
                    
                    short_title = evt['title'][:12] + "..." if len(evt['title']) > 12 else evt['title']
                    # HTML 특수문자 escape 처리
                    safe_title = html.escape(short_title)

                    header_html += f"<div class='event-badge' style='background-color: {event_color}; border-left: 4px solid {border_color};'>{emoji} {safe_title}</div>"
            
            header_html += "</div>"
        
        # 마지막 주의 빈 칸
        last_date = datetime(year, month, last_day_num)
        remaining_cells = 6 - last_date.weekday()
        for _ in range(remaining_cells):
            header_html += "<div class='calendar-cell' style='background-color: #fafafa;'></div>"
        
        header_html += "</div>"
        
        st.markdown(header_html, unsafe_allow_html=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # ------ 하단: 이번 달 일정 목록 (HTML 코드 노출 제거) ------
        st.divider()
        st.markdown("""
        <h3 style='font-size: 24px; font-weight: 700; color: #1a1a1a; margin-top: 30px;'>
            📋 이번 달 전체 일정
        </h3>
        """, unsafe_allow_html=True)
        
        # 이번 달 일정만 필터링
        month_events = []
        for date_str, events in events_by_date.items():
            evt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if evt_date.year == year and evt_date.month == month:
                for evt in events:
                    month_events.append({
                        'date': date_str,
                        'date_obj': evt_date,
                        'title': evt['title'],
                        'description': evt['description'],
                        'type': evt['event_type'],
                        'source': evt['source']
                    })
        
        # 날짜순 정렬
        month_events.sort(key=lambda x: x['date'])
        
        if month_events:
            for evt_idx, evt in enumerate(month_events):
                # D-Day 계산
                try:
                    dday = (evt['date_obj'] - today).days
                    if dday < 0:
                        dday_text = f"D+{abs(dday)}"
                        badge_color = "#9e9e9e"
                    elif dday == 0:
                        dday_text = "D-Day"
                        badge_color = "#d32f2f"
                    elif dday <= 3:
                        dday_text = f"D-{dday}"
                        badge_color = "#d32f2f"
                    elif dday <= 7:
                        dday_text = f"D-{dday}"
                        badge_color = "#f57c00"
                    else:
                        dday_text = f"D-{dday}"
                        badge_color = "#388e3c"
                except:
                    dday_text = ""
                    badge_color = "#666"
                
                # 일정 타입별 이모지
                emoji = _get_event_emoji(evt['type'])
                
                # D-Day 뱃지 (Markdown 형식으로 표시)
                # HTML 특수문자 escape 처리
                safe_evt_title = html.escape(evt['title'])
                if dday_text:
                    expander_title = f"{emoji} **{evt['date']}** | {safe_evt_title} | {dday_text}"
                else:
                    expander_title = f"{emoji} **{evt['date']}** | {safe_evt_title}"
                
                with st.expander(expander_title, expanded=False):
                    # 설명란 - 줄바꿈 처리
                    if evt['description']:
                        # \n을 실제 줄바꿈으로 변환
                        formatted_desc = evt['description'].replace('\\n', '\n')
                        st.text(formatted_desc)
                    else:
                        st.write("설명 없음")
                    
                    # D-Day 정보 (색상 뱃지로 표시)
                    if dday_text:
                        st.markdown(f"""
                        <div style='
                            display: inline-block;
                            background-color: {badge_color}; 
                            color: white; 
                            padding: 4px 12px; 
                            border-radius: 4px; 
                            font-weight: 700; 
                            font-size: 14px; 
                            margin: 10px 0;
                        '>
                            {dday_text}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # 로컬 일정만 삭제 가능
                    if evt['source'] == 'local':
                        if st.button("🗑️ 삭제", key=f"del_{evt_idx}_{evt['date']}"):
                            st.session_state.local_events = [
                                e for e in st.session_state.local_events 
                                if not (e['date'] == evt['date'] and e['title'] == evt['title'])
                            ]
                            st.success("일정이 삭제되었습니다.")
                            st.rerun()
        else:
            st.info("이번 달 일정이 없습니다.")
    
    # ================================================================
    # Tab 2: 일정 추가
    # ================================================================
    with tab2:
        st.markdown("<h3 style='font-size: 24px; font-weight: 700;'>➕ 새 일정 추가</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("add_event_form"):
                event_title = st.text_input("일정 제목", placeholder="예: 고객 미팅, 서류 마감")
                event_date = st.date_input("날짜", value=datetime.now())
                event_type = st.selectbox("일정 유형", [
                    "일반", 
                    "수출 관련", 
                    "수입 관련", 
                     
                    "미팅", 
                    "기타"
                ])
                event_desc = st.text_area("설명 (선택)", height=100, 
                    placeholder="여러 줄 입력 가능\n거래번호: XXX\n품목: XXX\n입항일: XXXX-XX-XX")
                sync_to_google = True if cal.is_connected() else False
                if st.form_submit_button("일정 추가", type="primary", use_container_width=True):
                    if event_title:
                        type_map = {
                            "일반": "general",
                            "수출 관련": "export",
                            "수입 관련": "import",
                            "미팅": "meeting",
                            "기타": "etc"
                        }

                        # Google Calendar 동기화 (성공 시 로컬 저장 안함 - 중복 방지)
                        if sync_to_google and cal.is_connected():
                            try:
                                cal.create_event(
                                    event_title,
                                    datetime.combine(event_date, datetime.min.time()),
                                    description=event_desc
                                )
                                st.success("✅ 일정이 Google Calendar에 동기화되었습니다!")
                            except Exception as e:
                                # Google 실패 시 로컬에 저장
                                st.session_state.local_events.append({
                                    'date': event_date.strftime("%Y-%m-%d"),
                                    'title': event_title,
                                    'description': event_desc,
                                    'event_type': type_map[event_type]
                                })
                                st.warning(f"Google 동기화 실패, 로컬에 저장됨: {e}")
                        else:
                            # Google 미연결 시 로컬에만 저장
                            st.session_state.local_events.append({
                                'date': event_date.strftime("%Y-%m-%d"),
                                'title': event_title,
                                'description': event_desc,
                                'event_type': type_map[event_type]
                            })
                            st.success("✅ 일정이 추가되었습니다!")

                        st.rerun()
                    else:
                        st.warning("일정 제목을 입력하세요.")
        
        with col2:
            st.info("""
            **일정 유형 안내**
            
            - **일반**: 기본 일정
            - **수출 관련**: 수출 업무
            - **수입 관련**: 수입 업무
            - **미팅**: 회의/미팅
            - **기타**: 기타 일정
            
            💡 수출/수입/마감일은 
            자동으로 D-Day가 표시되고
            오늘부터 마감일까지 
            표시됩니다.
            """)

# ================================================================
# 헬퍼 함수들
# ================================================================

def _classify_event_type(title: str) -> str:
    """일정 제목으로 타입 분류"""
    title_lower = title.lower()
    if '[수출]' in title or 'export' in title_lower:
        return 'export'
    if '[수입]' in title or 'import' in title_lower:
        return 'import'
    if '미팅' in title or 'meeting' in title_lower:
        return 'meeting'
    # (카테고리 제거) 마감/데드라인은 별도 분류하지 않고 일반으로 처리
    return 'general'



def _get_event_color(event_type: str) -> str:
    """일정 타입별 배경색"""
    colors = {
        'export': '#e3f2fd',   # 파란색(수출)
        'import': '#e8f5e9',   # 초록색(수입)
        'meeting': '#fff3e0',  # 주황색(미팅)
        'general': '#f5f5f5',  # 회색(일반)
        'etc': '#f5f5f5',      # 회색(기타)
        'deadline': '#f5f5f5'  # (구분 삭제) 회색 처리
    }
    return colors.get(event_type, '#f5f5f5')


def _get_event_border_color(event_type: str) -> str:
    """일정 타입별 좌측 테두리 색"""
    colors = {
        'export': '#1e88e5',   # 파란색
        'import': '#43a047',   # 초록색
        'meeting': '#fb8c00',  # 주황색
        'general': '#9e9e9e',  # 회색
        'etc': '#9e9e9e',      # 회색
        'deadline': '#9e9e9e'  # 회색
    }
    return colors.get(event_type, '#9e9e9e')


def _get_event_emoji(event_type: str) -> str:
    """일정 타입별 이모지"""
    emojis = {
        'export': '📤',
        'import': '📥',
        'deadline': '⏰',
        'meeting': '🤝',
        'general': '📌',
        'etc': '📋'
    }
    return emojis.get(event_type, '📌')

# ==================================================================
# PAGE: 수입 관리 (CIF 계산기 포함 v2.0)
# ==================================================================

def page_import():
    st.title("📥 수입 관리")
    
    # CIF 계산기 모듈 import
    from modules.import_process import (
        render_cif_input_fields,
        render_standalone_cif_calculator,
        calculate_cif_by_incoterms
    )
    
    tab1, tab2, tab3 = st.tabs(["🚀 스마트 서류 등록", "📋 수동 등록", "💰 CIF/과세가격 계산기"])
    
    # [TAB 1] AI Analysis
    with tab1:
        st.write("#### 수입 서류 업로드 (Invoice/BL)")
        uf = st.file_uploader("파일 선택", type=['pdf', 'jpg', 'png', 'jpeg', 'PDF', 'JPG', 'PNG', 'JPEG'], key="imp_uploader_final")
        
        if uf and st.button("🔍 문서 정밀 분석", key="imp_analyze_btn", type="primary"):
            with st.spinner("AI가 문서의 모든 필드를 추출하고 있습니다..."):
                extracted = extract_trade_data_from_doc(uf.read(), uf.name, 'import')
            if 'error' in extracted:
                st.error(extracted['error'])
            else:
                st.session_state.staging_data = extracted
                st.session_state.staging_type = 'import'
                st.rerun()

        # 데이터 검토 (Staging) - 수입용
        if st.session_state.staging_type == 'import' and st.session_state.staging_data:
            st.divider()
            st.markdown("### 2️⃣ 데이터 검토 및 보완 (Staging Area)")
            st.info("📌 AI가 추출한 데이터를 확인하세요. **인도조건에 따라 CIF가 자동 계산됩니다.**")

            data = st.session_state.staging_data
            
            with st.form("import_staging_form"):
                st.markdown("##### 📄 문서 기본 정보")
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    invoice_no = st.text_input("Invoice No.", value=data.get('invoice_no', ''))
                with c_d2:
                    def_date = datetime.now()
                    if data.get('date_info'):
                        try:
                            def_date = datetime.strptime(data.get('date_info'), "%Y-%m-%d")
                        except:
                            pass
                    doc_date = st.date_input("문서 날짜 (Date)", value=def_date)
                
                st.markdown("##### 🏢 거래 당사자")
                c1, c2, c3 = st.columns(3)
                with c1:
                    exporter = st.text_input("수출자 (Exporter)", value=data.get('exporter_name', ''))
                with c2:
                    importer = st.text_input("수입자 (Importer)", value=data.get('importer_name', ''))
                with c3:
                    notify = st.text_input("Notify Party", value=data.get('notify_party', ''))
                
                st.markdown("##### 📦 품목 및 규격")
                c4, c5, c6 = st.columns(3)
                with c4:
                    item_name = st.text_input("품목명", value=data.get('item_name', ''))
                with c5:
                    hs_code = st.text_input("HS Code", value=data.get('hs_code', ''))
                with c6:
                    origin = st.text_input("원산지", value=data.get('country', ''))
                
                # ★★★ CIF 계산 섹션 ★★★
                st.markdown("##### 💰 CIF 및 과세가격 계산")
                st.info("📌 인도조건에 따라 CIF 금액이 자동 계산됩니다.")
                
                def_qty = int(str(data.get('quantity', '0')).replace(',', '').replace('.0', '')) if data.get('quantity') else 0
                def_val = float(str(data.get('total_amount', '0')).replace(',', '')) if data.get('total_amount') else 0.0
                
                c7, c8, c9 = st.columns(3)
                with c7:
                    qty = st.number_input("수량 (Qty)", value=def_qty, key="stg_qty")
                    unit = st.text_input("단위", value=data.get('unit', 'EA'), key="stg_unit")
                with c8:
                    fob_value = st.number_input("물품가액 (FOB 기준)", value=def_val, key="stg_fob", help="Invoice 상의 물품 금액")
                    curr = st.text_input("통화", value=data.get('currency', 'USD'), key="stg_curr")
                with c9:
                    incoterms_options = ["FOB", "CIF", "CFR", "EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP"]
                    default_inco = data.get('incoterms', 'FOB')
                    inco_index = incoterms_options.index(default_inco) if default_inco in incoterms_options else 0
                    inco = st.selectbox("인도조건 (Incoterms)", options=incoterms_options, index=inco_index, key="stg_inco")
                
                # CIF 계산 로직 (Incoterms 조건별)
                freight = 0.0
                insurance = 0.0
                inland_freight = 0.0
                cif_value = fob_value
                
                if inco == "FOB":
                    st.markdown("---")
                    st.caption("🚢 FOB 조건 → 운임(F) + 보험료(I) 입력 필요")
                    c_cif1, c_cif2 = st.columns(2)
                    with c_cif1:
                        freight = st.number_input(f"운임 (Freight) [{curr}]", value=0.0, step=100.0, help="해상/항공 운임", key="stg_freight")
                    with c_cif2:
                        insurance = st.number_input(f"보험료 (Insurance) [{curr}]", value=0.0, step=10.0, help="화물 보험료", key="stg_ins")
                    
                    cif_value = fob_value + freight + insurance
                    st.success(f"💡 **계산된 CIF 금액: {curr} {cif_value:,.2f}** (FOB {fob_value:,.2f} + F {freight:,.2f} + I {insurance:,.2f})")
                
                elif inco == "CFR":
                    st.markdown("---")
                    st.caption("🚢 CFR 조건 → 보험료(I)만 추가 입력")
                    insurance = st.number_input(f"보험료 (Insurance) [{curr}]", value=0.0, step=10.0, key="stg_ins")
                    cif_value = fob_value + insurance
                    st.success(f"💡 **계산된 CIF 금액: {curr} {cif_value:,.2f}** (CFR {fob_value:,.2f} + I {insurance:,.2f})")
                
                elif inco == "CIF":
                    st.success(f"💡 **CIF 조건 → 추가 계산 불필요** (CIF = {curr} {cif_value:,.2f})")
                
                elif inco == "EXW":
                    st.markdown("---")
                    st.warning("⚠️ EXW 조건 → 운임 + 보험료 + 내륙운송비 모두 입력 필요")
                    c_exw1, c_exw2, c_exw3 = st.columns(3)
                    with c_exw1:
                        inland_freight = st.number_input(f"내륙운송비 [{curr}]", value=0.0, step=50.0, key="stg_inland")
                    with c_exw2:
                        freight = st.number_input(f"해상/항공 운임 [{curr}]", value=0.0, step=100.0, key="stg_freight")
                    with c_exw3:
                        insurance = st.number_input(f"보험료 [{curr}]", value=0.0, step=10.0, key="stg_ins")
                    
                    cif_value = fob_value + inland_freight + freight + insurance
                    st.success(f"💡 **계산된 CIF 금액: {curr} {cif_value:,.2f}**")
                
                elif inco in ["FCA", "CPT"]:
                    st.markdown("---")
                    st.caption(f"🚚 {inco} 조건 → 운임 + 보험료 확인 필요")
                    c_fca1, c_fca2 = st.columns(2)
                    with c_fca1:
                        freight = st.number_input(f"추가 운임 [{curr}]", value=0.0, step=100.0, key="stg_freight")
                    with c_fca2:
                        insurance = st.number_input(f"보험료 [{curr}]", value=0.0, step=10.0, key="stg_ins")
                    cif_value = fob_value + freight + insurance
                    st.success(f"💡 **계산된 CIF 금액: {curr} {cif_value:,.2f}**")
                
                elif inco in ["DAP", "DPU", "DDP"]:
                    st.markdown("---")
                    st.info(f"📦 {inco} 조건 → CIF 금액을 수동으로 입력하세요")
                    cif_value = st.number_input(f"CIF 금액 (수동 입력) [{curr}]", value=fob_value, step=100.0, key="stg_manual_cif")
                
                else:
                    st.info(f"'{inco}' 조건 → CIF 금액을 수동으로 입력하거나 조정하세요.")
                    cif_value = st.number_input(f"CIF 금액 (수동 입력) [{curr}]", value=fob_value, step=100.0, key="stg_manual_cif")
                
                st.markdown("##### 🚢 물류 정보")
                c_ship1, c_ship2, c_ship3 = st.columns(3)
                with c_ship1:
                    vessel = st.text_input("선박명", value=data.get('vessel_name', ''), key="stg_vessel")
                with c_ship2:
                    bl_no = st.text_input("B/L No.", value=data.get('bl_number', ''), key="stg_bl")
                with c_ship3:
                    payment_terms = st.text_input("결제조건 (Payment Terms)", value=data.get('payment_terms', ''), key="stg_payment", placeholder="예: T/T, L/C, D/P")

                arrival_date = st.date_input("입항예정일 (ETA)", value=datetime.now(), key="stg_eta")

                if st.form_submit_button("✅ 수입 등록 및 일정 추가", type="primary", use_container_width=True):
                    final_data = {
                        'invoice_no': invoice_no,
                        'exporter_name': exporter,
                        'importer_name': importer,
                        'notify_party': notify,
                        'item_name': item_name,
                        'hs_code': hs_code,
                        'origin_country': origin,
                        'quantity': qty,
                        'unit': unit,
                        'unit_price': fob_value,
                        'currency': curr,
                        'incoterms': inco,
                        'freight': freight,
                        'insurance': insurance,
                        'inland_freight': inland_freight,
                        'cif_value': cif_value,
                        'vessel_name': vessel,
                        'bl_number': bl_no,
                        'payment_terms': payment_terms,
                        'eta_date': arrival_date,
                        'ref_date': doc_date
                    }
                    if one_stop_sync('import', final_data):
                        st.session_state.staging_data = None
                        st.session_state.staging_type = None
                        st.balloons()

    # [TAB 2] 수동 등록
    with tab2:
        st.subheader("📝 수동 등록")
        # 기존 수동 등록 폼
        pf = {}
        with st.form("manual_import_form"):
            c1, c2 = st.columns(2)
            with c1:
                iname = st.text_input("품목명", value=pf.get('item_name', ''))
                hsc = st.text_input("HS Code", value=pf.get('hs_code', ''))
                qty = st.number_input("수량", min_value=1, value=1)
                uprice = st.number_input("단가", value=0.0)
            with c2:
                cur = st.selectbox("통화", ["USD", "EUR", "JPY"])
                ocountry = st.text_input("원산지")
                inco = st.selectbox("무역조건", ["FOB", "CIF", "CFR", "EXW", "DDP"])
                pay_terms = st.text_input("결제조건", placeholder="예: T/T, L/C, D/P")
            if st.form_submit_button("등록 (캘린더 미연동)", type="primary"):
                from modules.master_data import create_trade
                data = {'item_name': iname, 'hs_code': hsc, 'quantity': qty, 'unit_price': uprice,
                        'currency': cur, 'origin_country': ocountry, 'incoterms': inco, 'payment_terms': pay_terms}
                tid = create_trade("import", data)
                st.success(f"등록 완료: {tid}")

    # [TAB 3] 독립 CIF/과세가격 계산기
    with tab3:
        render_standalone_cif_calculator()

# ==================================================================
# PAGE: 수출 관리 (v2.0 - 파일 변환 기능 삭제, 오류 수정)
# ==================================================================

def page_export():
    st.title("📤 수출 관리")
    
    tab1, tab2 = st.tabs(["🚀 스마트 서류 등록", "📋 수동 등록"])
    
    # [TAB 1] 스마트 서류 등록
    with tab1:
        st.write("#### 수출 서류 업로드 (Commercial Invoice)")
        uf = st.file_uploader("파일 선택", type=['pdf', 'jpg', 'png', 'jpeg', 'PDF', 'JPG', 'PNG', 'JPEG'], key="exp_uploader_v2")
        
        if uf and st.button("🔍 문서 정밀 분석", key="exp_analyze_btn_v2", type="primary"):
            with st.spinner("AI가 문서의 모든 필드를 추출하고 있습니다..."):
                extracted = extract_trade_data_from_doc(uf.read(), uf.name, 'export')
            if 'error' in extracted:
                st.error(extracted['error'])
            else:
                st.session_state.staging_data = extracted
                st.session_state.staging_type = 'export'
                st.rerun()

        # 데이터 검토 (Staging) - 수출용
        if st.session_state.staging_type == 'export' and st.session_state.staging_data:
            st.divider()
            st.markdown("### 2️⃣ 데이터 검토 및 보완 (Staging Area)")
            st.info("수출 문서는 관세 정보 입력이 필요 없습니다. 품목과 포장 정보를 확인하세요.")

            data = st.session_state.staging_data
            
            with st.form("export_staging_form_v2"):
                st.markdown("##### 🏢 거래 당사자")
                c1, c2 = st.columns(2)
                with c1:
                    exporter = st.text_input("수출자", value=data.get('exporter_name', ''), key="exp_exporter")
                with c2:
                    importer = st.text_input("수입자", value=data.get('importer_name', ''), key="exp_importer")
                
                st.markdown("##### 📦 품목 및 금액")
                c3, c4, c5 = st.columns(3)
                with c3:
                    item_name = st.text_input("품목명", value=data.get('item_name', ''), key="exp_item")
                with c4:
                    hs_code = st.text_input("HS Code", value=data.get('hs_code', ''), key="exp_hs")
                with c5:
                    dest = st.text_input("목적국", value=data.get('country', ''), key="exp_dest")
                
                def_val = float(str(data.get('total_amount', '0')).replace(',', '')) if data.get('total_amount') else 0.0
                def_qty = int(str(data.get('quantity', '0')).replace(',', '').replace('.0', '')) if data.get('quantity') else 0
                
                c6, c7, c8 = st.columns(3)
                with c6:
                    qty = st.number_input("수량", value=def_qty, key="exp_qty")
                with c7:
                    val = st.number_input("총 금액", value=def_val, key="exp_val")
                with c8:
                    curr = st.text_input("통화", value=data.get('currency', 'USD'), key="exp_curr")

                st.markdown("##### 🚢 물류 및 일정")
                c9, c10, c11 = st.columns(3)
                with c9:
                    inco = st.selectbox("인도조건", options=["FOB", "CIF", "CFR", "EXW", "FCA", "DDP"],
                                       index=0, key="exp_inco")
                with c10:
                    vessel = st.text_input("선박명", value=data.get('vessel_name', ''), key="exp_vessel")
                with c11:
                    payment_terms = st.text_input("결제조건", value=data.get('payment_terms', ''), key="exp_payment", placeholder="예: T/T, L/C, D/P")

                # datetime은 파일 상단에서 이미 import됨
                def_date = datetime.now()
                if data.get('date_info'):
                    try:
                        def_date = datetime.strptime(data['date_info'], "%Y-%m-%d")
                    except:
                        pass
                clearance_date = st.date_input("수출신고 수리일", value=def_date, key="exp_date")

                if st.form_submit_button("✅ 등록 및 일정 추가", type="primary", use_container_width=True):
                    final_data = {
                        'exporter_name': exporter, 'importer_name': importer,
                        'item_name': item_name, 'hs_code': hs_code, 'import_country': dest,
                        'quantity': qty, 'unit_price': val, 'currency': curr,
                        'incoterms': inco, 'vessel_name': vessel,
                        'payment_terms': payment_terms,
                        'ref_date': clearance_date
                    }
                    if one_stop_sync('export', final_data):
                        st.session_state.staging_data = None
                        st.session_state.staging_type = None
                        st.balloons()

    # [TAB 2] 수동 등록
    with tab2:
        st.subheader("📝 수동 등록")
        pf = {}
        with st.form("manual_export_form_v2"):
            c1, c2 = st.columns(2)
            with c1:
                iname = st.text_input("품목명", value=pf.get('item_name', ''), key="man_exp_item")
                hsc = st.text_input("HS Code", value=pf.get('hs_code', ''), key="man_exp_hs")
                qty = st.number_input("수량", min_value=1, value=1, key="man_exp_qty")
                uprice = st.number_input("단가", value=0.0, key="man_exp_price")
            with c2:
                cur = st.selectbox("통화", ["USD", "EUR", "JPY"], key="man_exp_cur")
                icountry = st.text_input("목적국", key="man_exp_country")
                inco = st.selectbox("무역조건", ["FOB", "CIF", "CFR", "EXW", "DDP"], key="man_exp_inco")
                pay_terms = st.text_input("결제조건", placeholder="예: T/T, L/C, D/P", key="man_exp_pay")
            if st.form_submit_button("등록 (캘린더 미연동)", type="primary"):
                from modules.master_data import create_trade
                trade_data = {'item_name': iname, 'hs_code': hsc, 'quantity': qty, 'unit_price': uprice,
                        'currency': cur, 'import_country': icountry, 'incoterms': inco, 'payment_terms': pay_terms}
                tid = create_trade("export", trade_data)
                st.success(f"등록 완료: {tid}")

# ==================================================================
# PAGE: 서류 생성 (app_v11 최신 버전 사용)
# ==================================================================

def page_documents():
    st.title("📄 서류 생성")
    from modules.documents import generate_all_documents, DocumentGenerator
    from modules.master_data import get_trade, load_master_data
    st.divider()
    
    df = load_master_data()
    tids = df['trade_id'].tolist() if not df.empty else []
    if not tids:
        st.warning("등록된 거래가 없습니다.")
        return
    
    tid = st.selectbox("거래 선택", tids)
    td = get_trade(tid) or {}
    
    if td:
        st.divider()
        st.write("#### 📑 선택된 거래 정보")
        
        # 거래 정보를 HTML 카드로 표시 (OpenAI 스마트 필드 매칭)
        trade_type = '수입' if smart_get(td, 'trade_type') == 'import' else '수출'
        item_name = smart_get(td, 'item_name', '')
        hs_code = smart_get(td, 'hs_code', '-')
        exporter = smart_get(td, 'exporter_name', '-')
        importer = smart_get(td, 'importer_name', '-')
        currency = smart_get(td, 'currency', '')
        total_value = smart_get(td, 'item_value', 0) or smart_get(td, 'unit_price', 0)
        tariff = smart_get(td, 'tariff_amount', 0)
        bl_number = smart_get(td, 'bl_number', '-')
        payment_terms = smart_get(td, 'payment_terms', '-')
        
        st.markdown(f"""
        <div style="
            background-color: rgba(255, 255, 255, 0.8);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            margin: 1rem 0;
        ">
            <div style="display: flex; justify-content: space-between;">
                <div style="flex: 1;">
                    <p style="margin: 0.5rem 0;"><strong>거래유형:</strong> {trade_type}</p>
                    <p style="margin: 0.5rem 0;"><strong>품목:</strong> {item_name}</p>
                    <p style="margin: 0.5rem 0;"><strong>HS Code:</strong> {hs_code}</p>
                </div>
                <div style="flex: 1;">
                    <p style="margin: 0.5rem 0;"><strong>수출자:</strong> {exporter}</p>
                    <p style="margin: 0.5rem 0;"><strong>수입자:</strong> {importer}</p>
                    <p style="margin: 0.5rem 0;"><strong>총액:</strong> {currency} {total_value:,.0f}</p>
                </div>
                <div style="flex: 1;">
                    <p style="margin: 0.5rem 0;"><strong>관세액:</strong> ₩{tariff:,.0f}</p>
                    <p style="margin: 0.5rem 0;"><strong>B/L No:</strong> {bl_number}</p>
                    <p style="margin: 0.5rem 0;"><strong>결제조건:</strong> {payment_terms}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📝 개별 서류 생성")
        dt = st.selectbox("서류 종류", [
            "Commercial Invoice (상업송장)",
            "Packing List (포장명세서)",
            "수입신고서"
        ])
        if st.button("서류 생성", type="primary", key="doc_gen_btn"):
            gen = DocumentGenerator()
            with st.spinner("생성 중..."):
                if "Commercial" in dt:
                    path = gen.generate_commercial_invoice(td)
                elif "Packing" in dt:
                    path = gen.generate_packing_list(td)
                elif "수입신고" in dt:
                    path = gen.generate_import_declaration(td)
                else:
                    path = None
            if path:
                st.success(f"생성 완료: {Path(path).name}")
                with open(path, "rb") as f:
                    st.download_button("📥 다운로드", f, file_name=Path(path).name, key=f"dl_single_{dt}")
            else:
                st.error("서류 생성 실패. 템플릿 파일을 확인하세요.")
                
    with c2:
        st.subheader("📦 전체 서류 일괄 생성")
        if st.button("모든 서류 생성", type="primary", key="doc_gen_all_btn"):
            tt = td.get('trade_type', 'import')
            with st.spinner("서류 생성 중..."):
                generated = generate_all_documents(td, tt)
            if generated:
                st.success(f"{len(generated)}개 서류 생성 완료")
                for doc in generated:
                    with open(doc['path'], "rb") as f:
                        st.download_button(f"📥 {doc['name']}", f, file_name=Path(doc['path']).name, key=f"dl_{doc['name']}_{tid}")
            else:
                st.error("서류 생성 실패. 템플릿 파일을 확인하세요.")

# ==================================================================
# PAGE: 거래 목록 (app_v11 최신 버전 사용)
# ==================================================================

def page_trades():
    st.title("📋 거래 목록 관리")
    from modules.master_data import load_master_data, update_trade, delete_trade
    st.divider()

    # ============================================================
    # 동기화 컨트롤 패널 (캐시 매니저 활성화 시에만 표시)
    # ============================================================
    if hasattr(st.session_state, 'cached_manager') and st.session_state.cached_manager:
        st.markdown("### 🔄 Excel 동기화")

        col1, col2, col3, col4 = st.columns([2, 2, 2, 4])

        with col1:
            if st.button("💾 Excel에 저장", use_container_width=True, help="변경사항을 Excel 파일에 저장합니다"):
                with st.spinner("동기화 중..."):
                    try:
                        st.session_state.cached_manager.sync_to_excel(force=False)
                        st.success("✅ 저장 완료")
                    except Exception as e:
                        st.error(f"❌ 저장 실패: {e}")

        with col2:
            if st.button("🔄 Excel에서 불러오기", use_container_width=True, help="Excel 파일의 변경사항을 불러옵니다"):
                with st.spinner("동기화 중..."):
                    try:
                        st.session_state.cached_manager.sync_from_excel()
                        st.success("✅ 불러오기 완료")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 불러오기 실패: {e}")

        with col3:
            stats = st.session_state.cached_manager.get_statistics()
            pending = stats.get('pending_changes', 0)
            st.metric("대기 중", f"{pending}건", help="Excel에 저장 대기 중인 변경사항 수")

        with col4:
            # 스케줄러 및 파일 감시 상태
            scheduler_status = "🟢" if (hasattr(st.session_state, 'sync_scheduler') and
                                       st.session_state.sync_scheduler and
                                       st.session_state.sync_scheduler.is_running()) else "🔴"
            watcher_status = "🟢" if (hasattr(st.session_state, 'file_watcher') and
                                     st.session_state.file_watcher and
                                     st.session_state.file_watcher.is_running()) else "🔴"

            st.info(f"💡 자동 저장: {scheduler_status} (5분마다) | Excel 감시: {watcher_status}")

        st.divider()

    # ============================================================
    # 거래 데이터 로드
    # ============================================================
    df = load_master_data()
    if df.empty:
        st.info("등록된 거래가 없습니다.")
        return
    
    # [수정] notes(메모) 컬럼 nan → 빈 문자열 처리
    if 'notes' in df.columns:
        df['notes'] = df['notes'].apply(
            lambda x: '' if pd.isna(x) or str(x).lower() == 'nan' or str(x).strip() == '' else str(x)
        )
    
    # 중요 표시 컬럼이 없으면 추가
    if 'is_important' not in df.columns:
        df['is_important'] = False
    else:
        # is_important 값 정규화 (NaN, None, 빈 값 → False)
        df['is_important'] = df['is_important'].apply(
            lambda x: True if str(x).lower() in ['true', '1', 'yes', 'y', '예'] else False
        )
    
    # ---------------------------------------------------------
    # 1. 필터 및 정렬
    # ---------------------------------------------------------
    st.subheader("🔍 필터 및 정렬")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        ttf = st.selectbox("거래유형", ["전체", "수입", "수출"])
    with col_f2:
        sf = st.selectbox("상태", ["전체"] + sorted(df['status'].dropna().unique().tolist()))
    with col_f3:
        imf = st.selectbox("중요 필터", ["전체", "중요 거래만", "일반 거래만"])
    with col_f4:
        sort_by = st.selectbox("정렬 기준", [
            "최신순 (등록일)", "오래된순 (등록일)", "거래번호 (오름차순)", "거래번호 (내림차순)",
            "금액 (높은순)", "금액 (낮은순)", "품목명 (가나다순)"
        ])
    
    # 필터링 (컬럼명 호환: trade_type 또는 direction)
    fdf = df.copy()
    
    # trade_type 컬럼 확인 및 정규화
    if 'direction' in fdf.columns and 'trade_type' not in fdf.columns:
        fdf['trade_type'] = fdf['direction'].apply(
            lambda x: 'import' if x == '수입' else ('export' if x == '수출' else x)
        )
    
    if ttf != "전체":
        if 'trade_type' in fdf.columns:
            fdf = fdf[fdf['trade_type'] == ("import" if ttf == "수입" else "export")]
        elif 'direction' in fdf.columns:
            fdf = fdf[fdf['direction'] == ttf]
    if sf != "전체":
        fdf = fdf[fdf['status'] == sf]
    if imf == "중요 거래만":
        fdf = fdf[fdf['is_important'] == True]
    elif imf == "일반 거래만":
        fdf = fdf[fdf['is_important'] == False]
    
    # 정렬 로직 (컬럼명 호환: created_date 또는 created_at)
    date_col = 'created_at' if 'created_at' in fdf.columns else ('created_date' if 'created_date' in fdf.columns else 'trade_date')
    
    if sort_by == "최신순 (등록일)": 
        if date_col in fdf.columns:
            fdf = fdf.sort_values(date_col, ascending=False)
    elif sort_by == "오래된순 (등록일)": 
        if date_col in fdf.columns:
            fdf = fdf.sort_values(date_col, ascending=True)
    elif sort_by == "거래번호 (오름차순)": fdf = fdf.sort_values('trade_id', ascending=True)
    elif sort_by == "거래번호 (내림차순)": fdf = fdf.sort_values('trade_id', ascending=False)
    elif "금액" in sort_by:
        fdf['sort_amount'] = fdf.apply(lambda x: x.get('item_value', x.get('line_amount', x.get('unit_price', 0))), axis=1)
        fdf = fdf.sort_values('sort_amount', ascending=("낮은순" in sort_by))
    elif sort_by == "품목명 (가나다순)":
        # 품목명 정렬 시에도 순수 품목명 우선 사용
        fdf['sort_name'] = fdf.apply(lambda x: str(x.get('item_name_pure', x.get('item_name', ''))), axis=1)
        fdf = fdf.sort_values('sort_name', ascending=True)
    
    # ---------------------------------------------------------
    # 2. 거래 목록 표시 (핵심 수정)
    # ---------------------------------------------------------
    st.subheader(f"📊 거래 목록 ({len(fdf)}건)")
    
    for idx, row in fdf.iterrows():
        trade_type_emoji = "📥" if row['trade_type'] == 'import' else "📤"
        star_emoji = "⭐" if row.get('is_important') else "☆"
        
        # [핵심 수정] 리스트 제목에 '순수 품목명(item_name_pure)' 우선 표시
        display_name = row.get('item_name_pure')
        if not display_name or str(display_name) == 'nan' or str(display_name).strip() == '':
            display_name = row.get('item_name', '품목명 없음')
            
        # 너무 길면 자르기
        if len(str(display_name)) > 30:
            display_name = str(display_name)[:30] + "..."

        # [수정] 금액 포맷팅 - NaN 방지, line_amount 우선
        amt = row.get('line_amount', row.get('item_value', 0))
        if not amt or amt == 0 or str(amt) == 'nan':
            unit_p = row.get('unit_price', 0)
            qty = row.get('quantity', 0)
            try:
                unit_p = float(unit_p) if unit_p and str(unit_p) != 'nan' else 0
                qty = float(qty) if qty and str(qty) != 'nan' else 0
            except:
                unit_p = 0
                qty = 0
            amt = unit_p * qty if (unit_p and qty) else 0
        
        # NaN 방지
        try:
            amt = float(amt) if amt and str(amt) != 'nan' else 0
        except:
            amt = 0
        
        curr = row.get('currency', 'USD')
        
        title_parts = [
            f"{star_emoji} {trade_type_emoji}",
            f"`{row['trade_id']}`",
            f"**{display_name}**",
            f"{curr} {amt:,.0f}"
        ]
        
        expander_title = " │ ".join(title_parts)
        
        with st.expander(expander_title, expanded=False):
        # ... (나머지 코드 동일)
            # 탭으로 정보 구분
            tab1, tab2, tab3, tab4 = st.tabs(["📋 품목/물류", "🏢 거래처", "💰 금액/세액", "📝 관리"])
            
            # None/NaN → 공백 처리 헬퍼 함수
            def safe_val(val, default=''):
                if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).lower() in ['nan', 'none', '']:
                    return default
                return str(val)
            
            with tab1:
                # 편집 모드 토글
                edit_key = f"edit_logistics_{row['trade_id']}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False
                
                btn_col, _ = st.columns([1, 4])
                with btn_col:
                    if st.button("✏️ 편집" if not st.session_state[edit_key] else "❌ 취소", 
                                key=f"toggle_{row['trade_id']}", use_container_width=True):
                        st.session_state[edit_key] = not st.session_state[edit_key]
                        st.rerun()
                
                if st.session_state[edit_key]:
                    # === 편집 모드 ===
                    with st.form(f"edit_form_{row['trade_id']}"):
                        st.markdown("##### 📝 품목 정보")
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            new_item = st.text_input("순수 품목명", value=safe_val(row.get('item_name_pure', row.get('item_name'))))
                            new_hs = st.text_input("HS Code", value=safe_val(row.get('hscode', row.get('hs_code'))))
                            new_origin = st.text_input("원산지/목적국", value=safe_val(row.get('origin_country', row.get('import_country'))))
                        with ec2:
                            new_pkg = st.text_input("포장 방법", value=safe_val(row.get('package_summary')))
                            new_cont = st.text_input("컨테이너", value=safe_val(row.get('container_info')))
                            new_qty = st.text_input("수량", value=safe_val(row.get('quantity')))
                        
                        st.markdown("##### 🚢 물류 정보")
                        lc1, lc2, lc3 = st.columns(3)
                        with lc1:
                            new_pol = st.text_input("POL", value=safe_val(row.get('loading_port')))
                        with lc2:
                            new_pod = st.text_input("POD", value=safe_val(row.get('discharge_port')))
                        with lc3:
                            new_vessel = st.text_input("선박", value=safe_val(row.get('vessel', row.get('vessel_name'))))
                        
                        new_bl = st.text_input("B/L No", value=safe_val(row.get('bl_no', row.get('bl_number'))))
                        wc1, wc2 = st.columns(2)
                        with wc1:
                            new_gw = st.text_input("총중량", value=safe_val(row.get('gross_weight')))
                        with wc2:
                            new_nw = st.text_input("순중량", value=safe_val(row.get('net_weight')))

                        new_payment = st.text_input("결제조건", value=safe_val(row.get('payment_terms')), placeholder="예: T/T, L/C, D/P")

                        if st.form_submit_button("💾 저장", type="primary", use_container_width=True):
                            update_trade(row['trade_id'], {
                                'item_name_pure': new_item, 'hs_code': new_hs, 'origin_country': new_origin,
                                'package_summary': new_pkg, 'container_info': new_cont, 'quantity': new_qty,
                                'loading_port': new_pol, 'discharge_port': new_pod, 'vessel': new_vessel,
                                'bl_number': new_bl, 'gross_weight': new_gw, 'net_weight': new_nw,
                                'payment_terms': new_payment
                            })
                            st.session_state[edit_key] = False
                            st.success("✅ 저장 완료")
                            st.rerun()
                else:
                    # === 조회 모드 (None → 공백 처리) ===
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption("품목 상세")
                        st.write(f"**순수 품목명:** {safe_val(row.get('item_name_pure', row.get('item_name')), '-')}")
                        st.write(f"**HS Code:** {safe_val(row.get('hscode', row.get('hs_code')), '-')}")
                        st.write(f"**원산지/목적국:** {safe_val(row.get('origin_country', row.get('import_country')), '-')}")
                    with c2:
                        st.caption("포장 및 컨테이너")
                        st.write(f"**포장 방법:** {safe_val(row.get('package_summary'), '-')}")
                        st.write(f"**컨테이너:** {safe_val(row.get('container_info'), '-')}")
                        st.write(f"**수량:** {safe_val(row.get('quantity'), '0')} {safe_val(row.get('uom', row.get('unit')), 'EA')}")

                    st.markdown("---")
                    st.caption("물류 정보")
                    l1, l2, l3 = st.columns(3)
                    l1.write(f"**POL:** {safe_val(row.get('loading_port'), '-')}")
                    l2.write(f"**POD:** {safe_val(row.get('discharge_port'), '-')}")
                    l3.write(f"**선박:** {safe_val(row.get('vessel', row.get('vessel_name')), '-')}")
                    
                    st.write(f"**B/L No:** {safe_val(row.get('bl_no', row.get('bl_number')), '-')}")
                    st.write(f"**총중량:** {safe_val(row.get('gross_weight'), '-')} / **순중량:** {safe_val(row.get('net_weight'), '-')}")
            
            with tab2:
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**수출자:** {row.get('exporter_name', '-')}")
                    st.caption(row.get('exporter_address', ''))
                with c2:
                    st.write(f"**수입자:** {row.get('importer_name', '-')}")
                    st.caption(row.get('importer_address', ''))
            
            with tab3:
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**총 금액:** {curr} {amt:,.2f}")
                    st.write(f"**인도조건:** {row.get('incoterms', '-')}")
                    st.write(f"**결제조건:** {row.get('payment_terms', '-')}")
                with c2:
                    if row['trade_type'] == 'import':
                        st.write(f"**관세율:** {row.get('tariff_rate', 0)}%")
                        st.write(f"**관세액:** ₩{row.get('tariff_amount', 0):,.0f}")
                        st.write(f"**부가세:** ₩{row.get('vat_amount', 0):,.0f}")
            
            with tab4:
                # 액션 버튼
                c_a1, c_a2, c_a3 = st.columns(3)
                with c_a1:
                    btn_label = "중요 해제" if row.get('is_important') else "중요 표시"
                    if st.button(btn_label, key=f"imp_{row['trade_id']}", use_container_width=True):
                        update_trade(row['trade_id'], {'is_important': not row.get('is_important')})
                        st.rerun()
                with c_a2:
                    if st.button("메모 수정", key=f"memo_{row['trade_id']}", use_container_width=True):
                        st.session_state[f'edit_memo_{row["trade_id"]}'] = not st.session_state.get(f'edit_memo_{row["trade_id"]}', False)
                with c_a3:
                    if st.button("삭제", key=f"del_{row['trade_id']}", type="primary", use_container_width=True):
                        delete_trade(row['trade_id'])
                        st.rerun()
                
                # 메모 편집기
                if st.session_state.get(f'edit_memo_{row["trade_id"]}'):
                    # NaN 값을 빈 문자열로 변환
                    current_note = row.get('notes', '')
                    if current_note is None or str(current_note).lower() == 'nan' or str(current_note).strip() == '':
                        current_note = ''
                    
                    new_note = st.text_area(
                        "메모", 
                        value=current_note, 
                        key=f"txt_{row['trade_id']}",
                        placeholder="메모를 입력하세요"
                    )
                    if st.button("저장", key=f"save_{row['trade_id']}"):
                        update_trade(row['trade_id'], {'notes': new_note})
                        st.session_state[f'edit_memo_{row["trade_id"]}'] = False
                        st.rerun()

# ==================================================================
# PAGE: 설정 (app_v7_inti.py의 벡터 인덱스 관리 기능 유지)
# ==================================================================

def page_settings():
    st.title("⚙️ 설정")
    st.divider()
    
    st.subheader("API 상태")
    for k, v in settings.validate_api_keys().items():
        col1, col2 = st.columns([3, 1])
        col1.write(v['desc'])
        col2.write("✅ 설정됨" if v['set'] else "❌ 미설정")


if __name__ == "__main__":
    init_session()
    init_default_admin()
    
    if st.session_state.logged_in:
        main_app()
    else:
        login_page()

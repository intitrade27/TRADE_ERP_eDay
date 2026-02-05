# -*- coding: utf-8 -*-
"""
마스터 데이터 관리 모듈
- 통합 Excel 파일로 모든 거래 데이터 관리
- 수입/수출 데이터 저장 및 조회
- 마진율 자동 적용
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import MASTER_DATA_DIR
from config.constants import MASTER_DATA_COLUMNS, DEFAULT_MARGIN_RATES, DEFAULT_MARGIN_RATE

logger = logging.getLogger(__name__)
MASTER_FILE = MASTER_DATA_DIR / "trade_master.xlsx"


class MasterDataError(Exception):
    pass


def init_master_file() -> pd.DataFrame:
    """마스터 파일 초기화"""
    MASTER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(columns=MASTER_DATA_COLUMNS)
    df.to_excel(MASTER_FILE, index=False, engine='openpyxl')
    logger.info("[MASTER] 마스터 파일 초기화")
    return df


def load_master_data() -> pd.DataFrame:
    """
    마스터 데이터 로드 - ★ 모든 컬럼의 NaN 방지 및 기본값 설정
    """
    import pandas as pd
    from pathlib import Path
    
    # CSV 파일 경로
    csv_path = MASTER_DATA_DIR / "master_data.csv"
    
    # 파일이 없으면 빈 DataFrame 생성 (모든 컬럼 정의)
    if not csv_path.exists():
        columns = [
            'trade_id', 'trade_type', 'created_date', 'status',
            'is_important', 'notes',
            'item_name', 'item_name_pure', 'hs_code', 
            'quantity', 'unit', 'currency',
            'container_info', 'package_summary',
            'exporter_name', 'exporter_address',
            'importer_name', 'importer_address',
            'notify_party', 'notify_address',
            'incoterms', 'payment_terms', 'bl_number', 'vessel_name',
            'loading_port', 'discharge_port',
            'marks_numbers', 'gross_weight', 'net_weight',
            'invoice_no', 'invoice_date', 'ref_date', 'free_time',
            'item_value', 'unit_price', 'tariff_rate', 
            'tariff_amount', 'vat_amount',
            'origin_country', 'import_country',
            'base_margin_rate', 'applied_margin_rate'
        ]
        df = pd.DataFrame(columns=columns)
        # 안전하게 저장 후 리턴
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        return df
    
    # 파일 로드
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    
    # ★★★ [핵심] 모든 컬럼에 대한 기본값 정의 (NaN 방지) ★★★
    defaults = {
        # 1. 상태 및 관리
        'is_important': False,
        'notes': '',
        'status': 'pending',
        'created_date': '',

        # 2. 품목 및 규격
        'item_name': '', 
        'item_name_pure': '',       # 순수 품목명 (리스트 표시용)
        'hs_code': '', 
        'quantity': 0, 
        'unit': 'EA', 
        'currency': 'USD',
        'container_info': '',       # 컨테이너 정보 (예: 1x40' HC)
        'package_summary': '',      # 포장 정보 (예: 1440 BAGS)

        # 3. 거래 당사자 (주소 포함)
        'exporter_name': '', 
        'exporter_address': '',
        'importer_name': '', 
        'importer_address': '',
        'notify_party': '', 
        'notify_address': '',

        # 4. 물류 및 운송
        'incoterms': '', 
        'payment_terms': '', 
        'bl_number': '', 
        'vessel_name': '',
        'loading_port': '', 
        'discharge_port': '',
        'marks_numbers': '', 
        'gross_weight': '', 
        'net_weight': '',

        # 5. 서류 및 일정
        'invoice_no': '', 
        'invoice_date': '', 
        'ref_date': '', 
        'free_time': 7,

        # 6. 금액 및 세액 (숫자형은 0 또는 0.0)
        'item_value': 0.0, 
        'unit_price': 0.0, 
        'tariff_rate': 0.0, 
        'tariff_amount': 0.0, 
        'vat_amount': 0.0,
        
        # 7. 국가 정보
        'origin_country': '', 
        'import_country': '',

        # 8. 마진율
        'base_margin_rate': 0.0, 
        'applied_margin_rate': 0.0
    }
    
    # 딕셔너리를 순회하며 NaN 값 채우기 및 컬럼 생성
    for col, default_val in defaults.items():
        if col not in df.columns:
            # 컬럼 자체가 없으면 기본값으로 생성
            df[col] = default_val
        else:
            # 컬럼은 있는데 값이 비어있으면(NaN) 기본값으로 채움
            df[col] = df[col].fillna(default_val)
            
            # (옵션) 빈 문자열('')조차 NaN으로 인식될 경우를 대비해 확실하게 처리
            if isinstance(default_val, str):
                df[col] = df[col].astype(str).replace('nan', '')

    return df


def save_master_data(df: pd.DataFrame):
    """
    마스터 데이터 저장
    """
    csv_path = MASTER_DATA_DIR / "master_data.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')

def _generate_id(trade_type: str) -> str:
    """거래 ID 생성"""
    prefix = "IMP" if trade_type == "import" else "EXP"
    date_str = datetime.now().strftime('%Y%m%d')
    df = load_master_data()
    today = df[df['trade_id'].str.contains(f"{prefix}-{date_str}", na=False)]
    return f"{prefix}-{date_str}-{len(today)+1:03d}"


def get_margin_rate(hs_code: str = None) -> Dict[str, Any]:
    """
    HS Code 기반 마진율 조회
    품목군별 기본 마진율 적용
    """
    if not hs_code:
        return {
            'rate': DEFAULT_MARGIN_RATE,
            'name': '기본',
            'source': '기본 마진율'
        }
    
    hs_code = str(hs_code).replace('.', '').replace('-', '').zfill(10)
    hs_2digit = hs_code[:2]
    
    margin_info = DEFAULT_MARGIN_RATES.get(hs_2digit)
    if margin_info:
        return {
            'rate': margin_info['rate'],
            'name': margin_info['name'],
            'source': margin_info['source']
        }
    
    return {
        'rate': DEFAULT_MARGIN_RATE,
        'name': '기본',
        'source': '기본 마진율'
    }


def calculate_prices_with_margin(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    마진율 적용하여 가격 계산
    마진율 변경 시 연관 데이터 자동 업데이트
    """
    cif_krw = float(data.get('cif_value_krw', 0) or 0)
    tariff_amount = float(data.get('tariff_amount', 0) or 0)
    vat_amount = float(data.get('vat_amount', 0) or 0)
    
    # 원가 계산
    cost_price = cif_krw + tariff_amount + vat_amount
    
    # 마진율 결정
    hs_code = data.get('hs_code')
    margin_info = get_margin_rate(hs_code)
    
    # 적용 마진율 (사용자 지정 또는 기본)
    applied_margin = float(data.get('applied_margin_rate', 0) or 0)
    if applied_margin == 0:
        applied_margin = margin_info['rate']
    
    # 판매가 계산
    margin_amount = cost_price * (applied_margin / 100)
    selling_price_krw = cost_price + margin_amount
    
    # 외화 판매가 (환율 적용)
    exchange_rate = float(data.get('exchange_rate', 1) or 1)
    selling_price_foreign = selling_price_krw / exchange_rate if exchange_rate > 0 else 0
    
    return {
        'base_margin_rate': margin_info['rate'],
        'applied_margin_rate': applied_margin,
        'cost_price': round(cost_price),
        'margin_amount': round(margin_amount),
        'selling_price_krw': round(selling_price_krw),
        'selling_price_foreign': round(selling_price_foreign, 2),
    }


def create_trade(trade_type: str, data: Dict) -> str:
    """
    거래 생성 - ★ 모든 필드 저장
    """
    import pandas as pd
    from datetime import datetime
    
    # 거래 ID 생성
    today = datetime.now()
    prefix = "IMP" if trade_type == "import" else "EXP"
    
    # 시퀀스 번호 생성 (간단한 카운터)
    df = load_master_data()
    existing_ids = df[df['trade_id'].str.startswith(f"{prefix}-{today.strftime('%Y%m%d')}") if not df.empty else []]['trade_id'].tolist()
    seq = len(existing_ids) + 1
    trade_id = f"{prefix}-{today.strftime('%Y%m%d')}-{seq:03d}"
    
    # ★★★ 모든 필드를 포함한 거래 데이터 ★★★
    trade_data = {
        'trade_id': trade_id,
        'trade_type': trade_type,
        'created_date': today.strftime('%Y-%m-%d %H:%M:%S'),
        'status': data.get('status', 'pending'),
        'is_important': data.get('is_important', False),
        'notes': data.get('notes', ''),
        
        # 기본 정보
        'item_name': data.get('item_name', ''),
        'hs_code': data.get('hs_code', ''),
        'quantity': data.get('quantity', 0),
        'unit': data.get('unit', 'EA'),
        'currency': data.get('currency', 'USD'),
        
        # ★★★ 당사자 정보 (주소 포함) ★★★
        'exporter_name': data.get('exporter_name', ''),
        'exporter_address': data.get('exporter_address', ''),
        'importer_name': data.get('importer_name', ''),
        'importer_address': data.get('importer_address', ''),
        'notify_party': data.get('notify_party', ''),
        'notify_address': data.get('notify_address', ''),
        
        # ★★★ 물류 정보 ★★★
        'incoterms': data.get('incoterms', ''),
        'payment_terms': data.get('payment_terms', ''),
        'bl_number': data.get('bl_number', ''),
        'vessel_name': data.get('vessel_name', ''),
        'loading_port': data.get('loading_port', ''),
        'discharge_port': data.get('discharge_port', ''),
        'marks_numbers': data.get('marks_numbers', ''),
        'gross_weight': data.get('gross_weight', ''),
        'net_weight': data.get('net_weight', ''),

        # [추가] 분리된 상세 정보 저장
        'item_name_pure': data.get('item_name_pure', ''),
        'container_info': data.get('container_info', ''),
        'package_summary': data.get('package_summary', ''),
        
        # 서류 정보
        'invoice_no': data.get('invoice_no', ''),
        'invoice_date': str(data.get('invoice_date', '')),
        'ref_date': str(data.get('ref_date', '')),
        'free_time': data.get('free_time', 7),
        
        # 관세 정보
        'base_margin_rate': data.get('base_margin_rate', 20),
        'applied_margin_rate': data.get('applied_margin_rate', ''),
    }
    
    # 수입/수출 구분 필드
    if trade_type == 'import':
        trade_data.update({
            'item_value': data.get('item_value', 0),
            'origin_country': data.get('origin_country', ''),
            'tariff_rate': data.get('tariff_rate', 0),
            'tariff_amount': data.get('tariff_amount', 0),
            'vat_amount': data.get('vat_amount', 0),
        })
    else:  # export
        trade_data.update({
            'unit_price': data.get('unit_price', 0),
            'import_country': data.get('import_country', ''),
        })
    
    # DataFrame에 추가
    new_row = pd.DataFrame([trade_data])
    df = pd.concat([df, new_row], ignore_index=True)
    
    # 저장
    save_master_data(df)
    
    return trade_id


def get_trade(trade_id: str) -> Optional[Dict]:
    """거래 조회"""
    df = load_master_data()
    t = df[df['trade_id'] == trade_id]
    if t.empty:
        return None
    return t.iloc[0].to_dict()


def update_trade(trade_id: str, updates: Dict) -> bool:
    """
    거래 정보 업데이트 - ★ 모든 필드 업데이트 가능
    """
    try:
        df = load_master_data()
        
        if df.empty:
            return False
        
        # 해당 거래 찾기
        idx = df[df['trade_id'] == trade_id].index
        
        if len(idx) == 0:
            return False
        
        # ★★★ 모든 필드를 업데이트 ★★★
        for key, value in updates.items():
            if key in df.columns:
                df.loc[idx[0], key] = value
        
        # 저장
        save_master_data(df)
        return True
        
    except Exception as e:
        print(f"Update error: {e}")
        return False

def delete_trade(trade_id: str) -> bool:
    """
    거래 삭제
    """
    try:
        df = load_master_data()
        
        if df.empty:
            return False
        
        # 해당 거래 제외하고 저장
        df = df[df['trade_id'] != trade_id]
        save_master_data(df)
        
        return True
        
    except Exception as e:
        print(f"Delete error: {e}")
        return False

def search_trades(**kwargs) -> pd.DataFrame:
    """거래 검색"""
    df = load_master_data()
    if kwargs.get('trade_type'):
        df = df[df['trade_type'] == kwargs['trade_type']]
    if kwargs.get('status'):
        df = df[df['status'] == kwargs['status']]
    if kwargs.get('hs_code'):
        df = df[df['hs_code'].str.contains(kwargs['hs_code'], na=False)]
    return df


def get_statistics() -> Dict:
    """통계 조회"""
    df = load_master_data()
    return {
        'total': len(df),
        'import_count': len(df[df['trade_type'] == 'import']),
        'export_count': len(df[df['trade_type'] == 'export']),
        'total_cif': df['cif_value_krw'].sum() if 'cif_value_krw' in df else 0,
        'total_selling': df['selling_price_krw'].sum() if 'selling_price_krw' in df else 0,
    }


def update_clearance_status(trade_id: str, stage: str, stage_date: str = None) -> bool:
    """통관 단계 업데이트"""
    from config.constants import CLEARANCE_STAGES
    
    stage_info = CLEARANCE_STAGES.get(stage)
    if not stage_info:
        return False
    
    if not stage_date:
        stage_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    data = {'status': stage_info['name']}
    
    date_columns = {
        'arrival': 'arrival_date',
        'unloading': 'unloading_date',
        'warehousing': 'warehousing_date',
        'declaration': 'declaration_date',
        'clearance': 'clearance_date',
        'release': 'release_date',
    }
    
    if stage in date_columns:
        data[date_columns[stage]] = stage_date
    
    return update_trade(trade_id, data)


def export_to_excel(trade_ids: List[str] = None, filepath: str = None) -> str:
    """거래 데이터 Excel 내보내기"""
    df = load_master_data()
    
    if trade_ids:
        df = df[df['trade_id'].isin(trade_ids)]
    
    if not filepath:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = MASTER_DATA_DIR / f"export_{timestamp}.xlsx"
    
    df.to_excel(filepath, index=False, engine='openpyxl')
    return str(filepath)
# -*- coding: utf-8 -*-
"""
마스터 데이터 관리 모듈
- 레거시 excel_manager (폴백용)
- 신규 template_manager (trade_erp_master_template.xlsx 연동)
"""

# 기존 excel_manager 함수들 (폴백용)
from .excel_manager import (
    load_master_data as _load_master_data_legacy,
    save_master_data as _save_master_data_legacy,
    create_trade as _create_trade_legacy,
    get_trade as _get_trade_legacy,
    update_trade as _update_trade_legacy,
    delete_trade as _delete_trade_legacy,
    search_trades as _search_trades_legacy,
    get_statistics as _get_statistics_legacy,
    update_clearance_status as _update_clearance_status_legacy,
    get_margin_rate,
    calculate_prices_with_margin,
    export_to_excel as _export_to_excel_legacy
)

# 신규 template_manager
from .template_manager import (
    TemplateExcelManager,
    get_template_manager,
    reset_template_manager
)

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 템플릿 매니저 싱글톤
_template_mgr: Optional[TemplateExcelManager] = None


def _get_template_mgr() -> Optional[TemplateExcelManager]:
    """템플릿 매니저 가져오기"""
    global _template_mgr
    
    if _template_mgr is not None:
        return _template_mgr
    
    try:
        # trade_erp_master_template.xlsx 경로
        base_dir = Path(__file__).parent.parent.parent
        template_path = base_dir / "trade_erp_master_template.xlsx"
        
        if template_path.exists():
            _template_mgr = TemplateExcelManager(str(template_path))
            logger.info(f"[MASTER] 템플릿 매니저 초기화: {template_path}")
            return _template_mgr
    except Exception as e:
        logger.error(f"[MASTER] 템플릿 매니저 초기화 실패: {e}")
    
    return None


def _use_template_manager() -> bool:
    """템플릿 매니저 사용 가능 여부"""
    return _get_template_mgr() is not None


def _use_cached_manager() -> bool:
    """캐시 매니저 사용 가능 여부 확인"""
    return (hasattr(st, 'session_state') and
            hasattr(st.session_state, 'cached_manager') and
            st.session_state.cached_manager is not None)


def load_master_data() -> pd.DataFrame:
    """
    마스터 데이터 로드
    우선순위: 템플릿 매니저 > 캐시 매니저 > 레거시
    """
    # 1. 템플릿 매니저 (trade_erp_master_template.xlsx)
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            df = mgr.read_all_trades()
            
            # 컬럼명 호환성 처리 (direction → trade_type)
            if 'direction' in df.columns and 'trade_type' not in df.columns:
                df['trade_type'] = df['direction'].apply(
                    lambda x: 'import' if x == '수입' else ('export' if x == '수출' else x)
                )
            
            return df
        except Exception as e:
            logger.error(f"[MASTER] 템플릿 매니저 로드 실패: {e}")
    
    # 2. 캐시 매니저
    if _use_cached_manager():
        return st.session_state.cached_manager.read_all_rows()
    
    # 3. 레거시
    return _load_master_data_legacy()


def create_trade(trade_type: str, data: Dict[str, Any], save_to_master: bool = True) -> str:
    """
    거래 생성
    우선순위: 템플릿 매니저 > 캐시 매니저 > 레거시
    """
    # 1. 템플릿 매니저
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            return mgr.create_trade(trade_type, data)
        except Exception as e:
            logger.error(f"[MASTER] 템플릿 매니저 생성 실패: {e}")
    
    # 2. 캐시 매니저
    if _use_cached_manager():
        data['trade_type'] = trade_type
        return st.session_state.cached_manager.create_row(data)
    
    # 3. 레거시
    return _create_trade_legacy(trade_type, data, save_to_master)


def get_trade(trade_id: str) -> Optional[Dict]:
    """거래 조회"""
    # 1. 템플릿 매니저
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            return mgr.get_trade(trade_id)
        except Exception as e:
            logger.error(f"[MASTER] 템플릿 매니저 조회 실패: {e}")
    
    # 2. 캐시 매니저
    if _use_cached_manager():
        return st.session_state.cached_manager.read_row(trade_id)
    
    # 3. 레거시
    return _get_trade_legacy(trade_id)


def update_trade(trade_id: str, data: Dict) -> bool:
    """거래 업데이트"""
    # 1. 템플릿 매니저
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            return mgr.update_trade(trade_id, data)
        except Exception as e:
            logger.error(f"[MASTER] 템플릿 매니저 업데이트 실패: {e}")
    
    # 2. 캐시 매니저
    if _use_cached_manager():
        return st.session_state.cached_manager.update_row(trade_id, data)
    
    # 3. 레거시
    return _update_trade_legacy(trade_id, data)


def delete_trade(trade_id: str) -> bool:
    """거래 삭제"""
    # 1. 템플릿 매니저
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            return mgr.delete_trade(trade_id)
        except Exception as e:
            logger.error(f"[MASTER] 템플릿 매니저 삭제 실패: {e}")
    
    # 2. 캐시 매니저
    if _use_cached_manager():
        return st.session_state.cached_manager.delete_row(trade_id)
    
    # 3. 레거시
    return _delete_trade_legacy(trade_id)


def search_trades(**kwargs) -> pd.DataFrame:
    """거래 검색"""
    # 템플릿 매니저 사용 시 필터 적용
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            df = mgr.read_all_trades()
            
            # 필터 적용
            if kwargs.get('trade_type'):
                search_value = "수입" if kwargs['trade_type'] == 'import' else "수출"
                if 'direction' in df.columns:
                    df = df[df['direction'] == search_value]
            
            if kwargs.get('status') and 'status' in df.columns:
                df = df[df['status'] == kwargs['status']]
            
            if kwargs.get('hs_code') and 'hscode' in df.columns:
                df = df[df['hscode'].str.contains(kwargs['hs_code'], na=False)]
            
            return df
        except Exception as e:
            logger.error(f"[MASTER] 템플릿 매니저 검색 실패: {e}")
    
    # 캐시 매니저
    if _use_cached_manager():
        df = st.session_state.cached_manager.read_all_rows()
        
        if kwargs.get('trade_type'):
            trade_type_col = st.session_state.cached_manager._find_column('수입/수출', 'direction')
            if trade_type_col and trade_type_col in df.columns:
                search_value = "수입" if kwargs['trade_type'] == 'import' else "수출"
                df = df[df[trade_type_col] == search_value]
        
        if kwargs.get('status'):
            status_col = st.session_state.cached_manager._find_column('상태', 'status')
            if status_col and status_col in df.columns:
                df = df[df[status_col] == kwargs['status']]
        
        if kwargs.get('hs_code'):
            hs_col = st.session_state.cached_manager._find_column('HS', 'hscode')
            if hs_col and hs_col in df.columns:
                df = df[df[hs_col].str.contains(kwargs['hs_code'], na=False)]
        
        return df
    
    return _search_trades_legacy(**kwargs)


def get_statistics() -> Dict:
    """통계 조회"""
    # 템플릿 매니저
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            return mgr.get_statistics()
        except Exception as e:
            logger.error(f"[MASTER] 템플릿 매니저 통계 실패: {e}")
    
    # 캐시 매니저
    if _use_cached_manager():
        return st.session_state.cached_manager.get_statistics()
    
    return _get_statistics_legacy()


def get_monthly_summary(**kwargs) -> pd.DataFrame:
    """
    월별 집계 (PAGE2_VIEW 스타일)
    - 대시보드 월별 상세 실적에서 사용
    """
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            return mgr.get_monthly_summary(**kwargs)
        except Exception as e:
            logger.error(f"[MASTER] 월별 집계 실패: {e}")
    
    # 폴백: 직접 계산
    df = load_master_data()
    if df.empty:
        return pd.DataFrame(columns=['month', 'import', 'export', 'net_sales'])
    
    return _calculate_monthly_summary(df)


def _calculate_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """월별 집계 직접 계산 (폴백)"""
    # 날짜 컬럼 찾기
    date_col = None
    for col in ['trade_date', 'date', 'created_at', 'created_date']:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        return pd.DataFrame(columns=['month', 'import', 'export', 'net_sales'])
    
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    
    if df.empty:
        return pd.DataFrame(columns=['month', 'import', 'export', 'net_sales'])
    
    # 금액 컬럼 찾기
    amount_col = None
    for col in ['line_amount', 'item_value', 'amount', 'trade_amount']:
        if col in df.columns:
            amount_col = col
            break
    
    if amount_col is None:
        return pd.DataFrame(columns=['month', 'import', 'export', 'net_sales'])
    
    df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)
    
    # trade_type 컬럼 확인
    type_col = None
    for col in ['trade_type', 'direction']:
        if col in df.columns:
            type_col = col
            break
    
    if type_col is None:
        return pd.DataFrame(columns=['month', 'import', 'export', 'net_sales'])
    
    # 수입/수출 분리
    import_mask = df[type_col].isin(['import', '수입'])
    export_mask = df[type_col].isin(['export', '수출'])
    
    import_df = df[import_mask].groupby(df[date_col].dt.to_period('M'))[amount_col].sum()
    export_df = df[export_mask].groupby(df[date_col].dt.to_period('M'))[amount_col].sum()
    
    all_months = set(import_df.index) | set(export_df.index)
    
    result = []
    for month_period in sorted(all_months):
        imp_val = import_df.get(month_period, 0)
        exp_val = export_df.get(month_period, 0)
        result.append({
            'month': month_period.to_timestamp(),
            'import': imp_val,
            'export': exp_val,
            'net_sales': exp_val - imp_val
        })
    
    return pd.DataFrame(result)


def get_filter_options() -> Dict[str, List[str]]:
    """필터 옵션 목록 (드롭다운용)"""
    if _use_template_manager():
        try:
            mgr = _get_template_mgr()
            return mgr.get_filter_options()
        except Exception as e:
            logger.error(f"[MASTER] 필터 옵션 로드 실패: {e}")
    
    # 폴백
    return {
        'item_names': [],
        'import_countries': [],
        'export_countries': [],
        'origin_countries': [],
        'years': [],
        'months': list(range(1, 13))
    }


def get_template_file_path() -> Optional[str]:
    """템플릿 파일 경로 (다운로드용)"""
    if _use_template_manager():
        mgr = _get_template_mgr()
        return mgr.get_template_for_download()
    return None


def update_clearance_status(trade_id: str, stage: str, stage_date: str = None) -> bool:
    """통관 단계 업데이트 (레거시 사용)"""
    return _update_clearance_status_legacy(trade_id, stage, stage_date)


def save_master_data(df: pd.DataFrame):
    """마스터 데이터 저장 (레거시만 - 템플릿 매니저는 자동 동기화)"""
    if not _use_template_manager() and not _use_cached_manager():
        _save_master_data_legacy(df)
    else:
        logger.warning("[MASTER] save_master_data 호출 - 매니저 사용 시 자동 동기화됨")


def export_to_excel(trade_ids: List[str] = None, filepath: str = None) -> str:
    """Excel 내보내기 (레거시 사용)"""
    return _export_to_excel_legacy(trade_ids, filepath)


__all__ = [
    'load_master_data', 'save_master_data', 'create_trade', 'get_trade',
    'update_trade', 'delete_trade', 'search_trades', 'get_statistics',
    'update_clearance_status', 'get_margin_rate', 'calculate_prices_with_margin',
    'export_to_excel',
    # 신규 함수들
    'get_monthly_summary', 'get_filter_options', 'get_template_file_path',
    'TemplateExcelManager', 'get_template_manager', 'reset_template_manager'
]

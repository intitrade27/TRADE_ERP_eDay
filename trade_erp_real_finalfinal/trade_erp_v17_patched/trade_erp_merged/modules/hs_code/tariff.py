# -*- coding: utf-8 -*-
"""
관세율 분석 모듈
- 기본세율 vs FTA세율 vs 특별세율 비교
- 최저세율 도출
- 관세 종류별 시각화 데이터
"""

import logging
from typing import List, Dict, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.constants import FTA_AGREEMENTS, COUNTRY_TO_FTA, VAT_RATE, FTA_CODE_TO_NAME, ADDITIVE_TARIFFS
from .search import get_all_tariff_rates, get_tariff_by_category, get_hs_info

logger = logging.getLogger(__name__)


def get_applicable_fta(country_code: str) -> List[Dict[str, Any]]:
    """국가 적용 가능 FTA 목록"""
    country_code = country_code.upper()
    fta_codes = COUNTRY_TO_FTA.get(country_code, [])
    return [{
        'fta_code': code,
        'fta_name': FTA_AGREEMENTS[code]['name'],
        'effective_date': FTA_AGREEMENTS[code]['effective_date'],
    } for code in fta_codes if code in FTA_AGREEMENTS]


def analyze_tariff_rates(hs_code: str, country_code: str = None) -> Dict[str, Any]:
    """
    관세율 종합 분석
    """
    categorized = get_tariff_by_category(hs_code)
    hs_info = get_hs_info(hs_code)
    
    # 기본관세
    basic_tariff = None
    wto_tariff = None
    for rate in categorized.get('basic', []):
        if rate['tariff_type'] == 'A':
            basic_tariff = rate
        elif rate['tariff_type'] == 'U':
            wto_tariff = rate
    
    # FTA 협정관세
    fta_tariffs = categorized.get('fta', [])
    
    # 국가 필터링
    if country_code:
        applicable_fta_codes = [fta['fta_code'] for fta in get_applicable_fta(country_code)]
        filtered_fta = []
        for fta in fta_tariffs:
            fta_base = ''.join([c for c in fta['tariff_type'] if not c.isdigit()])
            if fta_base in applicable_fta_codes:
                filtered_fta.append(fta)
        fta_tariffs = filtered_fta if filtered_fta else fta_tariffs
    
    # 특별관세
    special_tariffs = categorized.get('special', [])
    
    # 최저세율 도출
    all_rates = []
    
    if basic_tariff:
        all_rates.append({
            'type': '기본관세',
            'type_code': 'A',
            'rate': basic_tariff['tariff_rate'],
            'category': 'basic'
        })
    
    if wto_tariff:
        all_rates.append({
            'type': 'WTO양허세율',
            'type_code': 'U',
            'rate': wto_tariff['tariff_rate'],
            'category': 'basic'
        })
    
    for fta in fta_tariffs[:10]:
        all_rates.append({
            'type': fta['tariff_type_name'],
            'type_code': fta['tariff_type'],
            'rate': fta['tariff_rate'],
            'category': 'fta'
        })
    
    for special in special_tariffs[:5]:
        tariff_code = special.get('tariff_type', '')[:1] if special.get('tariff_type') else ''
        rate = special.get('tariff_rate', 0) or 0
        
        # 추가 부과 관세(보복/덤핑방지/상계/긴급)가 0%면 "미적용"을 의미
        # → 최저세율 후보에서 제외
        if tariff_code in ADDITIVE_TARIFFS and rate == 0:
            continue
        
        all_rates.append({
            'type': special['tariff_type_name'],
            'type_code': special['tariff_type'],
            'rate': rate,
            'category': 'special'
        })
    # 정렬 및 최저세율
    all_rates.sort(key=lambda x: float(x['rate']) if x['rate'] is not None else 999)
    
    for i, r in enumerate(all_rates):
        r['rank'] = i + 1
        r['is_lowest'] = (i == 0)
    
    lowest = all_rates[0] if all_rates else None
    
    # 시각화용 데이터
    chart_data = {
        'labels': [r['type'] for r in all_rates[:8]],
        'values': [float(r['rate']) if r['rate'] is not None else 0 for r in all_rates[:8]],
        'colors': ['#FF6B6B' if r.get('is_lowest') else '#4ECDC4' if r['category'] == 'fta' else '#95A5A6' for r in all_rates[:8]]
    }
    
    return {
        'hs_code': hs_code,
        'hs_info': hs_info,
        'basic_tariff': basic_tariff,
        'wto_tariff': wto_tariff,
        'fta_tariffs': fta_tariffs[:10],
        'special_tariffs': special_tariffs[:5],
        'all_rates': all_rates[:15],
        'lowest_tariff': lowest,
        'chart_data': chart_data,
        'country_code': country_code,
        'applicable_fta': get_applicable_fta(country_code) if country_code else [],
    }


def find_lowest_tariff(hs_code: str, country_code: str = None) -> Dict[str, Any]:
    """최저세율 도출"""
    analysis = analyze_tariff_rates(hs_code, country_code)
    
    return {
        'hs_code': hs_code,
        'country_code': country_code,
        'recommendations': analysis['all_rates'][:5],
        'lowest': analysis['lowest_tariff'],
        'requires_confirmation': True,
    }


def calculate_tax(cif_krw: float, tariff_rate: float) -> Dict[str, float]:
    """관세 및 부가세 계산"""
    tariff = cif_krw * (tariff_rate / 100)
    vat_base = cif_krw + tariff
    vat = vat_base * VAT_RATE
    return {
        'cif_krw': cif_krw,
        'tariff_rate': tariff_rate,
        'tariff_amount': round(tariff),
        'vat_amount': round(vat),
        'total_tax': round(tariff + vat),
    }


def get_tariff_comparison_for_chart(hs_code: str, country_code: str = None) -> Dict[str, Any]:
    """차트용 관세 비교 데이터"""
    analysis = analyze_tariff_rates(hs_code, country_code)
    
    categories = {
        '기본관세': [],
        'FTA협정관세': [],
        '특별관세': []
    }
    
    if analysis['basic_tariff']:
        categories['기본관세'].append({
            'name': '기본관세(A)',
            'rate': analysis['basic_tariff']['tariff_rate']
        })
    
    if analysis['wto_tariff']:
        categories['기본관세'].append({
            'name': 'WTO양허세율(U)',
            'rate': analysis['wto_tariff']['tariff_rate']
        })
    
    for fta in analysis['fta_tariffs'][:5]:
        categories['FTA협정관세'].append({
            'name': fta['tariff_type_name'],
            'rate': fta['tariff_rate']
        })
    
    for special in analysis['special_tariffs'][:3]:
        categories['특별관세'].append({
            'name': special['tariff_type_name'],
            'rate': special['tariff_rate']
        })
    
    return {
        'hs_code': hs_code,
        'categories': categories,
        'lowest': analysis['lowest_tariff']
    }

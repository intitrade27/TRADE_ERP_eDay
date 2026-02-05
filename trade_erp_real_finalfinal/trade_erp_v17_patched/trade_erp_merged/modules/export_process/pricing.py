# -*- coding: utf-8 -*-
"""수출 최소판매가격 계산"""
from typing import Dict, Any
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.exchange import get_exchange_rate

def calculate_min_selling_price(cif_krw: float, tariff_amount: float, vat_amount: float, target_margin_rate: float, export_currency: str = "USD", export_exchange_rate: float = None, extra_costs: float = 0) -> Dict[str, Any]:
    """최소판매가격 계산"""
    total_cost = cif_krw + tariff_amount + vat_amount + extra_costs
    min_price_krw = total_cost / (1 - target_margin_rate / 100)
    margin = min_price_krw - total_cost
    
    if not export_exchange_rate:
        rate = get_exchange_rate(export_currency)
        export_exchange_rate = rate['rate'] if rate else 1300
    
    min_price_foreign = min_price_krw / export_exchange_rate
    
    return {
        'total_cost': total_cost,
        'margin_rate': target_margin_rate,
        'margin_amount': round(margin),
        'min_price_krw': round(min_price_krw),
        'min_price_foreign': round(min_price_foreign, 2),
        'currency': export_currency,
        'exchange_rate': export_exchange_rate,
    }


def calculate_profit_analysis(
    selling_price_foreign: float,
    total_cost_krw: float,
    export_currency: str = "USD",
    exchange_rate: float = None,
) -> Dict[str, Any]:
    """
    판매가격 대비 수익 분석
    
    Args:
        selling_price_foreign: 실제 판매가격 (외화)
        total_cost_krw: 총 원가 (원화)
        export_currency: 통화
        exchange_rate: 환율
    """
    if not exchange_rate:
        rate = get_exchange_rate(export_currency)
        exchange_rate = rate['rate'] if rate else 1300
    
    selling_price_krw = selling_price_foreign * exchange_rate
    profit_krw = selling_price_krw - total_cost_krw
    profit_rate = (profit_krw / selling_price_krw) * 100 if selling_price_krw > 0 else 0
    
    return {
        'selling_price_foreign': selling_price_foreign,
        'selling_price_krw': round(selling_price_krw),
        'total_cost_krw': total_cost_krw,
        'profit_krw': round(profit_krw),
        'profit_rate': round(profit_rate, 2),
        'is_profitable': profit_krw > 0,
    }

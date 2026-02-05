# -*- coding: utf-8 -*-
"""수입 과세가격 계산"""
import logging
from typing import Dict, Any
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.constants import VAT_RATE
from api.exchange import get_exchange_rate

logger = logging.getLogger(__name__)

def calculate_cif(item_value: float, freight: float, insurance: float, currency: str = "USD", exchange_rate: float = None) -> Dict[str, Any]:
    """CIF 과세가격 계산"""
    if not exchange_rate:
        rate_info = get_exchange_rate(currency)
        exchange_rate = rate_info['rate'] if rate_info else 1300
    
    cif_foreign = item_value + freight + insurance
    cif_krw = cif_foreign * exchange_rate
    
    return {
        'item_value': item_value,
        'freight': freight,
        'insurance': insurance,
        'cif_foreign': cif_foreign,
        'currency': currency,
        'exchange_rate': exchange_rate,
        'cif_krw': round(cif_krw),
    }

def calculate_taxes(cif_krw: float, tariff_rate: float) -> Dict[str, Any]:
    """관세/부가세 계산"""
    tariff = cif_krw * (tariff_rate / 100)
    vat_base = cif_krw + tariff
    vat = vat_base * VAT_RATE
    return {
        'cif_krw': cif_krw,
        'tariff_rate': tariff_rate,
        'tariff_amount': round(tariff),
        'vat_amount': round(vat),
        'total_tax': round(tariff + vat),
        'total_payment': round(cif_krw + tariff + vat),
    }

def calculate_full_import_cost(item_value: float, freight: float, insurance: float, tariff_rate: float, currency: str = "USD", exchange_rate: float = None) -> Dict[str, Any]:
    cif = calculate_cif(item_value, freight, insurance, currency, exchange_rate)
    tax = calculate_taxes(cif['cif_krw'], tariff_rate)
    return {**cif, **tax}

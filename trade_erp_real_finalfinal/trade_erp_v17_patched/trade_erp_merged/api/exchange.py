# -*- coding: utf-8 -*-
"""
환율 API 모듈
- 한국수출입은행 환율 API
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)


class ExchangeRateAPI:
    """한국수출입은행 환율 API"""
    
    API_URL = "https://www.koreaexim.go.kr/site/program/financial/exchangeJSON"
    
    def __init__(self):
        self.api_key = settings.exim_api_key
    
    def get_rate(self, currency: str = "USD", search_date: str = None) -> Optional[Dict[str, Any]]:
        """환율 조회"""
        if not self.api_key:
            logger.warning("[EXCHANGE] API 키 미설정")
            return None
        
        if not search_date:
            search_date = datetime.now().strftime("%Y%m%d")
        
        try:
            response = requests.get(self.API_URL, params={
                "authkey": self.api_key,
                "searchdate": search_date,
                "data": "AP01",
            }, timeout=10)
            
            data = response.json()
            if not data:
                # 주말/공휴일 → 이전 영업일
                return self._get_previous_day(currency, search_date)
            
            for item in data:
                if item.get('cur_unit') == currency:
                    rate = float(item.get('deal_bas_r', '0').replace(',', ''))
                    return {
                        'currency': currency,
                        'rate': rate,
                        'date': search_date,
                        'source': '한국수출입은행',
                    }
            return None
        except Exception as e:
            logger.error(f"[EXCHANGE] 조회 실패: {e}")
            return None
    
    def _get_previous_day(self, currency: str, from_date: str) -> Optional[Dict]:
        date_obj = datetime.strptime(from_date, "%Y%m%d")
        for i in range(1, 8):
            prev = (date_obj - timedelta(days=i)).strftime("%Y%m%d")
            result = self.get_rate(currency, prev)
            if result:
                result['note'] = f"조회일({from_date}) 데이터 없어 {prev} 기준"
                return result
        return None
    
    def get_all_rates(self, search_date: str = None) -> Dict[str, Any]:
        """주요 통화 일괄 조회"""
        currencies = ["USD", "EUR", "JPY(100)", "CNH", "GBP"]
        results = {}
        for cur in currencies:
            rate = self.get_rate(cur, search_date)
            if rate:
                results[cur] = rate
        return results


def get_exchange_rate(currency: str = "USD", date: str = None) -> Optional[Dict]:
    return ExchangeRateAPI().get_rate(currency, date)

def get_all_rates(date: str = None) -> Dict:
    return ExchangeRateAPI().get_all_rates(date)


class CustomsExchangeRate:
    """관세청 고시환율 (수동 관리)"""
    
    def __init__(self):
        self.rates = {}
    
    def set_rate(self, currency: str, rate: float, start_date: str, end_date: str):
        """고시환율 설정 (관세청 발표 기준)"""
        self.rates[currency] = {
            'rate': rate,
            'start_date': start_date,
            'end_date': end_date,
            'source': '관세청 고시환율',
        }
    
    def get_rate(self, currency: str) -> Optional[Dict]:
        """고시환율 조회"""
        return self.rates.get(currency)
    
    def get_all_rates(self) -> Dict:
        return self.rates

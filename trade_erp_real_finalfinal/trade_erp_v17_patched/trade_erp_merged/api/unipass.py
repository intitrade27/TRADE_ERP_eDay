# -*- coding: utf-8 -*-
"""
관세청 Unipass API 모듈
- 각 API별 개별 키 처리
"""

import logging
from typing import Dict, Any, List
import requests
import xml.etree.ElementTree as ET

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)


class UnipassError(Exception):
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        logger.error(f"[UNIPASS_ERROR] {error_code}: {message}")
        super().__init__(self.message)


class UnipassAPI:
    """관세청 Unipass API - 개별 키 관리"""
    
    BASE_URL = "https://unipass.customs.go.kr:38010/ext/rest"
    
    # API별 키 매핑
    API_KEYS = {
        "hs_code": lambda: settings.unipass_hs_code_api_key,
        "tariff": lambda: settings.unipass_tariff_api_key,
        "customs_check": lambda: settings.unipass_customs_check_api_key,
        "cargo": lambda: settings.unipass_cargo_api_key,
    }
    
    def _get_api_key(self, api_type: str) -> str:
        """API 타입별 키 반환"""
        key_func = self.API_KEYS.get(api_type)
        if not key_func:
            raise UnipassError(f"알 수 없는 API 타입: {api_type}", "INVALID_API_TYPE")
        
        key = key_func()
        if not key:
            raise UnipassError(f"{api_type} API 키가 설정되지 않았습니다.", "API_KEY_MISSING")
        return key
    
    def _request(self, endpoint: str, params: Dict[str, str], api_type: str) -> str:
        """API 요청"""
        api_key = self._get_api_key(api_type)
        params['crkyCn'] = api_key
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise UnipassError(f"API 요청 실패: {e}", "REQUEST_ERROR")
    
    def _parse_xml(self, xml_text: str) -> List[Dict[str, str]]:
        """XML 파싱"""
        try:
            root = ET.fromstring(xml_text)
            results = []
            for item in root.findall('.//item'):
                result = {child.tag: child.text for child in item}
                results.append(result)
            return results
        except ET.ParseError as e:
            raise UnipassError(f"XML 파싱 실패: {e}", "PARSE_ERROR")
    
    def search_hs_code(self, keyword: str) -> List[Dict[str, Any]]:
        """HS CODE 검색 API"""
        logger.info(f"[UNIPASS] HS CODE 검색: {keyword}")
        params = {'hsSgn': keyword}
        
        try:
            xml_response = self._request('hsCodeNavi', params, 'hs_code')
            results = self._parse_xml(xml_response)
            return [{
                'hs_code': item.get('hsSgn', ''),
                'name_kr': item.get('hsSgnNm', ''),
                'description': item.get('hsExpln', ''),
            } for item in results]
        except Exception as e:
            logger.error(f"[UNIPASS] HS CODE 검색 실패: {e}")
            return []
    
    def get_tariff_rate(self, hs_code: str) -> List[Dict[str, Any]]:
        """관세율 조회 API"""
        logger.info(f"[UNIPASS] 관세율 조회: {hs_code}")
        params = {'hsSgn': hs_code}
        
        try:
            xml_response = self._request('tariffRate', params, 'tariff')
            results = self._parse_xml(xml_response)
            return [{
                'hs_code': item.get('hsSgn', ''),
                'tariff_type': item.get('tariffTp', ''),
                'tariff_rate': item.get('tariffRt', ''),
            } for item in results]
        except Exception as e:
            logger.error(f"[UNIPASS] 관세율 조회 실패: {e}")
            return []
    
    def get_customs_check_items(self, hs_code: str, import_export: str = "1") -> List[Dict[str, Any]]:
        """세관장확인대상물품 조회 API"""
        logger.info(f"[UNIPASS] 세관장확인 조회: {hs_code}")
        params = {'hsSgn': hs_code, 'expcImptSe': import_export}
        
        try:
            xml_response = self._request('retrieveCcctLworCd', params, 'customs_check')
            results = self._parse_xml(xml_response)
            return [{
                'hs_code': item.get('hsSgn', ''),
                'agency_name': item.get('rqirAgncyNm', ''),
                'requirement': item.get('rqirNm', ''),
                'law_name': item.get('rltLwNm', ''),
            } for item in results]
        except Exception as e:
            logger.error(f"[UNIPASS] 세관장확인 조회 실패: {e}")
            return []
    
    def get_clearance_progress(self, bl_number: str) -> List[Dict[str, Any]]:
        """화물통관진행정보 조회 API"""
        logger.info(f"[UNIPASS] 통관진행 조회: {bl_number}")
        params = {'hblNo': bl_number}
        
        try:
            xml_response = self._request('cargTrckPrgsInfoQry', params, 'cargo')
            results = self._parse_xml(xml_response)
            return [{
                'bl_number': item.get('hblNo', ''),
                'stage_code': item.get('prgsStCd', ''),
                'stage_name': item.get('prgsStNm', ''),
                'process_date': item.get('prcsDttm', ''),
            } for item in results]
        except Exception as e:
            logger.error(f"[UNIPASS] 통관진행 조회 실패: {e}")
            return []


# 편의 함수
def search_hs_code_api(keyword: str) -> List[Dict]:
    return UnipassAPI().search_hs_code(keyword)

def get_tariff_rate_api(hs_code: str) -> List[Dict]:
    return UnipassAPI().get_tariff_rate(hs_code)

def check_customs_requirements(hs_code: str, import_export: str = "1") -> List[Dict]:
    return UnipassAPI().get_customs_check_items(hs_code, import_export)

def get_clearance_status(bl_number: str) -> List[Dict]:
    return UnipassAPI().get_clearance_progress(bl_number)

# -*- coding: utf-8 -*-
"""
파일 분석 모듈
- OpenAI GPT-4 Vision을 활용한 문서/이미지 분석
- Invoice, Packing List, B/L 등에서 데이터 자동 추출
"""

import logging
import base64
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import settings, UPLOADS_DIR

logger = logging.getLogger(__name__)


class FileAnalyzer:
    """파일 분석기 - OpenAI GPT-4 Vision 기반"""
    
    SUPPORTED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    SUPPORTED_DOC_TYPES = ['.pdf', '.csv', '.xlsx', '.xls']
    
    def __init__(self):
        self.api_key = settings.openai_api_key
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def analyze_trade_document(self, file_path: str = None, file_bytes: bytes = None, 
                                file_type: str = None, trade_type: str = 'import') -> Dict[str, Any]:
        """무역 서류 분석 및 데이터 추출"""
        if not self.is_configured():
            return {'error': 'OpenAI API 키가 설정되지 않았습니다.', 'extracted_data': {}}
        
        try:
            if file_path:
                file_type = Path(file_path).suffix.lower()
            
            if file_type in ['.csv', '.xlsx', '.xls']:
                return self._analyze_tabular_file(file_path, file_bytes, file_type, trade_type)
            
            return self._analyze_with_vision(file_path, file_bytes, file_type, trade_type)
            
        except Exception as e:
            logger.error(f"[FILE_ANALYZER] 분석 실패: {e}")
            return {'error': str(e), 'extracted_data': {}}
    
    def _analyze_with_vision(self, file_path: str, file_bytes: bytes, 
                             file_type: str, trade_type: str) -> Dict[str, Any]:
        """OpenAI Vision API로 이미지/PDF 분석"""
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        
        if file_path:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
        
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        mime_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
            '.gif': 'image/gif', '.webp': 'image/webp', '.pdf': 'application/pdf',
        }
        mime_type = mime_types.get(file_type, 'image/jpeg')
        
        if trade_type == 'import':
            fields = """item_name, hs_code, quantity, unit, unit_price, item_value, currency,
freight, insurance, import_company, export_company, import_country, export_country,
bl_number, container_no, vessel_name, port_of_loading, port_of_discharge, incoterms"""
        else:
            fields = """item_name, hs_code, quantity, unit, unit_price, item_value, currency,
export_company, import_company, export_country, import_country, incoterms"""

        prompt = f"""이 문서를 분석하여 무역 거래 정보를 추출해주세요.
찾을 필드: {fields}

JSON 형식으로만 응답:
{{"document_type": "문서종류", "confidence": 0.0~1.0, "extracted_data": {{"필드": "값"}}, "notes": "참고사항"}}

숫자는 숫자타입으로, 통화기호는 코드로 변환하세요."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}", "detail": "high"}}
                ]}],
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            extracted = self._clean_extracted_data(result.get('extracted_data', {}))
            
            return {
                'document_type': result.get('document_type', ''),
                'confidence': result.get('confidence', 0),
                'extracted_data': extracted,
                'notes': result.get('notes', ''),
            }
            
        except Exception as e:
            logger.error(f"[FILE_ANALYZER] Vision API 오류: {e}")
            return {'error': str(e), 'extracted_data': {}}
    
    def _analyze_tabular_file(self, file_path: str, file_bytes: bytes,
                              file_type: str, trade_type: str) -> Dict[str, Any]:
        """CSV/Excel 파일 분석"""
        try:
            import io
            if file_path:
                df = pd.read_csv(file_path) if file_type == '.csv' else pd.read_excel(file_path)
            elif file_bytes:
                df = pd.read_csv(io.BytesIO(file_bytes)) if file_type == '.csv' else pd.read_excel(io.BytesIO(file_bytes))
            else:
                return {'error': '파일 데이터가 없습니다.', 'extracted_data': {}}
            
            column_mappings = {
                'item_name': ['품목명', '품명', 'item', 'product', 'description'],
                'hs_code': ['hs code', 'hscode', 'hs', '세번'],
                'quantity': ['수량', 'qty', 'quantity'],
                'unit': ['단위', 'unit'],
                'unit_price': ['단가', 'unit price', 'price'],
                'item_value': ['금액', 'amount', 'total'],
                'currency': ['통화', 'currency'],
            }
            
            extracted = {}
            df.columns = df.columns.str.lower().str.strip()
            
            for field, keywords in column_mappings.items():
                for keyword in keywords:
                    matching_cols = [col for col in df.columns if keyword in col.lower()]
                    if matching_cols:
                        values = df[matching_cols[0]].dropna()
                        if not values.empty:
                            extracted[field] = values.iloc[0]
                        break
            
            return {
                'document_type': 'Tabular Data',
                'confidence': 0.7,
                'extracted_data': self._clean_extracted_data(extracted),
                'notes': f'총 {len(df)}행 데이터',
            }
            
        except Exception as e:
            return {'error': str(e), 'extracted_data': {}}
    
    def _clean_extracted_data(self, data: Dict) -> Dict:
        """추출 데이터 정제"""
        cleaned = {}
        for key, value in data.items():
            if value is None or value == '' or value == 'null':
                continue
            
            if key in ['quantity', 'unit_price', 'item_value', 'freight', 'insurance']:
                if isinstance(value, str):
                    value = re.sub(r'[,$€¥£\s]', '', value)
                    try:
                        value = float(value)
                    except:
                        pass
            
            if key == 'currency':
                currency_map = {'$': 'USD', '€': 'EUR', '¥': 'JPY', '£': 'GBP', '₩': 'KRW'}
                value = currency_map.get(value, value)
                if isinstance(value, str):
                    value = value.upper()
            
            cleaned[key] = value
        
        return cleaned
    
    def save_uploaded_file(self, file_bytes: bytes, filename: str, trade_id: str = None) -> str:
        """업로드된 파일 저장"""
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_name = f"{trade_id}_{timestamp}_{filename}" if trade_id else f"{timestamp}_{filename}"
        save_path = UPLOADS_DIR / save_name
        
        with open(save_path, 'wb') as f:
            f.write(file_bytes)
        
        return str(save_path)


_analyzer = None

def get_analyzer() -> FileAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = FileAnalyzer()
    return _analyzer

def analyze_trade_document(file_path: str = None, file_bytes: bytes = None,
                          file_type: str = None, trade_type: str = 'import') -> Dict[str, Any]:
    return get_analyzer().analyze_trade_document(file_path, file_bytes, file_type, trade_type)

def save_uploaded_file(file_bytes: bytes, filename: str, trade_id: str = None) -> str:
    return get_analyzer().save_uploaded_file(file_bytes, filename, trade_id)

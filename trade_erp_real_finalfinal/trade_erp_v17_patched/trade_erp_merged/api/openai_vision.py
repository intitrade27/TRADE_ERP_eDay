# -*- coding: utf-8 -*-
"""
OpenAI Vision API 모듈
- 이미지 분석으로 HS CODE 추천
- 문서 분석
"""

import logging
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIVisionError(Exception):
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class OpenAIVision:
    """OpenAI Vision API - 이미지 분석"""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def analyze_product_image(self, image_path: str = None, image_bytes: bytes = None) -> Dict[str, Any]:
        """물품 이미지 분석 → HS CODE 추천"""
        if not self.is_configured():
            raise OpenAIVisionError("OpenAI API 키가 설정되지 않았습니다.", "API_KEY_MISSING")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise OpenAIVisionError("openai 패키지가 설치되지 않았습니다.", "IMPORT_ERROR")
        
        if image_path:
            base64_image = self._encode_image(image_path)
        elif image_bytes:
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
        else:
            raise OpenAIVisionError("이미지가 필요합니다.", "NO_IMAGE")
        
        prompt = """이 이미지를 분석하여 무역/관세 분류를 위한 정보를 제공해주세요.

다음 JSON 형식으로만 응답하세요:
{
    "product_name_kr": "물품명 (한글)",
    "product_name_en": "Product Name (English)",
    "description": "물품 상세 설명",
    "material": "주요 재질",
    "category": "분류 카테고리",
    "hs_code_candidates": [
        {"code": "10자리 HS CODE", "name": "품목명", "confidence": 0.0~1.0}
    ]
}

hs_code_candidates는 가장 관련성 높은 5개를 confidence 순으로 제공하세요."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
                    ]
                }],
                max_tokens=1000,
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            logger.info(f"[OPENAI] 이미지 분석 완료: {result.get('product_name_kr')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"[OPENAI] JSON 파싱 실패: {e}")
            return {'product_name_kr': '분석 실패', 'hs_code_candidates': []}
        except Exception as e:
            raise OpenAIVisionError(f"API 요청 실패: {e}", "API_ERROR")
    
    def extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 물품 관련 키워드 추출"""
        if not self.is_configured():
            return [w.strip() for w in text.split() if len(w.strip()) > 1]
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": f"다음 문장에서 물품/제품을 나타내는 명사만 추출하세요. 쉼표로 구분:\n\n{text}"
                }],
                max_tokens=100,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            return [n.strip() for n in result.split(',') if n.strip()]
        except:
            return [w.strip() for w in text.split() if len(w.strip()) > 1]


def analyze_product_image(image_path: str = None, image_bytes: bytes = None) -> Dict[str, Any]:
    return OpenAIVision().analyze_product_image(image_path, image_bytes)

def extract_keywords(text: str) -> List[str]:
    return OpenAIVision().extract_keywords(text)

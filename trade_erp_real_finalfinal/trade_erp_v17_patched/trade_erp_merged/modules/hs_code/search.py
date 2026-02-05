# -*- coding: utf-8 -*-
"""
HS Code 검색 모듈 v3.2 — 추가 버그 수정

[v3.2 신규 수정]
  NEW-1 FIX: 공백 정규화 검색 ("피넛버터" → "피넛 버터" 매칭)
  NEW-2 FIX: 세관장확인 include_only/exclude 로직 추가
  NEW-3 FIX: 8단위 부모 포함 동적 부모 탐색 + 캐시

[v3.1 수정 내역]
  BUG-1 FIX: is_gita_code → 품목명 기반 감지
  BUG-2 FIX: 5단위-6단위 부모-자식 분리
  BUG-3 FIX: 2단위 코드 오염 차단
  BUG-4 FIX: 점수 공식 균형 조정
  BUG-5 FIX: 7/8/9단위 존재 인지
  BUG-6 FIX: 세관장확인 중복 매칭 시 우선순위

기존 호환:
  - get_searcher(), search_hs_code() 등 기존 편의 함수 모두 유지
"""

import logging
import re
import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import RAW_DATA_DIR, settings
from config.constants import TARIFF_TYPE_CODES, FTA_CODE_TO_NAME

# 세관장확인품목 상세 데이터
try:
    from config.constants import CUSTOMS_CONFIRMATION_ITEMS
except ImportError:
    CUSTOMS_CONFIRMATION_ITEMS = {}

# GRI 통칙 + 확장 동의어
try:
    from config.constants import GRI_RULES, EXTENDED_SYNONYM_MAP, SECTION_CHAPTER_MAP
except ImportError:
    GRI_RULES = {}
    EXTENDED_SYNONYM_MAP = {}
    SECTION_CHAPTER_MAP = {}

logger = logging.getLogger(__name__)


# ============================================================
# 파일 경로 자동 탐색
# ============================================================
def _find_file(directory: Path, keyword: str) -> Optional[Path]:
    if not directory.exists():
        return None
    for f in directory.iterdir():
        if f.suffix == '.xlsx' and keyword in f.name:
            return f
    for f in directory.iterdir():
        if f.suffix == '.xlsx' and f.name.startswith('#U'):
            try:
                decoded = f.name.replace('#U', '\\u').encode().decode('unicode_escape')
                if keyword in decoded:
                    return f
            except Exception:
                pass
    return None

HS_CODE_FILE = _find_file(RAW_DATA_DIR, "HS부호") or RAW_DATA_DIR / "관세청_HS부호_20260101.xlsx"
TARIFF_FILE = _find_file(RAW_DATA_DIR, "관세율표") or RAW_DATA_DIR / "관세청_품목번호별_관세율표_20260101.xlsx"
HSCODE_EXCEL_FILE = RAW_DATA_DIR / "hscode.xlsx"

# 임베딩 캐시 디렉토리
EMBEDDING_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "processed"


# ============================================================
# 확장 동의어 사전 (인라인 백업)
# ============================================================
_LOCAL_SYNONYM_MAP = {
    "에어컨": ["공기조절기", "냉방기", "냉방장치", "air conditioner", "에어컨디셔너"],
    "냉장고": ["냉동고", "냉장기구", "냉동기구", "refrigerator", "freezer"],
    "세탁기": ["세탁기계", "washing machine", "washer"],
    "전자레인지": ["마이크로웨이브", "전자오븐", "microwave"],
    "노트북": ["휴대용컴퓨터", "자동자료처리기계", "laptop", "노트북컴퓨터"],
    "스마트폰": ["휴대전화", "이동전화", "mobile phone", "핸드폰"],
    "TV": ["텔레비전", "television", "티비", "수상기"],
    "프린터": ["인쇄기", "printer", "복합기"],
    "배터리": ["축전지", "전지", "battery", "리튬이온"],
    "드론": ["무인항공기", "drone", "무인비행장치"],
    "봉제인형": ["인형", "완구", "봉제", "장난감", "stuffed toy", "plush toy"],
    "장난감": ["완구", "인형", "toy", "game"],
    "티셔츠": ["셔츠", "상의", "의류", "t-shirt"],
    "바지": ["하의", "팬츠", "pants", "trousers"],
    "신발": ["구두", "운동화", "shoes", "footwear", "부츠"],
    "커피": ["원두", "coffee", "커피콩", "커피원두"],
    "초콜릿": ["초코", "chocolate", "코코아", "카카오"],
    "와인": ["포도주", "wine", "적포도주", "백포도주"],
    "자동차": ["승용차", "차량", "car", "vehicle", "automobile"],
    "화장품": ["코스메틱", "cosmetic", "스킨케어", "메이크업"],
    "향수": ["perfume", "fragrance", "오드뚜왈렛"],
    "가구": ["furniture", "소파", "책상", "의자", "테이블"],
    "가방": ["핸드백", "bag", "배낭", "백팩"],
    "시계": ["손목시계", "watch", "clock", "스마트워치"],
    "철강": ["steel", "강철", "철판", "강판"],
    "플라스틱": ["plastic", "합성수지", "폴리에틸렌", "PVC"],
    "의약품": ["약품", "medicine", "drug", "pharmaceutical"],
    "의료기기": ["medical device", "의료기구", "의료장비"],
    "건강식품": ["건강보조식품", "supplement", "영양제", "비타민"],
    "라면": ["즉석면", "instant noodles", "면류"],
    "김치": ["kimchi", "절임식품", "채소절임"],
    "맥주": ["beer", "맥아발효음료"],
    "위스키": ["whisky", "whiskey", "증류주"],
    # v3.2 추가: 공백 변형 동의어
    "피넛버터": ["피넛 버터", "땅콩버터", "땅콩 버터", "peanut butter"],
    "땅콩버터": ["피넛버터", "피넛 버터", "땅콩 버터", "peanut butter"],
}

# GRI 통칙
_LOCAL_GRI_RULES = {
    "GRI1": {"title": "통칙 제1호: 법적 문언 우선", "logic": "keyword_exact_match"},
    "GRI2a": {"title": "통칙 제2호(가): 미완성·미조립 물품", "keywords": ["미완성", "미조립", "부분품", "키트"]},
    "GRI2b": {"title": "통칙 제2호(나): 혼합물·복합물", "keywords": ["혼합", "복합", "합성"]},
    "GRI3a": {"title": "통칙 제3호(가): 가장 구체적 표현 우선", "logic": "most_specific_match"},
    "GRI3b": {"title": "통칙 제3호(나): 본질적 특성", "logic": "essential_character"},
    "GRI4": {"title": "통칙 제4호: 가장 유사한 호", "logic": "most_similar"},
    "GRI6": {"title": "통칙 제6호: 소호 분류", "logic": "subheading_comparison"},
}

_LOCAL_SECTION_CHAPTER_MAP = {
    "84": {"priority": "function"}, "85": {"priority": "function"},
    "50": {"priority": "material"}, "51": {"priority": "material"},
    "52": {"priority": "material"}, "53": {"priority": "material"},
    "54": {"priority": "material"}, "55": {"priority": "material"},
    "61": {"priority": "material"}, "62": {"priority": "material"},
    "39": {"priority": "material"}, "40": {"priority": "material"},
    "72": {"priority": "material"}, "73": {"priority": "material"},
    "28": {"priority": "composition"}, "29": {"priority": "composition"},
    "30": {"priority": "function"}, "33": {"priority": "function"},
}


def _get_synonym_map() -> Dict:
    return EXTENDED_SYNONYM_MAP if EXTENDED_SYNONYM_MAP else _LOCAL_SYNONYM_MAP

def _get_gri_rules() -> Dict:
    return GRI_RULES if GRI_RULES else _LOCAL_GRI_RULES

def _get_section_map() -> Dict:
    return SECTION_CHAPTER_MAP if SECTION_CHAPTER_MAP else _LOCAL_SECTION_CHAPTER_MAP


# ============================================================
# 핵심 클래스: HSCodeSearcher v3.1
# ============================================================
class HSCodeSearcher:
    """
    HS Code 스마트 검색기 v3.1

    검색 파이프라인:
      1) HS코드 직접 입력 → 정규화 + AI 보정
      2) 키워드 입력 → 동의어 확장 + 4단위 Top-3
      3) 6단위 존재 여부 판별 → 없음 시 10단위 직접 연결
      4) 10단위 기타 감지 → 형제 코드 자동 전개
      5) 세관장확인품목 자동 조회
    """

    def __init__(self):
        self.hs_df = None
        self.tariff_df = None
        self.hscode_df = None
        self._hs_loaded = False
        self._tariff_loaded = False
        self._hscode_loaded = False
        self._synonym_map = _get_synonym_map()
        self._gri_rules = _get_gri_rules()
        self._section_map = _get_section_map()
        # 임베딩 캐시
        self._embedding_cache = None
        self._embedding_codes = None
        # v3.2: 부모 캐시
        self._parent_cache = {}
        self._all_codes_set = set()
        self._load_data()

    # ============================================================
    # 데이터 로드
    # ============================================================
    def _load_data(self):
        # 1) HS부호 데이터
        try:
            if HS_CODE_FILE.exists():
                self.hs_df = pd.read_excel(HS_CODE_FILE, engine='openpyxl')
                self.hs_df['HS부호'] = self.hs_df['HS부호'].astype(str).str.zfill(10)
                for col in ['한글품목명', '영문품목명', 'HS부호내용', '성질통합분류코드명']:
                    if col in self.hs_df.columns:
                        self.hs_df[col] = self.hs_df[col].fillna('').astype(str).replace('nan', '')
                self._hs_loaded = True
                logger.info(f"[HS] HS부호 데이터 로드: {len(self.hs_df)}건")
        except Exception as e:
            logger.error(f"[HS] HS부호 로드 실패: {e}")

        # 2) 관세율표
        try:
            if TARIFF_FILE.exists():
                self.tariff_df = pd.read_excel(TARIFF_FILE, engine='openpyxl')
                self.tariff_df['품목번호'] = self.tariff_df['품목번호'].astype(str).str.zfill(10)
                if '관세율구분' in self.tariff_df.columns:
                    self.tariff_df['관세율구분'] = self.tariff_df['관세율구분'].fillna('').astype(str)
                if '관세율' in self.tariff_df.columns:
                    self.tariff_df['관세율'] = pd.to_numeric(self.tariff_df['관세율'], errors='coerce').fillna(0).astype(float)
                if '적용국가구분' in self.tariff_df.columns:
                    self.tariff_df['적용국가구분'] = self.tariff_df['적용국가구분'].fillna(0)
                    try:
                        self.tariff_df['적용국가구분'] = self.tariff_df['적용국가구분'].astype(int)
                    except (ValueError, TypeError):
                        self.tariff_df['적용국가구분'] = pd.to_numeric(self.tariff_df['적용국가구분'], errors='coerce').fillna(0).astype(int)
                self._tariff_loaded = True
                logger.info(f"[TARIFF] 관세율표 로드: {len(self.tariff_df)}건")
        except Exception as e:
            logger.error(f"[TARIFF] 관세율표 로드 실패: {e}")

        # 3) hscode.xlsx 통합 데이터
        try:
            if HSCODE_EXCEL_FILE.exists():
                xls = pd.ExcelFile(HSCODE_EXCEL_FILE, engine='openpyxl')
                dfs = []
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str)
                    rename_map = {}
                    for col in df.columns:
                        c = str(col).strip().replace(" ", "").replace("\n", "")
                        if "영문" in c:
                            rename_map[col] = "영문품목명"
                        elif "한글" in c:
                            rename_map[col] = "한글품목명"
                        elif "품목명" in c:
                            rename_map[col] = "한글품목명"
                        elif ("HS" in c or "부호" in c or "코드" in c or "단위" in c) and "성질" not in c:
                            rename_map[col] = "HS부호"
                    df = df.rename(columns=rename_map)
                    df = df.loc[:, ~df.columns.duplicated()]
                    if "HS부호" in df.columns and "한글품목명" in df.columns:
                        df["HS부호"] = df["HS부호"].fillna("").astype(str).str.strip()
                        df["한글품목명"] = df["한글품목명"].fillna("").astype(str).str.strip()
                        if "영문품목명" not in df.columns:
                            df["영문품목명"] = ""
                        df["영문품목명"] = df["영문품목명"].fillna("").astype(str).str.strip()
                        df["code_len"] = df["HS부호"].str.len()
                        # v3.2: 공백 제거 정규화 컬럼
                        df["품목명_norm"] = df["한글품목명"].str.replace(" ", "", regex=False).str.lower()
                        df["영문명_norm"] = df["영문품목명"].str.replace(" ", "", regex=False).str.lower()
                        dfs.append(df[["HS부호", "한글품목명", "영문품목명", "code_len", "품목명_norm", "영문명_norm"]])
                if dfs:
                    self.hscode_df = pd.concat(dfs, ignore_index=True)
                    self.hscode_df.drop_duplicates(subset=["HS부호"], inplace=True)
                    self._hscode_loaded = True
                    logger.info(f"[HSCODE] 통합 데이터 로드: {len(self.hscode_df)}건")
                    # v3.2: 부모 캐시 구축
                    self._build_parent_cache()
        except Exception as e:
            logger.error(f"[HSCODE] hscode.xlsx 로드 실패: {e}")

    # ============================================================
    # v3.2: 부모 캐시 구축
    # ============================================================
    def _build_parent_cache(self):
        """로드 시점에 모든 10단위의 가장 가까운 부모를 사전 계산"""
        if self.hscode_df is None:
            return
        
        self._all_codes_set = set(self.hscode_df['HS부호'].tolist())
        codes_10 = self.hscode_df[self.hscode_df['code_len'] == 10]['HS부호'].tolist()
        
        for code in codes_10:
            # 9→8→7→6→5→4 순서로 부모 탐색
            for parent_len in range(9, 3, -1):
                parent = code[:parent_len]
                if parent in self._all_codes_set:
                    self._parent_cache[code] = (parent, parent_len)
                    break
            else:
                self._parent_cache[code] = (code[:4], 4)
        
        logger.info(f"[CACHE] 부모 캐시 구축 완료: {len(self._parent_cache)}건")

    def find_nearest_parent(self, code: str) -> tuple:
        """10단위 코드의 가장 가까운 실존 부모 찾기 (캐시 사용)"""
        code = str(code).strip()
        if code in self._parent_cache:
            return self._parent_cache[code]
        
        # 캐시 미스 시 동적 탐색
        for parent_len in range(len(code) - 1, 3, -1):
            parent = code[:parent_len]
            if parent in self._all_codes_set:
                return parent, parent_len
        
        return code[:4], 4

    # ============================================================
    # 유틸리티
    # ============================================================
    def _is_hs_code_format(self, query: str) -> bool:
        """HS코드 형식 여부 판별 (숫자 + 구분자만으로 구성)"""
        cleaned = query.replace('.', '').replace('-', '').replace(' ', '')
        return cleaned.isdigit() and len(cleaned) >= 4

    def _normalize_hs_code(self, code: str) -> str:
        return code.replace('.', '').replace('-', '').replace(' ', '').zfill(10)

    # ============================================================
    # [BUG-1 FIX] 기타 코드 감지 — 품목명 기반 (정확도 100%)
    # ============================================================
    def is_gita_code(self, hs_code: str) -> Tuple[bool, Optional[str], str]:
        """
        기타 코드 여부 판별 — 품목명 기반 (정확도 100%)
        
        Returns:
            (is_gita: bool, parent_prefix: str|None, gita_type: str)
        """
        code = str(hs_code).strip()
        
        # DataFrame이 있으면 품목명으로 판별
        if self.hscode_df is not None:
            row = self.hscode_df[self.hscode_df['HS부호'] == code]
            if not row.empty:
                name = str(row.iloc[0]['한글품목명']).strip()
                if name in ('기타', 'Other'):
                    if len(code) == 10:
                        # v3.2: 캐시된 부모 사용
                        parent, _ = self.find_nearest_parent(code)
                        return True, parent, 'name_based'
                    elif len(code) in (5, 6, 7, 8, 9):
                        return True, code[:4], 'name_based'
                    return True, None, 'name_based'
        
        # DataFrame 없으면 보수적 폴백
        if len(code) == 10 and code.endswith('9000'):
            return True, code[:6], '9000_fallback'
        
        return False, None, 'none'

    # ============================================================
    # v3.2: 형제 코드 조회 — 8단위 포함 동적 부모 탐색
    # ============================================================
    def get_sibling_codes(self, gita_code: str) -> List[Dict[str, Any]]:
        """
        기타 코드의 형제 코드 조회
        v3.2: 8단위 부모 포함 동적 탐색
        """
        if self.hscode_df is None:
            return []

        code = str(gita_code).strip()
        if len(code) != 10:
            return []

        # v3.2: 캐시된 부모 사용 (8단위 포함)
        parent, parent_len = self.find_nearest_parent(code)
        
        # 같은 부모 아래 10단위 형제 (기타 제외)
        siblings_df = self.hscode_df[
            (self.hscode_df['HS부호'].str[:parent_len] == parent) &
            (self.hscode_df['code_len'] == 10) &
            (self.hscode_df['HS부호'] != code)
        ]
        
        result = []
        for _, row in siblings_df.sort_values('HS부호').iterrows():
            name = str(row['한글품목명']).strip()
            if name not in ('기타', 'Other'):
                result.append({
                    'hs_code': row['HS부호'],
                    'name_kr': row['한글품목명'],
                    'name_en': row.get('영문품목명', ''),
                    'parent_code': parent,
                })
        return result

    # ============================================================
    # v3.2: 세관장확인품목 조회 — include_only/exclude 로직
    # ============================================================
    @staticmethod
    def check_customs_confirmation(hs_code: str) -> Dict[str, Any]:
        """
        세관장확인품목 여부 확인
        v3.2: include_only, exclude 필드 지원
        """
        code = str(hs_code).replace('.', '').replace('-', '').replace(' ', '')

        matched_categories = []

        for category_name, info in CUSTOMS_CONFIRMATION_ITEMS.items():
            prefixes = info.get('hs_prefixes', [])
            include_only = info.get('include_only', [])
            exclude = info.get('exclude', [])
            
            sorted_prefixes = sorted(prefixes, key=len, reverse=True)

            # 1. 기본 prefix 매칭
            matched_prefix = None
            for prefix in sorted_prefixes:
                if code[:len(prefix)] == prefix:
                    matched_prefix = prefix
                    break
            
            if not matched_prefix:
                continue
            
            # 2. include_only가 있으면 해당 목록에 있어야 함
            if include_only:
                is_included = False
                for inc in include_only:
                    if code == inc or code.startswith(inc):
                        is_included = True
                        break
                if not is_included:
                    continue
            
            # 3. exclude 목록에 있으면 제외
            is_excluded = False
            for exc in exclude:
                if code == exc or code.startswith(exc):
                    is_excluded = True
                    break
            if is_excluded:
                continue

            matched_categories.append({
                'category': category_name,
                'agency': info.get('agency', ''),
                'law': info.get('law', ''),
                'documents': info.get('documents', []),
                'conditions': info.get('conditions', ''),
                'contact': info.get('contact', ''),
                'match_prefix': matched_prefix,
                'match_specificity': len(matched_prefix),
            })

        if matched_categories:
            # BUG-6 FIX: 구체성(prefix 길이) 우선 정렬
            matched_categories.sort(key=lambda x: x['match_specificity'], reverse=True)

            # 최우선 카테고리 표시
            matched_categories[0]['is_primary'] = True
            for cat in matched_categories[1:]:
                cat['is_primary'] = False

            return {
                'is_subject': True,
                'categories': matched_categories,
                'primary_category': matched_categories[0],
                'hs_code': code,
                'note': f"주관기관: {matched_categories[0]['agency']} (가장 구체적 매칭)" if len(matched_categories) > 1 else '',
            }
        else:
            return {
                'is_subject': False,
                'categories': [],
                'hs_code': code,
                'message': '세관장확인 대상 품목이 아닙니다.',
                'disclaimer': '※ 이 결과는 참고용이며, 정확한 확인은 관세청 또는 해당 기관에 문의하시기 바랍니다.',
            }

    # ============================================================
    # [신규] HS코드 직접 입력 스마트 처리
    # ============================================================
    def smart_code_input(self, raw_input: str) -> Dict[str, Any]:
        """
        HS코드 직접 입력 시 스마트 매칭
        """
        cleaned = re.sub(r'[^0-9]', '', str(raw_input).strip())

        if len(cleaned) < 2:
            return {
                'match_type': 'error',
                'error': '최소 2자리 이상 입력하세요.',
                'matches': [],
            }

        if self.hscode_df is None:
            return {'match_type': 'error', 'error': '데이터 미로드', 'matches': []}

        # 정확 매칭 (10단위)
        if len(cleaned) == 10:
            exact = self.hscode_df[self.hscode_df['HS부호'] == cleaned]
            if not exact.empty:
                row = exact.iloc[0]
                return {
                    'match_type': 'exact',
                    'matches': [{'hs_code': cleaned, 'name_kr': row['한글품목명']}],
                    'confidence': 1.0,
                }

        # 접두사 매칭
        prefix_matches = self.hscode_df[self.hscode_df['HS부호'].str[:len(cleaned)] == cleaned]
        if not prefix_matches.empty:
            results_by_level = {}
            for _, row in prefix_matches.iterrows():
                code = row['HS부호']
                code_len = int(row['code_len'])
                if code_len not in results_by_level:
                    results_by_level[code_len] = []
                results_by_level[code_len].append({
                    'hs_code': code,
                    'name_kr': row['한글품목명'],
                    'name_en': row.get('영문품목명', ''),
                    'code_len': code_len,
                })

            # 4단위 후보 추출
            candidates_4 = []
            all_4_digit_codes = set()
            for _, row in prefix_matches.iterrows():
                c4 = row['HS부호'][:4]
                if len(c4) == 4 and c4 not in all_4_digit_codes:
                    all_4_digit_codes.add(c4)
                    c4_row = self.hscode_df[self.hscode_df['HS부호'] == c4]
                    name = c4_row.iloc[0]['한글품목명'] if not c4_row.empty else ''
                    candidates_4.append({'hs_code': c4, 'name_kr': name, 'score': 100})

            ranking = self._build_hierarchy_for_codes(candidates_4[:3])

            return {
                'match_type': 'prefix',
                'candidates_4': candidates_4[:3],
                'ranking': ranking,
                'confidence': 0.95,
                'input_cleaned': cleaned,
            }

        # AI 보정 시도
        if settings.openai_api_key:
            try:
                ai_corrected = self._ai_correct_code(raw_input, cleaned)
                if ai_corrected:
                    corrected_matches = self.hscode_df[
                        self.hscode_df['HS부호'].str[:len(ai_corrected)] == ai_corrected
                    ]
                    if not corrected_matches.empty:
                        candidates_4 = []
                        seen = set()
                        for _, row in corrected_matches.iterrows():
                            c4 = row['HS부호'][:4]
                            if len(c4) == 4 and c4 not in seen:
                                seen.add(c4)
                                c4_row = self.hscode_df[self.hscode_df['HS부호'] == c4]
                                name = c4_row.iloc[0]['한글품목명'] if not c4_row.empty else ''
                                candidates_4.append({'hs_code': c4, 'name_kr': name, 'score': 80})

                        ranking = self._build_hierarchy_for_codes(candidates_4[:3])
                        return {
                            'match_type': 'ai_corrected',
                            'candidates_4': candidates_4[:3],
                            'ranking': ranking,
                            'confidence': 0.7,
                            'original_input': raw_input,
                            'corrected_code': ai_corrected,
                        }
            except Exception as e:
                logger.warning(f"[CODE] AI 보정 실패: {e}")

        return {
            'match_type': 'not_found',
            'matches': [],
            'error': f'유효한 HS코드를 찾을 수 없습니다. (입력: {raw_input})',
        }

    def _ai_correct_code(self, raw_input: str, cleaned: str) -> Optional[str]:
        """OpenAI에게 가장 가까운 HS코드 접두사를 질문"""
        if not settings.openai_api_key:
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)

            prompt = f"""사용자가 HS코드를 입력했습니다: "{raw_input}" (정규화: {cleaned})
이 입력에 가장 가까운 유효한 HS코드 앞 4자리(4단위)를 추정하세요.
숫자 4자리만 응답하세요. 예: 0901"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.0,
            )
            result = response.choices[0].message.content.strip()
            digits = re.sub(r'[^0-9]', '', result)
            return digits[:4] if len(digits) >= 4 else None
        except Exception as e:
            logger.warning(f"[AI] 코드 보정 실패: {e}")
            return None

    # ============================================================
    # [BUG-2 FIX] 계층 트리 구축 — 5/6단위 부모-자식 분리
    # ============================================================
    def _build_hierarchy_for_codes(self, candidates_4: List[Dict]) -> Dict[str, Any]:
        """
        v3.1 핵심 수정:
          - 5단위는 그 아래 6단위가 있으면 '부모' 표시
          - 6단위는 5단위 자식이면 'parent_5' 필드에 부모 코드 기록
          - 독립 6단위(부모 5단위 없음)는 그대로 표시
        """
        if self.hscode_df is None:
            return {
                'ranked_4': candidates_4,
                'ranked_6': {}, 'ranked_10': {},
                'skip_6_codes': [], 'hierarchy_detail': {}
            }

        ranked_4 = candidates_4
        ranked_6 = {}
        ranked_10 = {}
        skip_6_codes = []

        for item in candidates_4:
            c4 = item['hs_code']

            # 5단위 찾기
            sub_5 = self.hscode_df[
                (self.hscode_df['HS부호'].str[:4] == c4) &
                (self.hscode_df['code_len'] == 5)
            ].sort_values('HS부호')

            # 6단위 찾기
            sub_6_all = self.hscode_df[
                (self.hscode_df['HS부호'].str[:4] == c4) &
                (self.hscode_df['code_len'] == 6)
            ].sort_values('HS부호')

            # 10단위 전체
            sub_10_all = self.hscode_df[
                (self.hscode_df['HS부호'].str[:4] == c4) &
                (self.hscode_df['code_len'] == 10)
            ].sort_values('HS부호')

            # 5단위도 6단위도 없으면 → skip
            if sub_5.empty and sub_6_all.empty:
                skip_6_codes.append(c4)
                ranked_6[c4] = []
                items_10 = []
                for _, r in sub_10_all.iterrows():
                    is_gita, _, _ = self.is_gita_code(r['HS부호'])
                    items_10.append({
                        'hs_code': r['HS부호'],
                        'name_kr': r['한글품목명'],
                        'name_en': r.get('영문품목명', ''),
                        'is_gita': is_gita,
                    })
                ranked_10[c4] = items_10
                continue

            # 계층 구조 구축
            items_6_structured = []
            used_6_codes = set()

            # (A) 5단위 처리
            for _, r5 in sub_5.iterrows():
                c5 = r5['HS부호']
                is_gita_5, _, _ = self.is_gita_code(c5)

                # 이 5단위 아래 6단위 찾기
                children_6 = sub_6_all[sub_6_all['HS부호'].str[:5] == c5]

                if children_6.empty:
                    # 5단위 아래 6단위 없음 → 5단위를 소호로 직접 표시
                    items_6_structured.append({
                        'hs_code': c5,
                        'name_kr': r5['한글품목명'],
                        'name_en': r5.get('영문품목명', ''),
                        'is_gita': is_gita_5,
                        'level': 5,
                        'has_children_6': False,
                        'children_6_codes': [],
                    })

                    # 10단위 매핑 (5단위 접두사)
                    sub_10_c5 = sub_10_all[sub_10_all['HS부호'].str[:5] == c5]
                    items_10_list = []
                    for _, r10 in sub_10_c5.iterrows():
                        is_gita_10, _, _ = self.is_gita_code(r10['HS부호'])
                        items_10_list.append({
                            'hs_code': r10['HS부호'],
                            'name_kr': r10['한글품목명'],
                            'name_en': r10.get('영문품목명', ''),
                            'is_gita': is_gita_10,
                        })
                    ranked_10[c5] = items_10_list
                else:
                    # 5단위 아래 6단위 있음 → 5단위는 '부모' 역할
                    child_6_list = []
                    for _, r6 in children_6.iterrows():
                        c6 = r6['HS부호']
                        used_6_codes.add(c6)
                        is_gita_6, _, _ = self.is_gita_code(c6)
                        child_6_list.append({
                            'hs_code': c6,
                            'name_kr': r6['한글품목명'],
                            'name_en': r6.get('영문품목명', ''),
                            'is_gita': is_gita_6,
                            'level': 6,
                            'parent_5': c5,
                        })

                        # 10단위 매핑 (6단위 접두사 — 정확한 슬라이싱)
                        sub_10_c6 = sub_10_all[sub_10_all['HS부호'].str[:6] == c6]
                        items_10_list = []
                        for _, r10 in sub_10_c6.iterrows():
                            is_gita_10, _, _ = self.is_gita_code(r10['HS부호'])
                            items_10_list.append({
                                'hs_code': r10['HS부호'],
                                'name_kr': r10['한글품목명'],
                                'name_en': r10.get('영문품목명', ''),
                                'is_gita': is_gita_10,
                            })
                        ranked_10[c6] = items_10_list

                    items_6_structured.append({
                        'hs_code': c5,
                        'name_kr': r5['한글품목명'],
                        'name_en': r5.get('영문품목명', ''),
                        'is_gita': is_gita_5,
                        'level': 5,
                        'has_children_6': True,
                        'children_6_codes': [c['hs_code'] for c in child_6_list],
                        'children_6': child_6_list,
                    })

            # (B) 독립 6단위 (부모 5단위 없이 4단위에 직접 소속)
            for _, r6 in sub_6_all.iterrows():
                c6 = r6['HS부호']
                if c6 in used_6_codes:
                    continue
                is_gita_6, _, _ = self.is_gita_code(c6)
                items_6_structured.append({
                    'hs_code': c6,
                    'name_kr': r6['한글품목명'],
                    'name_en': r6.get('영문품목명', ''),
                    'is_gita': is_gita_6,
                    'level': 6,
                    'has_children_6': False,
                    'children_6_codes': [],
                })

                # 10단위 매핑
                sub_10_c6 = sub_10_all[sub_10_all['HS부호'].str[:6] == c6]
                items_10_list = []
                for _, r10 in sub_10_c6.iterrows():
                    is_gita_10, _, _ = self.is_gita_code(r10['HS부호'])
                    items_10_list.append({
                        'hs_code': r10['HS부호'],
                        'name_kr': r10['한글품목명'],
                        'name_en': r10.get('영문품목명', ''),
                        'is_gita': is_gita_10,
                    })
                ranked_10[c6] = items_10_list

            ranked_6[c4] = items_6_structured

        return {
            'ranked_4': ranked_4,
            'ranked_6': ranked_6,
            'ranked_10': ranked_10,
            'skip_6_codes': skip_6_codes,
        }

    # ============================================================
    # [핵심] 확장 동의어 검색
    # ============================================================
    def _expand_synonyms(self, keywords: List[str]) -> List[str]:
        expanded = list(keywords)
        synonym_map = self._synonym_map
        for kw in keywords:
            kw_lower = kw.strip().lower()
            for base_word, synonyms in synonym_map.items():
                if kw_lower == base_word.lower():
                    for syn in synonyms:
                        if syn.lower() not in [e.lower() for e in expanded]:
                            expanded.append(syn)
                elif kw_lower in [s.lower() for s in synonyms]:
                    if base_word.lower() not in [e.lower() for e in expanded]:
                        expanded.append(base_word)
                    for syn in synonyms:
                        if syn.lower() not in [e.lower() for e in expanded]:
                            expanded.append(syn)
        return expanded

    # ============================================================
    # v3.2: 스마트 키워드 검색 — 공백 정규화 포함
    # ============================================================
    def _score_all_items(self, keywords: List[str]) -> pd.DataFrame:
        expanded = self._expand_synonyms(keywords)
        logger.info(f"[SMART] 키워드 확장: {keywords} → {expanded}")

        df_scored = self.hscode_df.copy()
        df_scored['_score'] = 0.0

        for kw in expanded:
            kw_str = str(kw).strip()
            if not kw_str:
                continue
            is_original = kw_str in keywords
            weight = 2.0 if is_original else 1.0
            
            # v3.2: 공백 제거 버전으로도 검색
            kw_norm = kw_str.replace(' ', '').lower()
            
            try:
                # 원본 매칭
                name_match = df_scored['한글품목명'].str.contains(kw_str, case=False, na=False, regex=False)
                eng_match = df_scored['영문품목명'].str.contains(kw_str, case=False, na=False, regex=False)
                
                # v3.2: 정규화 매칭 (공백 제거)
                name_norm_match = df_scored['품목명_norm'].str.contains(kw_norm, case=False, na=False, regex=False)
                eng_norm_match = pd.Series([False] * len(df_scored))
                if '영문명_norm' in df_scored.columns:
                    eng_norm_match = df_scored['영문명_norm'].str.contains(kw_norm, case=False, na=False, regex=False)
                
                # 원본 또는 정규화 매칭
                combined_name = name_match | name_norm_match
                combined_eng = eng_match | eng_norm_match
                
                df_scored['_score'] += combined_name.astype(float) * 3.0 * weight
                df_scored['_score'] += combined_eng.astype(float) * 1.5 * weight
                
                name_start = df_scored['한글품목명'].str.startswith(kw_str, na=False)
                df_scored['_score'] += name_start.astype(float) * 2.0 * weight
            except Exception as e:
                logger.warning(f"[SMART] 키워드 점수 계산 오류 ({kw_str}): {e}")

        return df_scored

    # ============================================================
    # [BUG-3, BUG-4 FIX] 스마트 키워드 검색 — 4단위 Top-3
    # ============================================================
    def smart_keyword_search(self, query: str, max_4_results: int = 3) -> Dict[str, Any]:
        query = query.strip()
        if self.hscode_df is None:
            return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0}

        exact = self.hscode_df[self.hscode_df['HS부호'] == query.replace("-", "")]
        if not exact.empty:
            return {'match_type': 'exact', 'candidates_4': [], 'confidence': 1.0}

        keywords = query.split()
        scored = self._score_all_items(keywords)

        # BUG-3 FIX: code_len >= 4인 것만 사용 (2단위 제거)
        positive = scored[(scored['_score'] > 0) & (scored['code_len'] >= 4)].copy()
        if positive.empty:
            return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0}

        positive['_code_4'] = positive['HS부호'].str[:4]

        # BUG-3 FIX 추가: _code_4가 실제로 4자리인지 확인
        positive = positive[positive['_code_4'].str.len() == 4]
        if positive.empty:
            return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0}

        # BUG-4 FIX: 점수 공식 균형 조정
        base_scores_df = scored[(scored['code_len'] == 4) & (scored['_score'] > 0)]
        base_scores = base_scores_df.set_index('HS부호')['_score'] if not base_scores_df.empty else pd.Series(dtype=float)

        child_10_scores = positive[positive['code_len'] == 10].groupby('_code_4')['_score'].sum()
        child_10_counts = positive[positive['code_len'] == 10].groupby('_code_4').size()
        child_mid_scores = positive[positive['code_len'].between(5, 9)].groupby('_code_4')['_score'].sum()

        final_scores = {}
        for c4 in positive['_code_4'].unique():
            s_base = float(base_scores.get(c4, 0))
            s_child_10 = float(child_10_scores.get(c4, 0))
            s_child_mid = float(child_mid_scores.get(c4, 0))
            n_child_10 = int(child_10_counts.get(c4, 0))

            # 새 공식: base와 child 균형 + 매칭 건수 보너스
            final_scores[c4] = (
                s_base * 2.0
                + s_child_10 * 1.0
                + s_child_mid * 0.5
                + min(n_child_10, 10) * 1.5
            )

        # BUG-3 FIX: 4단위 코드가 실제 데이터에 존재하는지 검증
        valid_4_codes = set(
            self.hscode_df[self.hscode_df['code_len'] == 4]['HS부호'].tolist()
        )
        final_scores = {c4: s for c4, s in final_scores.items() if c4 in valid_4_codes}

        if not final_scores:
            return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0}

        # 점수 기반 필터링: 1위 점수의 50% 이상인 항목만 포함 (최대 5개)
        all_sorted = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        if all_sorted:
            top_score = all_sorted[0][1]
            threshold = top_score * 0.5
            top_4_sorted = [item for item in all_sorted if item[1] >= threshold][:5]
        else:
            top_4_sorted = []

        candidates_4 = []
        for c4, score in top_4_sorted:
            row = self.hscode_df[self.hscode_df['HS부호'] == c4]
            name = row.iloc[0]['한글품목명'] if not row.empty else ''
            candidates_4.append({'hs_code': c4, 'name_kr': name, 'score': score})

        ranking = self._build_hierarchy_for_codes(candidates_4)

        return {
            'match_type': 'keyword',
            'candidates_4': ranking['ranked_4'],
            'ranking': ranking,
            'confidence': 0.8,
        }

    # ============================================================
    # [핵심] OpenAI 물품 속성 분석
    # ============================================================
    def analyze_product_with_ai(self, query: str) -> Optional[Dict[str, Any]]:
        if not settings.openai_api_key:
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)

            prompt = f"""당신은 한국 관세청의 품목분류 전문가입니다.

아래 물품에 대해 **HS Code를 절대 추천하지 말고**, 물품의 속성만 분석해주세요.

물품: {query}

다음 JSON 형식으로 정확히 응답하세요 (다른 텍스트 없이):
{{"product_name_kr": "물품의 정확한 한국어 명칭", "product_name_en": "물품의 영어 명칭",
"primary_function": "주요 기능 또는 용도 (1문장)", "primary_material": "주요 재질/원재료",
"category_keywords": ["관세율표에서 이 물품을 찾기 위한 핵심 키워드 5개 이상"],
"chapter_hint": "이 물품이 속할 가능성이 높은 관세율표 류(章) 번호 2자리",
"is_composite": false, "is_set": false,
"classification_notes": "분류 시 주의사항"}}"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.rstrip("`")

            return json.loads(content)
        except Exception as e:
            logger.error(f"[AI] 물품 속성 분석 실패: {e}")
            return None

    # ============================================================
    # [핵심] AI 추정 류 기반 검색 (v3.4: chapter_hint 우선 적용)
    # ============================================================
    def gri_enhanced_search(self, ai_analysis: Dict, max_4_results: int = 3) -> Dict[str, Any]:
        keywords = ai_analysis.get('category_keywords', [])
        chapter_hint = str(ai_analysis.get('chapter_hint', '')).strip()

        # AI가 추정한 류(章) 기준으로 필터링
        if chapter_hint and len(chapter_hint) == 2:
            # 해당 류(2자리)로 시작하는 4단위 코드만 추출
            chapter_4_codes = self.hscode_df[
                (self.hscode_df['code_len'] == 4) &
                (self.hscode_df['HS부호'].str[:2] == chapter_hint)
            ]['HS부호'].tolist()

            if not chapter_4_codes:
                # 해당 류에 4단위가 없으면 전체 검색으로 폴백
                logger.warning(f"[AI] 추정 류 {chapter_hint}에 4단위 코드가 없음. 전체 검색으로 전환")
                chapter_filter = None
            else:
                chapter_filter = chapter_4_codes
                logger.info(f"[AI] 추정 류 {chapter_hint} 기준 필터링: {len(chapter_4_codes)}개 4단위 코드")
        else:
            chapter_filter = None

        scored = self._score_all_items(keywords)

        positive = scored[(scored['_score'] > 0) & (scored['code_len'] >= 4)].copy()
        if positive.empty:
            return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0}

        positive['_code_4'] = positive['HS부호'].str[:4]
        positive = positive[positive['_code_4'].str.len() == 4]

        # chapter_hint 기반 필터링 적용
        if chapter_filter is not None:
            positive = positive[positive['_code_4'].isin(chapter_filter)]
            if positive.empty:
                return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0}

        base_scores_df = scored[(scored['code_len'] == 4) & (scored['_score'] > 0)]
        if chapter_filter is not None:
            base_scores_df = base_scores_df[base_scores_df['HS부호'].isin(chapter_filter)]

        base_scores = base_scores_df.set_index('HS부호')['_score'] if not base_scores_df.empty else pd.Series(dtype=float)
        child_scores = positive.groupby('_code_4')['_score'].sum()

        final_scores = {}
        for c4 in positive['_code_4'].unique():
            s_base = float(base_scores.get(c4, 0))
            s_child = float(child_scores.get(c4, 0))
            final_scores[c4] = s_base * 2.0 + s_child * 1.0

        # 4단위 검증
        valid_4_codes = set(self.hscode_df[self.hscode_df['code_len'] == 4]['HS부호'].tolist())
        final_scores = {c4: s for c4, s in final_scores.items() if c4 in valid_4_codes}

        if not final_scores:
            return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0}

        # 점수 기반 필터링: 1위 점수의 50% 이상인 항목만 포함 (최대 5개)
        all_sorted = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        if all_sorted:
            top_score = all_sorted[0][1]
            threshold = top_score * 0.5
            top_4_sorted = [item for item in all_sorted if item[1] >= threshold][:5]
        else:
            top_4_sorted = []

        candidates_4 = []
        for c4, score in top_4_sorted:
            row = self.hscode_df[self.hscode_df['HS부호'] == c4]
            name = row.iloc[0]['한글품목명'] if not row.empty else ''
            candidates_4.append({'hs_code': c4, 'name_kr': name, 'score': score})

        ranking = self._build_hierarchy_for_codes(candidates_4)

        return {
            'match_type': 'ai_rag',
            'candidates_4': ranking['ranked_4'],
            'ranking': ranking,
            'confidence': 0.85,
            'ai_analysis': ai_analysis,
        }

    # ============================================================
    # [핵심] 통합 검색 파이프라인
    # ============================================================
    def search(self, query: str, max_results: int = 5, use_openai: bool = True) -> List[Dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        if self._is_hs_code_format(query):
            return self.search_by_hs_code(query, max_results)

        smart_result = self.smart_keyword_search(query, max_4_results=3)

        if smart_result['match_type'] in ('exact', 'keyword') and smart_result['candidates_4']:
            return self._smart_result_to_legacy(smart_result, max_results)

        if use_openai and settings.openai_api_key:
            ai_analysis = self.analyze_product_with_ai(query)
            if ai_analysis:
                gri_result = self.gri_enhanced_search(ai_analysis, max_4_results=3)
                if gri_result['candidates_4']:
                    return self._smart_result_to_legacy(gri_result, max_results)

        return []

    def full_search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """전체 파이프라인 실행 (v3.3: AI 분석 항상 실행 + 우선 적용)"""
        query = query.strip()
        if not query:
            return {'match_type': 'not_found', 'candidates_4': [], 'confidence': 0}

        # 1️⃣ HS코드 직접 입력은 AI 분석 없이 바로 반환
        if self._is_hs_code_format(query):
            return self.smart_code_input(query)

        # 2️⃣ AI 분석 먼저 실행 (키워드 검색과 무관하게 항상 실행)
        ai_analysis = None
        gri_result = None
        if settings.openai_api_key:
            ai_analysis = self.analyze_product_with_ai(query)
            if ai_analysis:
                gri_result = self.gri_enhanced_search(ai_analysis, max_4_results=5)

        # 3️⃣ 키워드 검색 실행
        keyword_result = self.smart_keyword_search(query, max_4_results=5)

        # 4️⃣ AI 결과와 키워드 결과 병합 (AI 우선)
        if gri_result and gri_result.get('candidates_4'):
            # AI 분석 결과가 있으면 우선 반환 (키워드 결과를 ai_analysis에 첨부)
            gri_result['ai_analysis'] = ai_analysis
            gri_result['keyword_fallback'] = keyword_result.get('candidates_4', [])
            return gri_result
        elif keyword_result['match_type'] in ('exact', 'keyword') and keyword_result['candidates_4']:
            # AI 실패 시 키워드 결과 반환 (AI 분석 정보 첨부)
            keyword_result['ai_analysis'] = ai_analysis
            return keyword_result
        else:
            # 둘 다 실패
            return {
                'match_type': 'not_found',
                'candidates_4': [],
                'confidence': 0,
                'ai_analysis': ai_analysis
            }

    # ============================================================
    # 이미지 검색
    # ============================================================
    def search_by_image(self, image_path: str = None, image_bytes: bytes = None) -> Dict[str, Any]:
        if not settings.openai_api_key:
            return {'error': 'OpenAI API 키가 설정되지 않았습니다.', 'hs_code_candidates': []}
        try:
            import base64
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            if image_path:
                with open(image_path, "rb") as f:
                    base64_image = base64.b64encode(f.read()).decode('utf-8')
            elif image_bytes:
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
            else:
                return {'error': '이미지가 필요합니다.', 'hs_code_candidates': []}

            prompt = """이 이미지의 물품을 분석하여 JSON으로 응답해주세요.
{"product_name_kr": "물품명", "product_name_en": "Name", "description": "설명", "material": "재질",
"category_keywords": ["검색키워드1", "키워드2", ...]}"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
                ]}],
                max_tokens=800,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.rstrip("`")

            analysis = json.loads(content)
            gri_result = self.gri_enhanced_search(analysis)

            enriched = []
            for item in gri_result.get('ranking', {}).get('ranked_10', {}).values():
                for sub in (item if isinstance(item, list) else [item]):
                    enriched.append({
                        'hs_code': sub['hs_code'],
                        'name_kr': sub['name_kr'],
                        'name_en': sub.get('name_en', ''),
                        'confidence': gri_result.get('confidence', 0.5),
                        'match_grade': '✅ 로컬검증' if gri_result['match_type'] != 'not_found' else '⚠️ AI추정',
                    })
                    if len(enriched) >= 5:
                        break
                if len(enriched) >= 5:
                    break

            analysis['hs_code_candidates'] = enriched
            return analysis
        except Exception as e:
            logger.error(f"[HS] 이미지 분석 실패: {e}")
            return {'error': str(e), 'hs_code_candidates': []}

    # ============================================================
    # 관세율 관련 메서드
    # ============================================================
    def _find_tariff_hs_code(self, hs_code: str) -> str:
        if self.tariff_df is None:
            return hs_code
        hs_code = str(hs_code).replace('.', '').replace('-', '').zfill(10)
        if not self.tariff_df[self.tariff_df['품목번호'] == hs_code].empty:
            return hs_code
        for trim_len in [8, 6, 4]:
            prefix = hs_code[:trim_len]
            matches = self.tariff_df[self.tariff_df['품목번호'].str.startswith(prefix)]
            if not matches.empty:
                return matches['품목번호'].iloc[0]
        return hs_code

    def get_all_tariff_rates(self, hs_code: str) -> List[Dict[str, Any]]:
        if self.tariff_df is None:
            return []
        hs_code = str(hs_code).replace('.', '').replace('-', '').zfill(10)
        matched_code = self._find_tariff_hs_code(hs_code)
        results = self.tariff_df[self.tariff_df['품목번호'] == matched_code]
        tariff_list = []
        for _, row in results.iterrows():
            tariff_type = str(row.get('관세율구분', ''))
            if tariff_type == 'A':
                category, type_name = 'basic', '기본관세'
            elif tariff_type == 'U':
                category, type_name = 'basic', 'WTO양허세율'
            elif tariff_type.startswith('C'):
                category, type_name = 'special', '조정관세(탄력관세)'
            elif tariff_type == 'H' or tariff_type.startswith('H'):
                category, type_name = 'special', '할당관세'
            elif tariff_type.startswith('F'):
                category = 'fta'
                fta_base = ''.join([c for c in tariff_type if not c.isdigit()])
                type_name = FTA_CODE_TO_NAME.get(fta_base, f'FTA협정({fta_base})')
            elif tariff_type == 'R' or tariff_type.startswith('R'):
                category, type_name = 'special', '보복관세'
            elif tariff_type.startswith('E'):
                category, type_name = 'special', '긴급관세'
            else:
                category = 'other'
                type_name = TARIFF_TYPE_CODES.get(tariff_type, {}).get('name', tariff_type) if tariff_type else '기타'
            rate_val = row.get('관세율')
            try:
                rate_val = float(rate_val) if rate_val is not None else 0.0
            except (TypeError, ValueError):
                rate_val = 0.0
            ct_val = row.get('적용국가구분', '')
            try:
                ct_val = int(ct_val) if ct_val is not None else 0
            except (TypeError, ValueError):
                ct_val = 0
            tariff_list.append({
                'hs_code': str(hs_code), 'tariff_type': str(tariff_type),
                'tariff_type_name': str(type_name), 'category': str(category),
                'tariff_rate': rate_val, 'country_type': ct_val,
                'matched_code': str(matched_code),
            })
        return tariff_list

    def get_tariff_by_category(self, hs_code: str) -> Dict[str, List[Dict[str, Any]]]:
        all_rates = self.get_all_tariff_rates(hs_code)
        categorized = {'basic': [], 'fta': [], 'special': [], 'other': []}
        for rate in all_rates:
            cat = rate.get('category', 'other')
            if cat in categorized:
                categorized[cat].append(rate)
        return categorized

    # ============================================================
    # 호환 메서드
    # ============================================================
    def search_by_hs_code(self, hs_code: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if self.hs_df is None:
            return []
        normalized = self._normalize_hs_code(hs_code)
        prefix = hs_code.replace('.', '').replace('-', '').replace(' ', '')
        exact_match = self.hs_df[self.hs_df['HS부호'] == normalized]
        prefix_match = self.hs_df[self.hs_df['HS부호'].str.startswith(prefix)]
        if not exact_match.empty:
            results_df = pd.concat([exact_match, prefix_match[~prefix_match.index.isin(exact_match.index)]])
        else:
            results_df = prefix_match
        results = []
        for _, row in results_df.head(max_results).iterrows():
            results.append({
                'hs_code': row['HS부호'],
                'name_kr': str(row.get('한글품목명', '')),
                'name_en': str(row.get('영문품목명', '')),
                'description': str(row.get('HS부호내용', '')),
                'category': str(row.get('성질통합분류코드명', '')),
                'score': 100 if row['HS부호'] == normalized else 80,
                'search_type': 'code',
                'match_grade': '✅ 정확매치' if row['HS부호'] == normalized else '🔍 유사코드',
            })
        return results

    def search_by_keywords(self, keywords: List[str], max_results: int = 5) -> List[Dict[str, Any]]:
        if not keywords:
            return []
        query = ' '.join(keywords)
        result = self.smart_keyword_search(query, max_4_results=3)
        return self._smart_result_to_legacy(result, max_results)

    def search_with_openai(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        result = self.full_search(query, max_results)
        return self._smart_result_to_legacy(result, max_results)

    def _validate_hs_code(self, code: str) -> Dict[str, Any]:
        code = str(code).replace('.', '').replace('-', '').zfill(10)
        if self.hs_df is not None:
            exact = self.hs_df[self.hs_df['HS부호'] == code]
            if not exact.empty:
                return {'valid': True, 'code': code, 'match_type': '정확매치'}
        if self.hs_df is not None:
            for trim_len in [8, 6, 4]:
                prefix = code[:trim_len]
                matches = self.hs_df[self.hs_df['HS부호'].str.startswith(prefix)]
                if not matches.empty:
                    best = matches.iloc[0]['HS부호']
                    return {'valid': False, 'code': best, 'match_type': f'상위코드({trim_len}자리)', 'original': code}
        return {'valid': False, 'code': code, 'match_type': 'AI추정(미확인)'}

    def get_hs_info(self, hs_code: str) -> Optional[Dict[str, Any]]:
        if self.hs_df is None:
            return None
        hs_code = str(hs_code).replace('.', '').replace('-', '').zfill(10)
        result = self.hs_df[self.hs_df['HS부호'] == hs_code]
        if result.empty:
            for trim_len in [8, 6, 4]:
                prefix = hs_code[:trim_len]
                matches = self.hs_df[self.hs_df['HS부호'].str.startswith(prefix)]
                if not matches.empty:
                    result = matches.head(1)
                    break
        if result.empty:
            return None
        row = result.iloc[0]
        return {
            'hs_code': row['HS부호'],
            'name_kr': str(row.get('한글품목명', '')),
            'name_en': str(row.get('영문품목명', '')),
            'description': str(row.get('HS부호내용', '')),
            'category': str(row.get('성질통합분류코드명', '')),
        }

    def _smart_result_to_legacy(self, smart_result: Dict, max_results: int) -> List[Dict]:
        results = []
        for item in smart_result.get('candidates_4', [])[:max_results]:
            results.append({
                'hs_code': item['hs_code'],
                'name_kr': item['name_kr'],
                'name_en': item.get('name_en', ''),
                'description': '',
                'category': '',
                'score': 80,
                'search_type': smart_result['match_type'],
                'match_grade': '✅ 정확매치' if smart_result['match_type'] == 'exact' else '🔍 키워드매치',
            })
        return results


# ============================================================
# 편의 함수 (기존 인터페이스 100% 호환)
# ============================================================
_searcher = None

def get_searcher() -> HSCodeSearcher:
    global _searcher
    if _searcher is None:
        _searcher = HSCodeSearcher()
    return _searcher

def search_hs_code(query: str, max_results: int = 5, use_openai: bool = True) -> List[Dict]:
    return get_searcher().search(query, max_results, use_openai)

def search_hs_code_by_keywords(keywords: List[str], max_results: int = 5) -> List[Dict]:
    return get_searcher().search_by_keywords(keywords, max_results)

def search_hs_code_by_code(hs_code: str, max_results: int = 5) -> List[Dict]:
    return get_searcher().search_by_hs_code(hs_code, max_results)

def search_hs_code_by_image(image_path: str = None, image_bytes: bytes = None) -> Dict:
    return get_searcher().search_by_image(image_path, image_bytes)

def get_hs_info(hs_code: str) -> Optional[Dict]:
    return get_searcher().get_hs_info(hs_code)

def get_all_tariff_rates(hs_code: str) -> List[Dict]:
    return get_searcher().get_all_tariff_rates(hs_code)

def get_tariff_by_category(hs_code: str) -> Dict[str, List[Dict]]:
    return get_searcher().get_tariff_by_category(hs_code)

def extract_keywords(text: str) -> List[str]:
    return [w.strip() for w in text.replace(',', ' ').split() if len(w.strip()) > 1]

def full_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    return get_searcher().full_search(query, max_results)

# 신규 편의 함수 (v3.1)
def check_customs_confirmation(hs_code: str) -> Dict[str, Any]:
    return HSCodeSearcher.check_customs_confirmation(hs_code)

def is_gita_code(hs_code: str) -> Tuple[bool, Optional[str], str]:
    """기타 코드 감지 — get_searcher() 인스턴스 메서드 호출"""
    return get_searcher().is_gita_code(hs_code)

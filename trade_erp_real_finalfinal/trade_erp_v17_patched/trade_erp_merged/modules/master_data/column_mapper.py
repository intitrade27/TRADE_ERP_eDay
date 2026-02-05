# -*- coding: utf-8 -*-
"""
OpenAI 기반 컬럼 매핑 모듈
- 기존 63개 컬럼 → 신규 39개 컬럼 자동 매핑
- GPT-4를 사용한 지능형 매핑 생성
- JSON 캐싱으로 API 비용 절감
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import OpenAI

logger = logging.getLogger(__name__)


class ColumnMapper:
    """
    OpenAI API를 사용하여 컬럼 구조 자동 매핑
    """

    def __init__(self, api_key: str, cache_dir: Path = None):
        """
        Args:
            api_key: OpenAI API 키
            cache_dir: 매핑 캐시 파일 저장 경로 (기본: data/processed)
        """
        self.client = OpenAI(api_key=api_key)

        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "data" / "processed"

        cache_dir.mkdir(parents=True, exist_ok=True)
        self.mapping_cache_file = cache_dir / "column_mapping.json"

        self._mapping: Optional[Dict] = None
        self._load_cache()

    @staticmethod
    def normalize_column_name(col_name: str) -> str:
        """
        컬럼명 정규화 (Excel에서 읽은 멀티라인 텍스트 처리)

        Args:
            col_name: 원본 컬럼명 (예: "거래ID\n(trade_id)")

        Returns:
            정규화된 컬럼명 (예: "거래ID")
        """
        if not col_name:
            return col_name

        # 개행 문자로 split하여 첫번째 라인만 사용
        lines = str(col_name).split('\n')
        return lines[0].strip() if lines else col_name

    def _load_cache(self):
        """캐시 파일에서 매핑 로드"""
        if self.mapping_cache_file.exists():
            try:
                with open(self.mapping_cache_file, 'r', encoding='utf-8') as f:
                    self._mapping = json.load(f)
                    logger.info(f"[MAPPER] 캐시 로드 완료: {len(self._mapping.get('mappings', []))}개 매핑")
            except Exception as e:
                logger.warning(f"[MAPPER] 캐시 로드 실패: {e}")
                self._mapping = None

    def _save_cache(self):
        """매핑을 캐시 파일에 저장"""
        try:
            with open(self.mapping_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._mapping, f, ensure_ascii=False, indent=2)
            logger.info(f"[MAPPER] 캐시 저장 완료: {self.mapping_cache_file}")
        except Exception as e:
            logger.error(f"[MAPPER] 캐시 저장 실패: {e}")

    def generate_mapping(
        self,
        old_columns: List[str],
        new_columns: List[str],
        force_regenerate: bool = False
    ) -> Dict:
        """
        GPT-4를 사용하여 컬럼 매핑 생성

        Args:
            old_columns: 기존 컬럼 목록 (63개)
            new_columns: 신규 컬럼 목록 (39개)
            force_regenerate: True시 캐시 무시하고 재생성

        Returns:
            {
                "mappings": [
                    {
                        "old": "trade_id",
                        "new": "거래ID",
                        "transform": null,
                        "description": "거래 고유 ID"
                    },
                    {
                        "old": "item_name",
                        "new": "물품명",
                        "transform": null,
                        "description": "물품명"
                    },
                    {
                        "old": null,
                        "new": "라인",
                        "default": 1,
                        "description": "품목 라인 번호 (기본값 1)"
                    },
                    ...
                ],
                "unmapped_old": ["documents_uploaded", "documents_generated", ...],
                "unmapped_new": ["source_module", ...]
            }
        """
        # 캐시가 있고 재생성 불필요하면 캐시 사용
        if self._mapping and not force_regenerate:
            logger.info("[MAPPER] 기존 캐시 사용")
            return self._mapping

        logger.info("[MAPPER] OpenAI API로 매핑 생성 시작...")

        # GPT-4 프롬프트 작성
        system_prompt = """당신은 데이터베이스 스키마 매핑 전문가입니다.
두 개의 컬럼 구조를 비교하여 최적의 매핑을 생성해주세요.

매핑 규칙:
1. 의미가 유사한 컬럼끼리 매핑 (예: trade_id → 거래ID)
2. 매핑되지 않는 신규 컬럼은 default 값 설정 (예: 라인 → 1)
3. 여러 컬럼을 조합해야 하는 경우 transform 함수 지정
4. 날짜 형식 변환이 필요한 경우 명시

응답 형식은 반드시 다음 JSON 구조를 따라주세요:
{
    "mappings": [
        {
            "old": "기존_컬럼명_또는_null",
            "new": "신규_컬럼명",
            "transform": "변환_함수명_또는_null",
            "default": "기본값_또는_null",
            "description": "매핑_설명"
        }
    ]
}"""

        user_prompt = f"""다음 두 컬럼 구조를 매핑해주세요:

**기존 컬럼 (63개)**:
{json.dumps(old_columns, ensure_ascii=False, indent=2)}

**신규 컬럼 (39개 - 무역 ERP 템플릿)**:
{json.dumps(new_columns, ensure_ascii=False, indent=2)}

신규 컬럼의 영문명 힌트:
- 거래ID (trade_id)
- 수입/수출 (direction: import/export)
- 거래일 (trade_date)
- 상태 (status)
- 라인 (item_line_no: 품목 라인 번호)
- 물품명 (item_name)
- HS (hscode)
- 원산지 (origin_country)
- 수입회사 (importer_name)
- 수출회사 (exporter_name)
- 수입국 (import_country)
- 수출국 (export_country)
- 인코텀즈 (incoterms)
- 통화 (currency)
- 단가 (unit_price)
- 수량 (quantity)
- 단위 (uom: unit of measure)
- 라인금액 (line_amount: 단가 × 수량)
- 운임 (freight)
- 보험 (insurance)
- 인보이스총액 (invoice_total)
- C/I (ci_no: Commercial Invoice 번호)
- P/L (pl_no: Packing List 번호)
- B/L (bl_no: Bill of Lading 번호)
- POL (loading_port: Port of Loading)
- POD (discharge_port: Port of Discharge)
- 선명/항차 (vessel: 선박명)
- 선적일 (shipment_date)
- 양하일 (discharge_date)
- ETD (estimated time of departure)
- ETA (estimated time of arrival)
- G.W. (gross_weight: 총중량)
- N.W. (net_weight: 순중량)
- 세관신고번호 (customs_decl_no)
- FTA (fta_applicable: FTA 적용 여부)
- 출처 (source_module: 데이터 출처 모듈)
- 서류유형 (source_doc_type: 원본 서류 타입)
- 생성일시 (created_at)
- 수정일시 (updated_at)

모든 신규 컬럼에 대해 매핑을 생성하고, 매핑되지 않는 기존 컬럼은 무시합니다."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            mapping_json = response.choices[0].message.content
            mapping = json.loads(mapping_json)

            # 매핑되지 않은 컬럼 추적
            mapped_old = {m['old'] for m in mapping['mappings'] if m.get('old')}
            mapped_new = {m['new'] for m in mapping['mappings']}

            unmapped_old = [col for col in old_columns if col not in mapped_old]
            unmapped_new = [col for col in new_columns if col not in mapped_new]

            mapping['unmapped_old'] = unmapped_old
            mapping['unmapped_new'] = unmapped_new

            self._mapping = mapping
            self._save_cache()

            logger.info(f"[MAPPER] 매핑 생성 완료: {len(mapping['mappings'])}개")
            logger.info(f"[MAPPER] 매핑 안된 기존 컬럼: {len(unmapped_old)}개")
            logger.info(f"[MAPPER] 매핑 안된 신규 컬럼: {len(unmapped_new)}개")

            return mapping

        except Exception as e:
            logger.error(f"[MAPPER] OpenAI API 오류: {e}")
            raise

    def apply_mapping(self, old_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        기존 데이터를 신규 컬럼 구조로 변환

        Args:
            old_data: 기존 63개 컬럼 데이터

        Returns:
            신규 39개 컬럼 데이터 (빈 값은 None)
        """
        if not self._mapping:
            raise ValueError("매핑이 생성되지 않았습니다. generate_mapping()을 먼저 호출하세요.")

        new_data = {}

        for mapping_rule in self._mapping['mappings']:
            old_col = mapping_rule.get('old')
            new_col = mapping_rule['new']
            transform = mapping_rule.get('transform')
            default = mapping_rule.get('default')

            # 1. 기본값이 있으면 사용
            if default is not None:
                new_data[new_col] = default

            # 2. 기존 컬럼에서 값 가져오기
            elif old_col and old_col in old_data:
                value = old_data[old_col]

                # 변환 함수 적용
                if transform:
                    value = self._apply_transform(transform, value, old_data)

                # 빈 값 처리 (None, 빈 문자열, NaN 등)
                if value is None or value == '' or (isinstance(value, float) and value != value):
                    new_data[new_col] = None
                else:
                    new_data[new_col] = value

            # 3. 매핑 안되면 None
            else:
                new_data[new_col] = None

        return new_data

    def _apply_transform(self, transform: str, value: Any, full_data: Dict) -> Any:
        """
        변환 함수 적용

        Args:
            transform: 변환 함수명
            value: 변환할 값
            full_data: 전체 데이터 (다른 컬럼 참조용)

        Returns:
            변환된 값
        """
        try:
            # trade_type 변환 (import → 수입, export → 수출)
            if transform == "transform_trade_type":
                if value == "import":
                    return "수입"
                elif value == "export":
                    return "수출"
                return value

            # 라인금액 계산: 수량 × 단가
            elif transform in ["calculate_line_amount", "multiply_quantity_price"]:
                quantity = float(full_data.get('quantity', 0) or 0)
                unit_price = float(full_data.get('unit_price', 0) or 0)
                return quantity * unit_price

            # 인보이스 총액 계산
            elif transform == "calculate_invoice_total":
                # 라인금액 + 운임 + 보험
                line_amount = float(full_data.get('item_value', 0) or 0)
                freight = float(full_data.get('freight', 0) or 0)
                insurance = float(full_data.get('insurance', 0) or 0)
                return line_amount + freight + insurance

            # 날짜 형식 변환 (YYYY-MM-DD HH:MM:SS → YYYY-MM-DD)
            elif transform in ["convert_date_format", "format_date"]:
                if value and isinstance(value, str):
                    return value.split()[0] if ' ' in value else value
                return value

            # FTA 적용 여부 (True/False → Y/N)
            elif transform == "boolean_to_yn":
                if value is True or value == "True" or value == 1:
                    return "Y"
                elif value is False or value == "False" or value == 0:
                    return "N"
                return value

            # 기본: 값 그대로 반환
            return value

        except Exception as e:
            logger.warning(f"[MAPPER] 변환 실패 ({transform}): {e}")
            return value

    def get_mapping_summary(self) -> str:
        """매핑 요약 정보 반환"""
        if not self._mapping:
            return "매핑이 생성되지 않았습니다."

        summary = []
        summary.append(f"=== 컬럼 매핑 요약 ===")
        summary.append(f"총 매핑: {len(self._mapping['mappings'])}개")
        summary.append(f"매핑 안된 기존 컬럼: {len(self._mapping.get('unmapped_old', []))}개")
        summary.append(f"매핑 안된 신규 컬럼: {len(self._mapping.get('unmapped_new', []))}개")
        summary.append("")

        summary.append("주요 매핑:")
        for rule in self._mapping['mappings'][:10]:
            old = rule.get('old', '(없음)')
            new = rule['new']
            desc = rule.get('description', '')
            summary.append(f"  {old} → {new}: {desc}")

        if len(self._mapping['mappings']) > 10:
            summary.append(f"  ... 외 {len(self._mapping['mappings']) - 10}개")

        return "\n".join(summary)


def create_column_mapper(api_key: str) -> ColumnMapper:
    """
    ColumnMapper 인스턴스 생성 (헬퍼 함수)

    Args:
        api_key: OpenAI API 키

    Returns:
        ColumnMapper 인스턴스
    """
    return ColumnMapper(api_key=api_key)

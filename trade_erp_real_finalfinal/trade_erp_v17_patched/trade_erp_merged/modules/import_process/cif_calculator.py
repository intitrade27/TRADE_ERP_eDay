# -*- coding: utf-8 -*-
"""
CIF 계산기 모듈 (v1.0)

Incoterms 조건별 CIF 가격 자동 계산
- FOB: 물품가 + 운임 + 보험료
- CFR: 물품가(운임포함) + 보험료  
- CIF: 그대로 사용
- EXW: 물품가 + 내륙운송비 + 운임 + 보험료
- DDP/기타: 수동 입력

Author: Trade ERP System
Date: 2026-02
"""

import streamlit as st
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Incoterms(Enum):
    """Incoterms 2020 열거형"""
    FOB = "FOB"
    CIF = "CIF"
    CFR = "CFR"
    EXW = "EXW"
    FCA = "FCA"
    CPT = "CPT"
    CIP = "CIP"
    DAP = "DAP"
    DPU = "DPU"
    DDP = "DDP"


@dataclass
class CIFCalculationResult:
    """CIF 계산 결과 데이터 클래스"""
    incoterms: str
    base_value: float          # 기본 물품가액
    freight: float             # 운임
    insurance: float           # 보험료
    inland_freight: float      # 내륙운송비 (EXW용)
    cif_value: float           # 계산된 CIF 금액
    currency: str
    calculation_note: str      # 계산 방식 설명
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'incoterms': self.incoterms,
            'base_value': self.base_value,
            'freight': self.freight,
            'insurance': self.insurance,
            'inland_freight': self.inland_freight,
            'cif_value': self.cif_value,
            'currency': self.currency,
            'calculation_note': self.calculation_note
        }


# ============================================================
# 핵심 계산 함수
# ============================================================

def calculate_cif_by_incoterms(
    incoterms: str,
    base_value: float,
    freight: float = 0.0,
    insurance: float = 0.0,
    inland_freight: float = 0.0,
    currency: str = "USD"
) -> CIFCalculationResult:
    """
    Incoterms 조건에 따른 CIF 가격 계산
    
    Parameters:
    -----------
    incoterms : str
        무역 조건 (FOB, CIF, CFR, EXW, DDP 등)
    base_value : float
        Invoice 상의 물품 금액
    freight : float
        해상/항공 운임
    insurance : float
        화물 보험료
    inland_freight : float
        내륙 운송비 (EXW 조건에서 사용)
    currency : str
        통화 코드
        
    Returns:
    --------
    CIFCalculationResult
        계산 결과 객체
    """
    inco_upper = incoterms.upper().strip()
    cif_value = base_value
    note = ""
    
    if inco_upper == "FOB":
        # FOB: 본선인도 → 운임 + 보험료 추가 필요
        cif_value = base_value + freight + insurance
        note = f"CIF = FOB({base_value:,.2f}) + 운임({freight:,.2f}) + 보험료({insurance:,.2f})"
        
    elif inco_upper == "CFR" or inco_upper == "C&F" or inco_upper == "CNF":
        # CFR: 운임포함 → 보험료만 추가
        cif_value = base_value + insurance
        note = f"CIF = CFR({base_value:,.2f}) + 보험료({insurance:,.2f})"
        
    elif inco_upper == "CIF":
        # CIF: 운임+보험 포함 → 추가 계산 불필요
        cif_value = base_value
        note = f"CIF = {base_value:,.2f} (추가 비용 없음)"
        
    elif inco_upper == "EXW":
        # EXW: 공장인도 → 모든 비용 추가
        cif_value = base_value + inland_freight + freight + insurance
        note = f"CIF = EXW({base_value:,.2f}) + 내륙운송({inland_freight:,.2f}) + 운임({freight:,.2f}) + 보험료({insurance:,.2f})"
        
    elif inco_upper in ["FCA", "CPT"]:
        # FCA/CPT: 운송인인도 → 운임 일부 + 보험료 추가
        cif_value = base_value + freight + insurance
        note = f"CIF = {inco_upper}({base_value:,.2f}) + 운임({freight:,.2f}) + 보험료({insurance:,.2f})"
        
    elif inco_upper == "CIP":
        # CIP: 운임+보험 포함 (CIF와 유사)
        cif_value = base_value
        note = f"CIF = CIP({base_value:,.2f}) (운임+보험 포함)"
        
    elif inco_upper in ["DAP", "DPU", "DDP"]:
        # DAP/DPU/DDP: 도착지 인도 → CIF 역산 필요 (수동 입력 권장)
        cif_value = base_value  # 기본값으로 설정
        note = f"{inco_upper} 조건: CIF 금액 수동 확인 필요"
        
    else:
        # 기타 조건
        cif_value = base_value
        note = f"'{incoterms}' 조건: CIF 금액 수동 입력"
    
    return CIFCalculationResult(
        incoterms=inco_upper,
        base_value=base_value,
        freight=freight,
        insurance=insurance,
        inland_freight=inland_freight,
        cif_value=cif_value,
        currency=currency,
        calculation_note=note
    )


def estimate_insurance(cif_base: float, rate: float = 0.003) -> float:
    """
    보험료 추정 (CIF 기준 0.3% 기본)
    
    실무 기준:
    - 일반 화물: 0.2% ~ 0.5%
    - 위험물/고가품: 0.5% ~ 1.0%
    - 식품/의약품: 0.4% ~ 0.8%
    """
    return round(cif_base * rate, 2)


def estimate_freight_by_route(
    origin_country: str,
    weight_kg: float = 1000,
    volume_cbm: float = 1.0,
    transport_mode: str = "sea"
) -> float:
    """
    간이 운임 추정 (참고용)
    
    실제 운임은 포워더 견적 필요
    """
    # 주요 국가별 기본 운임 (USD, 참고용)
    base_rates = {
        "CN": {"sea": 150, "air": 800},   # 중국
        "US": {"sea": 400, "air": 1500},  # 미국
        "JP": {"sea": 200, "air": 600},   # 일본
        "VN": {"sea": 180, "air": 700},   # 베트남
        "DE": {"sea": 350, "air": 1200},  # 독일
        "default": {"sea": 300, "air": 1000}
    }
    
    rates = base_rates.get(origin_country.upper(), base_rates["default"])
    base_rate = rates.get(transport_mode, rates["sea"])
    
    # 중량/부피 기준 계산 (간이)
    weight_factor = max(1, weight_kg / 1000)
    volume_factor = max(1, volume_cbm)
    
    return round(base_rate * max(weight_factor, volume_factor), 2)


# ============================================================
# Streamlit UI 컴포넌트 함수들
# ============================================================

def render_cif_input_fields(
    incoterms: str,
    base_value: float,
    currency: str = "USD",
    key_prefix: str = "cif"
) -> Tuple[float, float, float, float]:
    """
    Incoterms 조건에 따라 필요한 입력 필드만 동적으로 렌더링
    
    Returns:
    --------
    Tuple[freight, insurance, inland_freight, cif_value]
    """
    inco_upper = incoterms.upper().strip()
    freight = 0.0
    insurance = 0.0
    inland_freight = 0.0
    cif_value = base_value
    
    if inco_upper == "FOB":
        st.markdown("---")
        st.caption("🚢 **FOB 조건** → 운임(Freight) + 보험료(Insurance) 입력 필요")
        
        col1, col2 = st.columns(2)
        with col1:
            freight = st.number_input(
                f"운임 (Freight) [{currency}]",
                min_value=0.0,
                value=0.0,
                step=100.0,
                help="해상/항공 운임 (포워더 견적 참조)",
                key=f"{key_prefix}_freight"
            )
        with col2:
            insurance = st.number_input(
                f"보험료 (Insurance) [{currency}]",
                min_value=0.0,
                value=0.0,
                step=10.0,
                help="화물 보험료 (CIF의 약 0.3%)",
                key=f"{key_prefix}_insurance"
            )
        
        cif_value = base_value + freight + insurance
        st.success(f"💡 **계산된 CIF 금액: {currency} {cif_value:,.2f}** (FOB {base_value:,.2f} + F {freight:,.2f} + I {insurance:,.2f})")
        
    elif inco_upper == "CFR" or inco_upper == "C&F" or inco_upper == "CNF":
        st.markdown("---")
        st.caption("🚢 **CFR 조건** → 보험료(Insurance)만 추가 입력")
        
        insurance = st.number_input(
            f"보험료 (Insurance) [{currency}]",
            min_value=0.0,
            value=0.0,
            step=10.0,
            help="화물 보험료",
            key=f"{key_prefix}_insurance"
        )
        
        cif_value = base_value + insurance
        st.success(f"💡 **계산된 CIF 금액: {currency} {cif_value:,.2f}** (CFR {base_value:,.2f} + I {insurance:,.2f})")
        
    elif inco_upper == "CIF":
        st.success(f"💡 **CIF 조건** → 추가 계산 불필요 (CIF = {currency} {cif_value:,.2f})")
        
    elif inco_upper == "EXW":
        st.markdown("---")
        st.warning("⚠️ **EXW 조건** → 내륙운송비 + 운임 + 보험료 모두 입력 필요")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            inland_freight = st.number_input(
                f"내륙운송비 [{currency}]",
                min_value=0.0,
                value=0.0,
                step=50.0,
                help="공장 → 선적항 운송비",
                key=f"{key_prefix}_inland"
            )
        with col2:
            freight = st.number_input(
                f"해상/항공 운임 [{currency}]",
                min_value=0.0,
                value=0.0,
                step=100.0,
                key=f"{key_prefix}_freight"
            )
        with col3:
            insurance = st.number_input(
                f"보험료 [{currency}]",
                min_value=0.0,
                value=0.0,
                step=10.0,
                key=f"{key_prefix}_insurance"
            )
        
        cif_value = base_value + inland_freight + freight + insurance
        st.success(f"💡 **계산된 CIF 금액: {currency} {cif_value:,.2f}** (EXW + 내륙 + 운임 + 보험)")
        
    elif inco_upper in ["FCA", "CPT"]:
        st.markdown("---")
        st.caption(f"🚚 **{inco_upper} 조건** → 운임 + 보험료 확인 필요")
        
        col1, col2 = st.columns(2)
        with col1:
            freight = st.number_input(
                f"추가 운임 [{currency}]",
                min_value=0.0,
                value=0.0,
                step=100.0,
                key=f"{key_prefix}_freight"
            )
        with col2:
            insurance = st.number_input(
                f"보험료 [{currency}]",
                min_value=0.0,
                value=0.0,
                step=10.0,
                key=f"{key_prefix}_insurance"
            )
        
        cif_value = base_value + freight + insurance
        st.success(f"💡 **계산된 CIF 금액: {currency} {cif_value:,.2f}**")
        
    elif inco_upper in ["DAP", "DPU", "DDP"]:
        st.markdown("---")
        st.info(f"📦 **{inco_upper} 조건** → 도착지 인도 조건으로 CIF 역산 또는 수동 입력 필요")
        
        cif_value = st.number_input(
            f"CIF 금액 (수동 입력) [{currency}]",
            min_value=0.0,
            value=base_value,
            step=100.0,
            help="관세 과세가격 기준 CIF 금액을 직접 입력하세요",
            key=f"{key_prefix}_manual_cif"
        )
        st.caption("💡 DDP 조건의 경우 관세/부가세가 이미 포함되어 있을 수 있으니 확인 필요")
        
    else:
        st.markdown("---")
        st.info(f"'{incoterms}' 조건 → CIF 금액을 수동으로 입력하세요")
        
        cif_value = st.number_input(
            f"CIF 금액 (수동 입력) [{currency}]",
            min_value=0.0,
            value=base_value,
            step=100.0,
            key=f"{key_prefix}_manual_cif"
        )
    
    return freight, insurance, inland_freight, cif_value


def render_standalone_cif_calculator():
    """
    독립형 CIF 계산기 UI (Tab3용)
    
    서류 분석 없이 직접 CIF 계산 가능
    """
    st.subheader("💰 CIF 가격 계산기")
    st.info("📌 Invoice 금액과 무역조건을 입력하면 CIF(과세가격 기준)가 자동 계산됩니다.")
    
    # 기본 정보 입력
    col1, col2, col3 = st.columns(3)
    
    with col1:
        base_value = st.number_input(
            "물품가액 (Invoice 금액)",
            min_value=0.0,
            value=10000.0,
            step=100.0,
            key="calc_base_value"
        )
    
    with col2:
        currency = st.selectbox(
            "통화",
            options=["USD", "EUR", "JPY", "CNY", "GBP"],
            key="calc_currency"
        )
    
    with col3:
        incoterms = st.selectbox(
            "인도조건 (Incoterms)",
            options=["FOB", "CIF", "CFR", "EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP"],
            key="calc_incoterms"
        )
    
    # 조건별 입력 필드 렌더링
    freight, insurance, inland_freight, cif_value = render_cif_input_fields(
        incoterms=incoterms,
        base_value=base_value,
        currency=currency,
        key_prefix="calc"
    )
    
    st.divider()
    
    # 과세가격 계산 (환율 적용)
    st.subheader("📊 과세가격 계산 (KRW)")
    
    col_ex1, col_ex2 = st.columns(2)
    
    with col_ex1:
        # 환율 입력
        default_rates = {"USD": 1450.0, "EUR": 1550.0, "JPY": 9.5, "CNY": 200.0, "GBP": 1800.0}
        exchange_rate = st.number_input(
            f"{currency}/KRW 환율",
            min_value=0.0,
            value=default_rates.get(currency, 1300.0),
            step=1.0,
            key="calc_exchange_rate"
        )
    
    with col_ex2:
        tariff_rate = st.number_input(
            "관세율 (%)",
            min_value=0.0,
            max_value=100.0,
            value=8.0,
            step=0.1,
            key="calc_tariff_rate"
        )
    
    # 최종 계산
    if st.button("🧮 과세가격 계산", type="primary", key="calc_btn"):
        cif_krw = cif_value * exchange_rate
        tariff_amount = cif_krw * (tariff_rate / 100)
        vat_base = cif_krw + tariff_amount
        vat_amount = vat_base * 0.10  # 부가세 10%
        total_tax = tariff_amount + vat_amount
        total_payment = cif_krw + total_tax
        
        st.divider()
        
        # 결과 표시
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            st.markdown("##### 📋 CIF 계산 내역")
            st.write(f"**물품가액:** {currency} {base_value:,.2f}")
            if freight > 0:
                st.write(f"**운임:** {currency} {freight:,.2f}")
            if insurance > 0:
                st.write(f"**보험료:** {currency} {insurance:,.2f}")
            if inland_freight > 0:
                st.write(f"**내륙운송비:** {currency} {inland_freight:,.2f}")
            st.write(f"**CIF 합계:** {currency} {cif_value:,.2f}")
        
        with col_r2:
            st.markdown("##### 💵 과세가격 (원화)")
            st.metric("CIF (KRW)", f"₩{cif_krw:,.0f}")
            st.write(f"**관세 ({tariff_rate}%):** ₩{tariff_amount:,.0f}")
            st.write(f"**부가세 (10%):** ₩{vat_amount:,.0f}")
            st.divider()
            st.metric("총 납부세액", f"₩{total_tax:,.0f}")
            st.metric("총 수입비용", f"₩{total_payment:,.0f}", help="CIF + 관세 + 부가세")
        
        # 계산 결과 저장 (session_state)
        st.session_state['last_cif_calculation'] = {
            'incoterms': incoterms,
            'base_value': base_value,
            'freight': freight,
            'insurance': insurance,
            'inland_freight': inland_freight,
            'cif_foreign': cif_value,
            'currency': currency,
            'exchange_rate': exchange_rate,
            'cif_krw': cif_krw,
            'tariff_rate': tariff_rate,
            'tariff_amount': tariff_amount,
            'vat_amount': vat_amount,
            'total_tax': total_tax,
            'total_payment': total_payment
        }
        
        st.success("✅ 계산 완료! 이 결과를 수입 등록에 활용할 수 있습니다.")


# ============================================================
# 유틸리티 함수
# ============================================================

def get_incoterms_description(incoterms: str) -> str:
    """Incoterms 설명 반환"""
    descriptions = {
        "FOB": "본선인도 (Free On Board) - 수출항에서 본선 선적 시 위험 이전",
        "CIF": "운임보험료포함 (Cost, Insurance & Freight) - 수입항까지 운임+보험 포함",
        "CFR": "운임포함 (Cost & Freight) - 수입항까지 운임 포함, 보험 별도",
        "EXW": "공장인도 (Ex Works) - 판매자 공장에서 인도, 모든 비용 구매자 부담",
        "FCA": "운송인인도 (Free Carrier) - 지정 장소에서 운송인에게 인도",
        "CPT": "운송비지급 (Carriage Paid To) - 지정 목적지까지 운송비 지급",
        "CIP": "운송비보험료지급 (Carriage & Insurance Paid) - 운송비+보험료 지급",
        "DAP": "도착장소인도 (Delivered at Place) - 목적지 도착 시 인도",
        "DPU": "도착지양하인도 (Delivered at Place Unloaded) - 양하 완료 후 인도",
        "DDP": "관세지급인도 (Delivered Duty Paid) - 관세 포함 목적지 인도"
    }
    return descriptions.get(incoterms.upper(), f"{incoterms} 조건")


def validate_cif_inputs(
    incoterms: str,
    base_value: float,
    freight: float = 0,
    insurance: float = 0
) -> Tuple[bool, str]:
    """CIF 입력값 유효성 검증"""
    
    if base_value <= 0:
        return False, "물품가액은 0보다 커야 합니다."
    
    inco_upper = incoterms.upper()
    
    if inco_upper == "FOB":
        if freight <= 0:
            return False, "FOB 조건에서는 운임 입력이 필요합니다."
        if insurance <= 0:
            # 보험료는 경고만 (필수 아님)
            logger.warning("FOB 조건에서 보험료가 0입니다. 확인 필요.")
    
    elif inco_upper == "CFR":
        if insurance <= 0:
            logger.warning("CFR 조건에서 보험료가 0입니다. 확인 필요.")
    
    return True, "OK"


__all__ = [
    'Incoterms',
    'CIFCalculationResult',
    'calculate_cif_by_incoterms',
    'estimate_insurance',
    'estimate_freight_by_route',
    'render_cif_input_fields',
    'render_standalone_cif_calculator',
    'get_incoterms_description',
    'validate_cif_inputs'
]

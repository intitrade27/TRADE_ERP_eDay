# -*- coding: utf-8 -*-
"""
상수 정의 모듈 (v3.0 — 세관장확인품목 상세 확장)
- FTA 협정 코드
- 관세율 구분
- 인코텀즈
- 품목군별 기본 마진율
- 세관장확인품목 상세 (4자리 레벨 + 필요서류)
"""

# ============================================================
# FTA 협정 코드 매핑
# ============================================================
FTA_AGREEMENTS = {
    "FCL": {"name": "한-칠레 FTA", "countries": ["CL"], "effective_date": "2004-04-01"},
    "FSG": {"name": "한-싱가포르 FTA", "countries": ["SG"], "effective_date": "2006-03-02"},
    "FEF": {"name": "한-EFTA FTA", "countries": ["CH", "NO", "IS", "LI"], "effective_date": "2006-09-01"},
    "FAS": {"name": "한-아세안 FTA", "countries": ["BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN"], "effective_date": "2007-06-01"},
    "FIN": {"name": "한-인도 CEPA", "countries": ["IN"], "effective_date": "2010-01-01"},
    "FEU": {"name": "한-EU FTA", "countries": ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"], "effective_date": "2011-07-01"},
    "FPE": {"name": "한-페루 FTA", "countries": ["PE"], "effective_date": "2011-08-01"},
    "FUS": {"name": "한-미국 FTA", "countries": ["US"], "effective_date": "2012-03-15"},
    "FTR": {"name": "한-터키 FTA", "countries": ["TR"], "effective_date": "2013-05-01"},
    "FAU": {"name": "한-호주 FTA", "countries": ["AU"], "effective_date": "2014-12-12"},
    "FCA": {"name": "한-캐나다 FTA", "countries": ["CA"], "effective_date": "2015-01-01"},
    "FCN": {"name": "한-중국 FTA", "countries": ["CN"], "effective_date": "2015-12-20"},
    "FNZ": {"name": "한-뉴질랜드 FTA", "countries": ["NZ"], "effective_date": "2015-12-20"},
    "FVN": {"name": "한-베트남 FTA", "countries": ["VN"], "effective_date": "2015-12-20"},
    "FCO": {"name": "한-콜롬비아 FTA", "countries": ["CO"], "effective_date": "2016-07-15"},
    "FCE": {"name": "한-중미 FTA", "countries": ["CR", "SV", "HN", "NI", "PA"], "effective_date": "2019-10-01"},
    "FGB": {"name": "한-영국 FTA", "countries": ["GB"], "effective_date": "2021-01-01"},
    "FRC": {"name": "RCEP", "countries": ["AU", "BN", "KH", "CN", "ID", "JP", "LA", "MY", "MM", "NZ", "PH", "SG", "TH", "VN"], "effective_date": "2022-02-01"},
    "FIL": {"name": "한-이스라엘 FTA", "countries": ["IL"], "effective_date": "2022-12-01"},
    "FKH": {"name": "한-캄보디아 FTA", "countries": ["KH"], "effective_date": "2022-12-01"},
    "FID": {"name": "한-인도네시아 CEPA", "countries": ["ID"], "effective_date": "2023-01-01"},
    "FPH": {"name": "한-필리핀 FTA", "countries": ["PH"], "effective_date": "2024-01-01"},
}

# 국가 → FTA 코드 매핑
COUNTRY_TO_FTA = {}
for fta_code, info in FTA_AGREEMENTS.items():
    for country in info["countries"]:
        if country not in COUNTRY_TO_FTA:
            COUNTRY_TO_FTA[country] = []
        COUNTRY_TO_FTA[country].append(fta_code)


# ============================================================
# 관세율 구분 코드 매핑
# ============================================================
TARIFF_TYPE_CODES = {
    "A": {"name": "기본관세", "category": "basic", "priority": 1},
    "U": {"name": "WTO양허세율", "category": "basic", "priority": 2},
    "C": {"name": "조정관세(탄력관세)", "category": "special", "priority": 3},
    "H": {"name": "할당관세", "category": "special", "priority": 4},
    "R": {"name": "보복관세", "category": "special", "priority": 5},
    "B": {"name": "잠정세율", "category": "basic", "priority": 6},
    "E": {"name": "긴급관세", "category": "special", "priority": 7},
    "S": {"name": "계절관세", "category": "special", "priority": 8},
    "Q": {"name": "상계관세", "category": "special", "priority": 9},
    "D": {"name": "덤핑방지관세", "category": "special", "priority": 10},
}
# ============================================================
# 추가 부과 관세 vs 대체 세율 관세 구분
# ============================================================
# 추가 부과 관세: 기본관세에 "더해서" 부과 → 0%면 미적용 의미
ADDITIVE_TARIFFS = {'R', 'D', 'Q', 'E', 'G', 'T'}
# R: 보복관세, D: 덤핑방지관세, Q: 상계관세
# E: 긴급관세, G: 긴급관세(세이프가드), T: 농긴급관세

# 대체 세율 관세: 기본관세 "대신" 적용 → 0%면 실제 0% 적용
SUBSTITUTIVE_TARIFFS = {'C', 'H', 'B', 'S'}
# C: 조정관세, H: 할당관세, B: 잠정세율, S: 계절관세
# FTA 협정코드 → 협정명 매핑
FTA_CODE_TO_NAME = {
    "FAS": "한-아세안 FTA",
    "FAU": "한-호주 FTA",
    "FCA": "한-캐나다 FTA",
    "FCE": "한-중미 FTA",
    "FCL": "한-칠레 FTA",
    "FCN": "한-중국 FTA",
    "FCO": "한-콜롬비아 FTA",
    "FEF": "한-EFTA FTA",
    "FEU": "한-EU FTA",
    "FGB": "한-영국 FTA",
    "FID": "한-인도네시아 CEPA",
    "FIL": "한-이스라엘 FTA",
    "FIN": "한-인도 CEPA",
    "FKH": "한-캄보디아 FTA",
    "FNZ": "한-뉴질랜드 FTA",
    "FPE": "한-페루 FTA",
    "FPH": "한-필리핀 FTA",
    "FRC": "RCEP",
    "FSG": "한-싱가포르 FTA",
    "FTR": "한-터키 FTA",
    "FUS": "한-미국 FTA",
    "FVN": "한-베트남 FTA",
}


# ============================================================
# 인코텀즈 2020 (ICC 공식)
# ============================================================
INCOTERMS_2020 = {
    "EXW": {"name_en": "Ex Works", "name_kr": "공장인도", "transport": "모든 운송", "seller_costs": [], "buyer_costs": ["내륙운송(수출)", "수출통관", "국제운송", "보험", "수입통관", "내륙운송(수입)"]},
    "FCA": {"name_en": "Free Carrier", "name_kr": "운송인인도", "transport": "모든 운송", "seller_costs": ["내륙운송(수출)", "수출통관"], "buyer_costs": ["국제운송", "보험", "수입통관", "내륙운송(수입)"]},
    "CPT": {"name_en": "Carriage Paid To", "name_kr": "운송비지급인도", "transport": "모든 운송", "seller_costs": ["내륙운송(수출)", "수출통관", "국제운송"], "buyer_costs": ["보험", "수입통관", "내륙운송(수입)"]},
    "CIP": {"name_en": "Carriage and Insurance Paid To", "name_kr": "운송비보험료지급인도", "transport": "모든 운송", "seller_costs": ["내륙운송(수출)", "수출통관", "국제운송", "보험"], "buyer_costs": ["수입통관", "내륙운송(수입)"]},
    "DAP": {"name_en": "Delivered at Place", "name_kr": "도착장소인도", "transport": "모든 운송", "seller_costs": ["내륙운송(수출)", "수출통관", "국제운송", "보험"], "buyer_costs": ["양하", "수입통관", "내륙운송(수입)"]},
    "DPU": {"name_en": "Delivered at Place Unloaded", "name_kr": "도착지양하인도", "transport": "모든 운송", "seller_costs": ["내륙운송(수출)", "수출통관", "국제운송", "보험", "양하"], "buyer_costs": ["수입통관", "내륙운송(수입)"]},
    "DDP": {"name_en": "Delivered Duty Paid", "name_kr": "관세지급인도", "transport": "모든 운송", "seller_costs": ["내륙운송(수출)", "수출통관", "국제운송", "보험", "수입통관", "관세", "내륙운송(수입)"], "buyer_costs": []},
    "FAS": {"name_en": "Free Alongside Ship", "name_kr": "선측인도", "transport": "해상운송", "seller_costs": ["내륙운송(수출)", "수출통관"], "buyer_costs": ["국제운송", "보험", "수입통관", "내륙운송(수입)"]},
    "FOB": {"name_en": "Free on Board", "name_kr": "본선인도", "transport": "해상운송", "seller_costs": ["내륙운송(수출)", "수출통관", "선적비"], "buyer_costs": ["국제운송", "보험", "수입통관", "내륙운송(수입)"]},
    "CFR": {"name_en": "Cost and Freight", "name_kr": "운임포함인도", "transport": "해상운송", "seller_costs": ["내륙운송(수출)", "수출통관", "국제운송"], "buyer_costs": ["보험", "수입통관", "내륙운송(수입)"]},
    "CIF": {"name_en": "Cost, Insurance, Freight", "name_kr": "운임보험료포함인도", "transport": "해상운송", "seller_costs": ["내륙운송(수출)", "수출통관", "국제운송", "보험"], "buyer_costs": ["수입통관", "내륙운송(수입)"]},
}

# ============================================================
# 통관 단계
# ============================================================
CLEARANCE_STAGES = {
    "arrival": {"code": "01", "name": "입항", "progress": 10},
    "unloading": {"code": "03", "name": "하선", "progress": 30},
    "warehousing": {"code": "05", "name": "반입", "progress": 50},
    "declaration": {"code": "06", "name": "수입신고", "progress": 60},
    "examination": {"code": "07", "name": "심사", "progress": 70},
    "clearance": {"code": "10", "name": "수리", "progress": 90},
    "release": {"code": "11", "name": "반출", "progress": 100},
}

# 부가세율
VAT_RATE = 0.10

# ============================================================
# 수입/수출 마진율 기본값
# ============================================================
DEFAULT_MARGIN_RATES = {
    "식품": {"min": 15, "max": 40, "default": 25},
    "의류": {"min": 30, "max": 80, "default": 50},
    "전자기기": {"min": 10, "max": 30, "default": 20},
    "화장품": {"min": 40, "max": 100, "default": 60},
    "자동차부품": {"min": 15, "max": 35, "default": 25},
    "기계류": {"min": 10, "max": 25, "default": 15},
    "화학제품": {"min": 10, "max": 30, "default": 20},
    "섬유원료": {"min": 5, "max": 15, "default": 10},
    "금속제품": {"min": 8, "max": 20, "default": 12},
    "기타": {"min": 10, "max": 50, "default": 25},
}


# ============================================================
# 세관장확인 대상 품목 상세 (v3.0)
# 
# 구조:
#   - hs_prefixes: HS코드 앞자리 리스트 (2자리 또는 4자리)
#   - agency: 확인기관
#   - law: 관련 법령
#   - documents: 필요 서류 리스트
#   - conditions: 확인 조건/비고
#   - contact: 문의처
# ============================================================
CUSTOMS_CONFIRMATION_ITEMS = {
    # ─── 식품의약품안전처 관련 ───
    "식품": {
        "hs_prefixes": [
            "02", "03", "04", "05", "07", "08", "09", "10", "11", "12",
            "15", "16", "17", "18", "19", "20", "21", "22",
            "0401", "0402", "0403", "0404", "0405", "0406",
            "0901", "0902", "1006", "1509", "1513", "1517",
            "1601", "1602", "1604", "1605", "1701", "1704",
            "1806", "1901", "1902", "1904", "1905",
            "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009",
            "2101", "2103", "2104", "2105", "2106",
            "2201", "2202",
        ],
        "agency": "식품의약품안전처",
        "law": "식품위생법, 건강기능식품에 관한 법률",
        "documents": [
            "수입식품등 수입신고서",
            "제조공정 설명서 (가공식품)",
            "검사성적서 (해당 시)",
            "영문 성분표 (원료·첨가물 명시)",
            "한글표시사항 (라벨링)",
        ],
        "conditions": "판매용 식품은 반드시 한글표시 부착 필요. 자가소비용(US$150이하)은 면제 가능.",
        "contact": "식약처 수입식품통관센터 1577-1255",
    },
    "건강기능식품": {
        "hs_prefixes": ["2106", "2936", "2937", "3003", "3004"],
        "agency": "식품의약품안전처",
        "law": "건강기능식품에 관한 법률",
        "documents": [
            "건강기능식품 수입신고서",
            "건강기능식품 기능성 인정서 (해당 시)",
            "제조증명서(GMP)",
            "성분분석표",
            "한글표시사항",
        ],
        "conditions": "건강기능식품 마크 표시 의무. 기능성 원료 사용 시 사전 인정 필요.",
        "contact": "식약처 건강기능식품정책과 043-719-2451",
    },
    "의약품": {
        "hs_prefixes": ["30", "3001", "3002", "3003", "3004", "3005", "3006"],
        "agency": "식품의약품안전처",
        "law": "약사법",
        "documents": [
            "의약품 수입품목허가서(신고서)",
            "GMP 증명서",
            "시험성적서(Lot별)",
            "원산지증명서",
            "의약품 수입업 허가증 사본",
        ],
        "conditions": "수입자는 의약품 수입업 허가 필수. 마약류 포함 시 별도 허가.",
        "contact": "식약처 의약품정책과 043-719-2611",
    },
    "의약외품": {
        "hs_prefixes": ["3307", "3401", "3808", "3824", "9018"],
        "agency": "식품의약품안전처",
        "law": "약사법",
        "documents": [
            "의약외품 수입품목신고서",
            "제조증명서",
            "시험성적서",
        ],
        "conditions": "모기퇴치제, 소독제, 생리대 등 의약외품 해당 여부 확인 필요.",
        "contact": "식약처 의약외품정책과 043-719-2781",
    },
    "화장품": {
        "hs_prefixes": [
            "33", "3301", "3302", "3303", "3304", "3305", "3306", "3307",
        ],
        "agency": "식품의약품안전처",
        "law": "화장품법",
        "documents": [
            "화장품 수입 관련 서류 (제조판매업 등록증)",
            "화장품 책임판매업 등록증",
            "제품별 안전성 자료",
            "전성분 표시 자료",
            "한글 라벨 표시사항",
        ],
        "conditions": "화장품책임판매업 등록 필수. 기능성 화장품은 심사/보고 필요.",
        "contact": "식약처 화장품정책과 043-719-3401",
    },
    "의료기기": {
        "hs_prefixes": [
            "90", "9018", "9019", "9020", "9021", "9022", "9025", "9027",
            "8419", "8479", "8543",
        ],
        "agency": "식품의약품안전처",
        "law": "의료기기법",
        "documents": [
            "의료기기 수입허가(인증/신고)서",
            "GMP 적합인정서",
            "기술문서 심사결과 통보서",
            "수입업 허가증 사본",
        ],
        "conditions": "등급(1~4등급)에 따라 신고/인증/허가 절차 상이. 1등급은 신고, 4등급은 허가.",
        "contact": "식약처 의료기기정책과 043-719-3801",
    },

    # ─── 국가기술표준원 관련 ───
    "전기용품": {
        "hs_prefixes": [
            "84", "85", "8415", "8418", "8450", "8451", "8471", "8501",
            "8502", "8504", "8508", "8509", "8510", "8516", "8528",
            "8539", "8544", "9405",
        ],
        "agency": "국가기술표준원 (KATS)",
        "law": "전기용품 및 생활용품 안전관리법",
        "documents": [
            "안전인증서 (KC인증)",
            "안전확인신고서 또는 공급자적합성확인서",
            "시험성적서 (공인시험기관)",
            "기술문서 (도면, 규격서)",
        ],
        "conditions": "안전인증(KC) 대상: 전선, 전기기기 등. 안전확인 대상: IT기기, 가전 등. 어린이제품은 별도.",
        "contact": "국가기술표준원 제품안전정책과 043-870-5441",
    },
    "생활용품": {
        "hs_prefixes": [
            "3924", "3926", "4202", "6307", "7323", "7615",
            "9401", "9403", "9404", "9503", "9504",
        ],
        "agency": "국가기술표준원 (KATS)",
        "law": "전기용품 및 생활용품 안전관리법",
        "documents": [
            "안전확인신고서 또는 공급자적합성확인서",
            "시험성적서",
        ],
        "conditions": "어린이 보호포장, 유아용 제품은 별도 기준 적용.",
        "contact": "국가기술표준원 043-870-5441",
    },

    # ─── 국립전파연구원 관련 ───
    "방송통신기자재": {
        "hs_prefixes": [
            "8517", "8518", "8519", "8521", "8525", "8526", "8527", "8528",
            "8529", "8471", "8443",
        ],
        "agency": "국립전파연구원 (RRA)",
        "law": "전파법, 방송통신기자재등의 적합성평가에 관한 고시",
        "documents": [
            "적합인증서 / 적합등록서",
            "시험성적서 (공인시험기관)",
            "기술문서 (회로도, 사양서)",
            "EMC 시험성적서 (해당 시)",
        ],
        "conditions": "무선기기: 적합인증 필수. 유선기기: 적합등록. 블루투스/WiFi 내장 기기 포함.",
        "contact": "국립전파연구원 적합성평가과 061-338-4524",
    },

    # ─── 국토교통부/자동차 관련 ───
    "자동차·자동차부품": {
        "hs_prefixes": [
            "87", "8701", "8702", "8703", "8704", "8705", "8706", "8707", "8708",
            "4011", "7007", "7009", "8301", "8409", "8483", "8511", "8512",
            "8539", "9026", "9029", "9032",
        ],
        # v3.2 추가: 8712(자전거)는 자동차가 아니므로 세관장확인 제외
        "exclude": ["8712"],
        "agency": "국토교통부 / 한국교통안전공단",
        "law": "자동차관리법, 자동차 및 자동차부품의 성능과 기준에 관한 규칙",
        "documents": [
            "자기인증서 (자동차관리법 기준)",
            "배출가스 인증서 (환경부)",
            "소음 인증서 (환경부)",
            "안전기준 적합 시험성적서",
        ],
        "conditions": "완성차: 자기인증 + 배출가스/소음 인증 필수. 부품: 해당 안전기준 적합 확인.",
        "contact": "한국교통안전공단 자동차안전연구원 031-389-6400",
    },

    # ─── 농림축산검역본부 관련 ───
    "동물·축산물": {
        "hs_prefixes": [
            "01", "02", "0201", "0202", "0203", "0204", "0205", "0206", "0207",
            "0208", "0209", "0210", "0401", "0402", "0404", "0405", "0406",
            "0504", "0505", "0506", "0507", "0510", "0511",
            "1501", "1502", "1516", "1601", "1602",
        ],
        "agency": "농림축산검역본부",
        "law": "가축전염병예방법, 축산물 위생관리법",
        "documents": [
            "수입검역증명서",
            "수출국 검역증명서 (원본)",
            "도축·가공 위생증명서",
            "축산물 영업허가증 (수입업)",
        ],
        "conditions": "구제역/AI 발생국은 수입금지. 수입 전 검역증명서 사전 확인 필수.",
        "contact": "농림축산검역본부 수입검역과 054-912-0643",
    },
    "식물": {
        "hs_prefixes": [
            "06", "07", "08", "09", "10", "12",
            "0601", "0602", "0603", "0604",
            "0701", "0702", "0703", "0801", "0802", "0803", "0804", "0805",
            "0901", "0902", "1001", "1005", "1006", "1201",
        ],
        "agency": "농림축산검역본부",
        "law": "식물방역법",
        "documents": [
            "식물검역증명서 (수출국 발급)",
            "수입식물검역신청서",
            "재배지 검사증명서 (해당 시)",
        ],
        "conditions": "병해충 위험 식물은 수입제한. 종자는 품종보호법 확인 필요.",
        "contact": "농림축산검역본부 식물검역과 054-912-0633",
    },

    # ─── 환경부 관련 ───
    "화학물질": {
        "hs_prefixes": [
            "28", "29", "32", "34", "36", "38",
            "2801", "2803", "2804", "2806", "2811", "2833",
            "2901", "2902", "2905", "2915", "2916", "2917",
            "3204", "3206", "3208", "3209", "3210",
            "3402", "3808", "3809", "3812", "3824",
        ],
        "agency": "환경부 / 국립환경과학원 / 화학물질안전원",
        "law": "화학물질관리법, 화학물질의 등록 및 평가 등에 관한 법률(화평법)",
        "documents": [
            "화학물질 사전확인 결과서",
            "유해화학물질 취급허가서 (유해물질 해당 시)",
            "물질안전보건자료(MSDS)",
            "화학물질 등록 또는 신고 확인서 (화평법, 연 1톤 이상)",
        ],
        "conditions": "유독물질, 제한/금지물질은 별도 허가/승인. 연간 1톤 이상 수입 시 화평법 등록 의무.",
        "contact": "화학물질안전원 043-830-4000",
    },

    # ─── 수산 관련 ───
    "수산물": {
        "hs_prefixes": [
            "03", "0301", "0302", "0303", "0304", "0305", "0306", "0307", "0308",
            "1604", "1605",
        ],
        "agency": "국립수산물품질관리원",
        "law": "수산물 유통의 관리 및 지원에 관한 법률, 원산지 표시에 관한 법률",
        "documents": [
            "수산물 수입신고서",
            "위생증명서 (수출국 발급)",
            "검사성적서 (해당 시)",
            "원산지 증명서",
        ],
        "conditions": "수산물 이력제 대상 품목 확인 필요. IUU(불법어업) 증명서 요구 가능.",
        "contact": "국립수산물품질관리원 044-411-6811",
    },

    # ─── 주류 관련 ───
    "주류": {
        "hs_prefixes": [
            "2203", "2204", "2205", "2206", "2207", "2208",
        ],
        "agency": "국세청",
        "law": "주세법",
        "documents": [
            "주류수입면허증",
            "수입주류 통관신고서",
            "원산지증명서",
            "한글 라벨 표시사항",
        ],
        "conditions": "주류수입업 면허 필수. 한글 라벨(용량, 도수, 원산지 등) 부착 의무.",
        "contact": "관할 세무서 주류면허 담당",
    },

    # ─── 전략물자 관련 ───
    "전략물자": {
        "hs_prefixes": [
            "8401", "8456", "8462", "8464", "8479", "8514", "8543",
            "9005", "9006", "9012", "9013", "9014", "9015", "9030", "9031",
        ],
        "agency": "산업통상자원부 / 전략물자관리원",
        "law": "대외무역법, 전략물자 수출입 통합 고시",
        "documents": [
            "전략물자 판정서 (비해당 판정 포함)",
            "수출허가서 (해당 시)",
            "최종 사용자 증명서(End-User Certificate)",
        ],
        "conditions": "WMD(대량살상무기) 관련 물품 및 이중용도 물품은 사전 판정 필수.",
        "contact": "전략물자관리원 02-6000-6400",
    },
}

# 기존 호환용 (간단 버전)
CUSTOMS_INSPECTION_CATEGORIES = {
    "식품": {"hs_prefix": ["02", "03", "04", "07", "08", "09", "10", "11", "12", "15", "16", "17", "18", "19", "20", "21", "22"], "agency": "식품의약품안전처"},
    "의약품": {"hs_prefix": ["30"], "agency": "식품의약품안전처"},
    "화장품": {"hs_prefix": ["33"], "agency": "식품의약품안전처"},
    "의료기기": {"hs_prefix": ["90"], "agency": "식품의약품안전처"},
    "전기용품": {"hs_prefix": ["84", "85"], "agency": "국가기술표준원"},
    "통신기기": {"hs_prefix": ["85"], "agency": "국립전파연구원"},
    "자동차부품": {"hs_prefix": ["87"], "agency": "국토교통부"},
    "농산물": {"hs_prefix": ["01", "02", "03", "06", "07", "08", "10", "12"], "agency": "농림축산검역본부"},
    "수산물": {"hs_prefix": ["03"], "agency": "국립수산물품질관리원"},
    "화학물질": {"hs_prefix": ["28", "29", "38"], "agency": "환경부/국립환경과학원"},
}

# 기본 마진율 (HS 코드 없을 때)
DEFAULT_MARGIN_RATE = 20


# ============================================================
# 마스터 데이터 컬럼
# ============================================================
MASTER_DATA_COLUMNS = [
    # 기본 정보
    "trade_id", "trade_type", "created_date", "updated_date", "status",
    # 물품 정보
    "item_name", "hs_code", "quantity", "unit", "unit_price", "currency",
    # 거래처 정보
    "import_country", "export_country", "import_company", "export_company",
    "import_company_address", "export_company_address",
    "import_company_tel", "export_company_tel",
    # 가격 정보
    "item_value", "freight", "insurance", "exchange_rate", "exchange_rate_date",
    "cif_value_foreign", "cif_value_krw",
    # 관세 정보
    "tariff_type", "tariff_type_name", "tariff_rate", "tariff_amount", 
    "vat_amount", "total_tax",
    "fta_applied", "fta_agreement",
    # 마진 정보
    "base_margin_rate", "applied_margin_rate", "margin_amount",
    "cost_price", "selling_price_krw", "selling_price_foreign",
    # 환급 정보
    "refund_eligible", "refund_type", "refund_amount", "refund_status",
    # 운송 정보
    "bl_number", "container_no", "vessel_name", "voyage_no",
    "port_of_loading", "port_of_discharge",
    "incoterms",
    # 일정 정보
    "arrival_date", "unloading_date", "warehousing_date",
    "declaration_date", "clearance_date", "release_date",
    "loading_deadline", "container_return_deadline", "free_time_days",
    # 서류 정보
    "documents_uploaded", "documents_generated",
    # 비고
    "notes",
]


# ============================================================
# 수출 적재 기한 (법적 기한: 수출신고 수리일 + 30일)
# ============================================================
EXPORT_LOADING_DEADLINE_DAYS = 30

# ============================================================
# 알림 기준일 (D-7, D-3)
# ============================================================
ALERT_DAYS = [7, 3, 1]


# ============================================================
# 수출입 필요 서류 목록
# ============================================================
IMPORT_DOCUMENTS = {
    "required": [
        {"code": "ID01", "name": "수입신고서", "name_en": "Import Declaration", "auto_generate": True},
        {"code": "ID02", "name": "상업송장", "name_en": "Commercial Invoice", "auto_generate": True},
        {"code": "ID03", "name": "포장명세서", "name_en": "Packing List", "auto_generate": True},
        {"code": "ID04", "name": "선하증권", "name_en": "Bill of Lading (B/L)", "auto_generate": True},
    ],
    "conditional": [
        {"code": "ID05", "name": "원산지증명서", "name_en": "Certificate of Origin (C/O)", "condition": "FTA 적용 시", "auto_generate": True},
        {"code": "ID06", "name": "검역증명서", "name_en": "Quarantine Certificate", "condition": "농산물/축산물", "auto_generate": False},
        {"code": "ID07", "name": "식품등 수입신고서", "name_en": "Food Import Declaration", "condition": "식품류", "auto_generate": True},
        {"code": "ID08", "name": "KC인증서", "name_en": "KC Certification", "condition": "전기용품/생활용품", "auto_generate": False},
        {"code": "ID09", "name": "전파인증서", "name_en": "Radio Equipment Certification", "condition": "무선기기", "auto_generate": False},
        {"code": "ID10", "name": "위생증명서", "name_en": "Sanitary Certificate", "condition": "의료기기/화장품", "auto_generate": False},
    ],
}

EXPORT_DOCUMENTS = {
    "required": [
        {"code": "ED01", "name": "수출신고서", "name_en": "Export Declaration", "auto_generate": True},
        {"code": "ED02", "name": "상업송장", "name_en": "Commercial Invoice", "auto_generate": True},
        {"code": "ED03", "name": "포장명세서", "name_en": "Packing List", "auto_generate": True},
    ],
    "conditional": [
        {"code": "ED04", "name": "원산지증명서", "name_en": "Certificate of Origin (C/O)", "condition": "FTA 적용 시", "auto_generate": True},
        {"code": "ED05", "name": "수출면장", "name_en": "Export License", "condition": "통관 후 발급", "auto_generate": False},
        {"code": "ED06", "name": "검역증명서", "name_en": "Phytosanitary Certificate", "condition": "농산물", "auto_generate": False},
        {"code": "ED07", "name": "수출승인서", "name_en": "Export Approval", "condition": "전략물자", "auto_generate": False},
        {"code": "ED08", "name": "선적요청서", "name_en": "Shipping Request", "condition": "선적 시", "auto_generate": True},
    ],
}

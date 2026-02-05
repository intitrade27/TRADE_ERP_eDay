# 💼 자동 eDay - 무역 ERP 시스템

**Trade ERP (자동 eDay)** 는 수출입 무역업무를 자동화하고 통합 관리하는 웹 기반 ERP 시스템입니다.

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [주요 기능](#주요-기능)
3. [시스템 요구사항](#시스템-요구사항)
4. [설치 방법](#설치-방법)
5. [환경 설정](#환경-설정)
6. [실행 방법](#실행-방법)
7. [사용 가이드](#사용-가이드)
8. [프로젝트 구조](#프로젝트-구조)
9. [API 연동](#api-연동)
10. [문제 해결](#문제-해결)

---

## 🎯 프로젝트 개요

### 목표

무역업 실무에서 발생하는 반복적이고 복잡한 업무를 자동화하여 업무 효율성을 극대화합니다.

- **HS Code 검색 자동화**: AI 기반 품목 분류 및 관세율 조회
- **서류 자동 생성**: Commercial Invoice, Packing List, 수입신고서 등 무역서류 자동 생성
- **마감일 관리**: 수출 적재 마감일, 컨테이너 반납 기한 자동 추적 및 알림
- **거래 통합 관리**: 수입/수출 거래 이력 통합 관리 및 분석
- **실시간 환율**: 주요 통화 환율 조회 및 추이 분석

### 대상 사용자

- 무역회사 실무자
- 관세사 사무소
- 포워딩 업체
- 수출입 담당자

---

## ⚡ 주요 기능

### 1. 대시보드
- 거래 현황 요약 (총 거래, 수입, 수출 건수)
- 실시간 환율 정보 (USD, JPY, CNY, EUR, GBP)
- 환율 추이 차트 (1개월/1년/5년/10년)
- 간편 환율 계산기

### 2. HS Code 검색
- **스마트 검색**: 키워드, 코드, 이미지 기반 검색
- **AI 지원**: OpenAI 기반 품목 분류 추천
- **단계별 탐색**: 4단위 → 6단위 → 8단위 → 10단위 계층 구조
- **관세율 조회**: 기본관세, FTA 협정세율, 특혜세율 비교
- **세관장확인품목**: 특별 확인 대상 품목 자동 안내
- **간이세액환급**: 환급 대상 여부 및 환급율 조회

### 3. 수입 관리
- **문서 자동 인식**: Invoice/B/L 이미지에서 데이터 자동 추출 (GPT-4 Vision)
- **CIF 가격 계산**: FOB → CIF 자동 변환
- **관세/부가세 계산**: HS Code 기반 세액 자동 계산
- **마감일 자동 설정**: 컨테이너 반납 기한 (ETA + Free Time)

### 4. 수출 관리
- **적재 마감일 관리**: 수리일 + 30일 자동 계산
- **수출 단가 산정**: 마진율 기반 견적 지원
- **FTA 원산지 확인**: 협정별 원산지 결정기준 안내

### 5. 서류 생성
- **Commercial Invoice**: 상공회의소 양식 자동 생성
- **Packing List**: 포장 명세서 자동 생성
- **수입신고서**: 관세청 양식 Word 문서 생성
- **B/L Draft**: 선하증권 초안 생성

### 6. 캘린더
- **Google Calendar 연동**: 마감일 자동 등록
- **D-Day 알림**: D-7, D-3, D-1 시점 알림 발송
- **이메일 알림**: SMTP 기반 알림 발송

### 7. 거래 목록
- 전체 거래 이력 조회 및 검색
- 상태별 필터링 (진행중/완료/중요)
- 거래 상세 정보 편집

---

## 💻 시스템 요구사항

### 필수 요구사항

| 항목 | 요구사항 |
|------|----------|
| Python | 3.10 이상 |
| 메모리 | 4GB 이상 권장 |
| 디스크 | 500MB 이상 |
| 브라우저 | Chrome, Edge, Safari 최신 버전 |

### 권장 환경

- Python 3.10 ~ 3.12
- Windows 10/11, macOS, Linux
- 인터넷 연결 (API 호출용)

---

## 📦 설치 방법

### Step 1: 프로젝트 다운로드

```bash
# 프로젝트 폴더로 이동
cd trade_erp_merged
```

### Step 2: 가상환경 생성 (권장)

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Step 3: 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 설치되는 주요 패키지

| 패키지 | 용도 |
|--------|------|
| streamlit | 웹 UI 프레임워크 |
| pandas | 데이터 처리 |
| openpyxl | Excel 파일 처리 |
| openai | AI 기능 (GPT-4, 임베딩) |
| google-api-python-client | Google Calendar 연동 |
| plotly | 차트 시각화 |
| python-docx | Word 문서 생성 |
| python-dotenv | 환경변수 관리 |
| Pillow | 이미지 처리 |

### Step 4: 추가 패키지 설치 (선택)

```bash
# 환율 데이터 조회 (yfinance)
pip install yfinance

# 파일 모니터링 (실시간 동기화)
pip install watchdog
```

---

## ⚙️ 환경 설정

### Step 1: 환경변수 파일 생성

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env
```

### Step 2: API 키 설정

`.env` 파일을 열어 아래 항목을 설정합니다:

```env
# ===== 필수 설정 =====

# OpenAI API (이미지 분석, AI 검색)
OPENAI_API_KEY=sk-your-openai-api-key

# ===== 권장 설정 =====

# 관세청 Unipass API
UNIPASS_HS_CODE_API_KEY=your-key
UNIPASS_TARIFF_API_KEY=your-key
UNIPASS_CUSTOMS_CHECK_API_KEY=your-key

# 수출입은행 환율 API
EXIM_API_KEY=your-key

# ===== 선택 설정 =====

# Google Calendar 연동
GOOGLE_CALENDAR_ID=primary

# 이메일 알림 (Gmail 예시)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_RECIPIENT_EMAIL=recipient@email.com

# 앱 설정
APP_SECRET_KEY=your-secret-key
DEBUG_MODE=False
```

### Step 3: Google Calendar 연동 (선택)

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Calendar API 활성화
3. OAuth 2.0 클라이언트 ID 생성
4. `credentials.json` 파일 다운로드
5. 프로젝트 루트에 `credentials.json` 배치
6. 최초 실행 시 브라우저에서 권한 승인 → `token.json` 자동 생성

### API 키 발급 안내

| API | 발급처 | 용도 |
|-----|--------|------|
| OpenAI | [platform.openai.com](https://platform.openai.com/) | 이미지 분석, HS Code 추천 |
| 관세청 Unipass | [unipass.customs.go.kr](https://unipass.customs.go.kr/) | HS Code, 관세율 조회 |
| 수출입은행 | [koreaexim.go.kr](https://www.koreaexim.go.kr/) | 공식 환율 조회 |
| Google Calendar | [console.cloud.google.com](https://console.cloud.google.com/) | 일정 관리 |

---

## 🚀 실행 방법

### 기본 실행

```bash
streamlit run app_final_15.py
```

### 실행 옵션

```bash
# 포트 지정
streamlit run app_final_15.py --server.port 8080

# 외부 접속 허용
streamlit run app_final_15.py --server.address 0.0.0.0

# 자동 새로고침 비활성화
streamlit run app_final_15.py --server.runOnSave false
```

### 접속

브라우저에서 아래 주소로 접속:

```
http://localhost:8501
```

### 기본 로그인 정보

| 항목 | 값 |
|------|-----|
| 아이디 | `admin` |
| 비밀번호 | `admin123` |

⚠️ **보안 주의**: 실제 운영 시 반드시 비밀번호를 변경하세요.

---

## 📖 사용 가이드

### 1. 로그인

1. 브라우저에서 `http://localhost:8501` 접속
2. 아이디/비밀번호 입력 후 로그인

### 2. 대시보드 사용

로그인 후 자동으로 대시보드가 표시됩니다:
- 상단: 거래 현황 요약 (총 거래, 수입, 수출 건수)
- 중단: 실시간 환율 정보 및 변동폭
- 하단: 환율 추이 차트

### 3. HS Code 검색

1. 좌측 메뉴에서 **"HS Code 검색"** 클릭
2. 검색 방법 선택:
   - **키워드 검색**: 품목명 입력 (예: "노트북", "커피")
   - **코드 검색**: HS Code 직접 입력 (예: "8471.30")
   - **이미지 검색**: 제품 이미지 업로드 → AI 자동 분류
3. 검색 결과에서 4단위 → 6단위 → 10단위 순으로 선택
4. 관세율 및 세관장확인 정보 확인

### 4. 수입 거래 등록

1. 좌측 메뉴에서 **"수입 관리"** 클릭
2. **자동 입력** (권장):
   - Invoice 또는 B/L 이미지 업로드
   - AI가 자동으로 데이터 추출
   - 추출된 데이터 확인 및 수정
3. **수동 입력**:
   - 품목명, HS Code, 금액 등 직접 입력
4. 원산지 국가 선택 → FTA 세율 자동 적용
5. **"등록"** 버튼 클릭 → 캘린더 자동 연동

### 5. 수출 거래 등록

1. 좌측 메뉴에서 **"수출 관리"** 클릭
2. 품목 정보 및 거래처 정보 입력
3. 수리일 입력 → 적재 마감일 자동 계산 (수리일 + 30일)
4. **"등록"** 버튼 클릭

### 6. 서류 생성

1. 좌측 메뉴에서 **"서류 생성"** 클릭
2. 거래 선택 (또는 새로 입력)
3. 생성할 서류 유형 선택:
   - Commercial Invoice
   - Packing List
   - 수입신고서
4. **"생성"** 버튼 클릭 → 자동 다운로드

### 7. 거래 관리

1. 좌측 메뉴에서 **"거래 목록"** 클릭
2. 필터 옵션:
   - 거래 유형: 전체/수입/수출
   - 상태: 전체/진행중/완료
   - 중요 표시 필터
3. 거래 클릭 → 상세 정보 확인/편집
4. 중요 표시, 메모 추가, 삭제 가능

---

## 📁 프로젝트 구조

```
trade_erp_merged/
│
├── app_final_15.py          # 메인 애플리케이션 (Streamlit)
├── requirements.txt         # Python 패키지 의존성
├── .env                     # 환경변수 (API 키 등)
├── .env.example             # 환경변수 예시 파일
│
├── config/                  # 설정 모듈
│   ├── settings.py          # 환경설정 관리
│   └── constants.py         # 상수 정의 (관세코드, FTA 목록 등)
│
├── api/                     # 외부 API 연동
│   ├── exchange.py          # 환율 API
│   ├── google_calendar.py   # Google Calendar API
│   ├── notifications.py     # 알림 (이메일)
│   ├── openai_vision.py     # OpenAI Vision API
│   └── unipass.py           # 관세청 Unipass API
│
├── modules/                 # 기능 모듈
│   ├── auth/                # 인증/로그인
│   │   └── login.py
│   │
│   ├── calendar/            # 캘린더/마감일 관리
│   │   └── deadline_manager.py
│   │
│   ├── documents/           # 서류 생성
│   │   └── generator.py     # CI, PL, 수입신고서 생성
│   │
│   ├── hs_code/             # HS Code 검색
│   │   ├── search.py        # 스마트 검색 엔진
│   │   └── tariff.py        # 관세율 조회
│   │
│   ├── import_process/      # 수입 업무
│   │   ├── calculator.py    # 세액 계산
│   │   └── cif_calculator.py # CIF 가격 계산
│   │
│   ├── export_process/      # 수출 업무
│   │   └── pricing.py       # 수출 단가 계산
│   │
│   ├── master_data/         # 마스터 데이터 관리
│   │   ├── cached_manager.py    # 캐시 기반 데이터 관리
│   │   ├── column_mapper.py     # 컬럼 자동 매핑
│   │   ├── excel_manager.py     # Excel 파일 처리
│   │   ├── file_watcher.py      # 파일 변경 감지
│   │   └── sync_scheduler.py    # 동기화 스케줄러
│   │
│   └── file_analyzer/       # 파일 분석
│       └── analyzer.py
│
├── data/                    # 데이터 디렉토리
│   ├── raw/                 # 원본 데이터 (HS부호, 관세율표)
│   ├── master/              # 마스터 데이터
│   ├── processed/           # 처리된 데이터
│   │   └── documents/       # 생성된 서류
│   └── uploads/             # 업로드 파일
│
├── templates/               # 서류 템플릿
│   ├── COMMERCIAL_INVOICE_template.xlsx
│   ├── PACKING_LIST_template.xlsx
│   └── 수입신고서_template.docx
│
├── font/                    # 커스텀 폰트
│   └── atoz_*.ttf
│
├── logs/                    # 로그 파일
│   └── app.log
│
├── credentials.json         # Google API 인증 (직접 배치)
└── token.json               # Google OAuth 토큰 (자동 생성)
```

---

## 🔌 API 연동

### OpenAI API

**용도**: 이미지 분석, HS Code 추천, 스마트 필드 매칭

```python
# 문서 이미지에서 데이터 자동 추출
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "분석 프롬프트"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]
    }]
)
```

### 관세청 Unipass API

**용도**: HS Code 조회, 관세율 조회, 세관장확인품목 조회

- HS Code 조회 API
- 품목번호별 관세율 API
- 세관장확인대상물품 API

### Google Calendar API

**용도**: 마감일 자동 등록, 알림 설정

```python
# 마감일 캘린더 등록
calendar.create_event(
    title="[수입] 컨테이너반납 - IMP-20260201-001",
    start_date=deadline,
    description="거래번호: IMP-20260201-001",
    reminders=[7*24*60, 3*24*60, 1*24*60]  # D-7, D-3, D-1
)
```

---

## ❓ 문제 해결

### 1. 설치 오류

**문제**: `pip install` 실패

```bash
# 해결: pip 업그레이드 후 재시도
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Streamlit 실행 오류

**문제**: `ModuleNotFoundError`

```bash
# 해결: 가상환경 활성화 확인
# Windows
venv\Scripts\activate

# 패키지 재설치
pip install -r requirements.txt
```

### 3. OpenAI API 오류

**문제**: `AuthenticationError`

```
# 해결: .env 파일의 API 키 확인
OPENAI_API_KEY=sk-your-actual-api-key
```

### 4. Google Calendar 연동 오류

**문제**: `credentials.json not found`

1. Google Cloud Console에서 OAuth 클라이언트 ID 생성
2. JSON 파일 다운로드
3. `credentials.json`으로 이름 변경
4. 프로젝트 루트에 배치

### 5. 환율 데이터 오류

**문제**: 환율 차트가 표시되지 않음

```bash
# 해결: yfinance 설치
pip install yfinance
```

### 6. 한글 깨짐

**문제**: Excel/Word 파일에서 한글 깨짐

```bash
# 해결: 폰트 파일 확인
# font/ 디렉토리에 atoz_*.ttf 파일 존재 확인
```

### 7. 로그 확인

문제 발생 시 로그 파일 확인:

```bash
# 로그 파일 위치
cat logs/app.log

# 실시간 로그 확인
tail -f logs/app.log
```

---

## 📞 지원

### 로그 파일 위치
- `logs/app.log`: 애플리케이션 로그

### 데이터 백업
- `data/master/`: 마스터 데이터
- `data/processed/documents/`: 생성된 서류

---

## 📄 라이선스

이 프로젝트는 내부 사용 목적으로 개발되었습니다.

---

## 🔄 버전 정보

- **현재 버전**: v17 (app_final_15.py)
- **최종 업데이트**: 2026년 2월

---

**Made with ❤️ for Trade Professionals**

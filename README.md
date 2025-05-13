# Auto-Trading Code Modifier

LLM 기반 자동 코드 수정 시스템을 갖춘 백엔드 서버입니다.

## 설치 방법

필요한 패키지 설치:

```bash
pip install -r requirements.txt
```

## 환경 변수 설정

`.env` 파일에 다음과 같이 API 키를 설정합니다:

```
OPENAI_API_KEY=your_openai_api_key_here
```

API 키가 없을 경우, 테스트 목적으로 모의 구현(mock)이 사용됩니다.

## 실행 방법

개발 모드로 실행:

```bash
uvicorn main:app --reload
```

## 기능

1. TradingView에서 보내는 웹훅 수신 (`/webhook`)
2. 수신된 데이터 저장 (`storage/webhooks/`)
3. LLM을 활용한 거래 전략 코드 자동 수정 (`/webhook/test-analyze`)
   - 문제점 분석 및 설명 생성
   - 수정된 Pine Script 코드 생성
   - 수정된 코드 저장 (`storage/strategies/`)

## API 엔드포인트

- `GET /`: 서버 상태 및 사용 가능한 엔드포인트 정보
- `POST /webhook`: TradingView 웹훅 수신
- `POST /webhook/test-analyze`: 테스트용 전략 코드 분석 및 수정

## 디렉토리 구조

```
project/
├── main.py              # FastAPI 메인 앱
├── webhook_router.py    # 웹훅 수신 라우터
├── pine_modifier.py     # Pine Script 코드 수정 모듈
├── prompt_template.txt  # LLM 프롬프트 템플릿
├── mock_openai.py       # 테스트용 OpenAI API 모의 구현
├── storage/             # 데이터 저장소
│   ├── webhooks/        # 웹훅 페이로드 저장 위치
│   └── strategies/      # 거래 전략 코드 저장 위치
``` 
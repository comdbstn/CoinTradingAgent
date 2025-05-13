# 자동 트레이딩 코드 수정 시스템

TradingView 웹훅을 받아 Pine Script 트레이딩 전략 코드를 자동으로 분석하고 개선하는 시스템입니다.

## 주요 기능

1. TradingView에서 알림 웹훅 수신
2. 성능 데이터 기반 Pine Script 코드 분석
3. OpenAI API를 활용한 전략 코드 자동 개선
4. 수정 내역 추적 및 관리
5. Vercel 서버리스 환경에서 실행 가능

## 설치 및 실행

### 필수 요구 사항

- Python 3.9 이상
- OpenAI API 키

### 로컬 환경에서 실행

1. 저장소 클론:
```bash
git clone [저장소 URL]
cd [프로젝트 디렉토리]
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정:
`.env` 파일 생성:
```
OPENAI_API_KEY=your-api-key-here
```

4. 서버 실행:
```bash
uvicorn main:app --reload
```

서버가 http://localhost:8000 에서 실행됩니다.

### Vercel에 배포하기

1. Vercel CLI 설치:
```bash
npm i -g vercel
```

2. 배포:
```bash
vercel
```

3. 환경 변수 설정:
Vercel 대시보드에서 프로젝트 설정 -> 환경 변수에 `OPENAI_API_KEY`를 추가합니다.

## API 엔드포인트

- `POST /webhook/`: TradingView에서 웹훅 수신
- `GET /webhook/test`: 테스트 분석 실행
- `GET /webhook/history`: 수정 내역 조회
- `GET /webhook/status`: 시스템 상태 확인
- `GET /webhook/strategy/{filename}`: 특정 전략 코드 조회
- `GET /webhook/webhook/{filename}`: 특정 웹훅 데이터 조회

## TradingView 웹훅 설정 방법

1. TradingView에서 알림 생성
2. 웹훅 URL 설정: `https://[your-vercel-app-url]/webhook/`
3. 웹훅 메시지 형식 (예시):
```json
{
  "strategy_name": "RSI 전략",
  "performance": {
    "profit_factor": 1.5,
    "win_rate": 60,
    "avg_profit": 2.3,
    "max_drawdown": 15
  },
  "trading_problem": "RSI 전략이 최근 상승 추세에서 수익성이 낮습니다. 과매수/과매도 기준이 현재 시장 상황에 최적화되지 않았으며, 이익실현 및 손절매 설정이 개선이 필요합니다.",
  "suggested_improvements": "RSI 과매도 기준을 28로 낮추고, 이익실현 비율을 5%에서 7%로 높이세요. 트레일링 스탑을 2%로 적용하고, 매도 신호에 볼린저 밴드 상단을 추가로 활용하여 더 정확한 매도 시점을 잡으세요."
}
```

## 디렉토리 구조

```
/
├── api/                        # Vercel 서버리스 함수
│   ├── index.py                # 메인 FastAPI 앱
│   ├── webhook_router.py       # 웹훅 처리 라우터
│   └── pine_modifier.py        # Pine Script 수정 모듈
├── static/                     # 정적 파일
│   └── index.html              # 웹 인터페이스
├── storage/                    # 저장소 디렉토리
│   ├── strategies/             # 전략 파일 저장소
│   │   ├── current.pine        # 현재 사용 중인 전략
│   │   └── example.pine        # 예제 전략
│   └── webhooks/               # 웹훅 로그 저장소
│       └── webhook_test.json   # 테스트용 웹훅 데이터
├── requirements.txt            # 파이썬 의존성
├── vercel.json                 # Vercel 배포 설정
└── README.md                   # 문서
```

## 라이센스

MIT License

## 문의 및 기여

이슈 또는 PR은 언제든지 환영합니다. 질문이나 제안이 있으시면 이슈를 등록해주세요. 
# Auto-Trading Code Modifier

TradingView에서 보낸 웹훅을 기반으로 Pine Script 거래 전략을 자동으로 분석하고 개선하는 서비스입니다.

## 기능

- TradingView 웹훅 수신 및 로깅
- GPT-4o를 활용한 거래 전략 분석 및 개선
- 전략 코드 버전 관리
- 웹 인터페이스를 통한 결과 확인

## 시작하기

### 필수 요구사항

- Python 3.8+
- OpenAI API 키

### 설치 및 실행

1. 저장소 클론
```bash
git clone https://github.com/your-username/auto-trading-code-modifier.git
cd auto-trading-code-modifier
```

2. 가상 환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. `.env` 파일 생성 및 OpenAI API 키 설정
```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

5. 서버 실행
```bash
uvicorn main:app --reload --port 8000
```

## 서버 사용 방법

### 웹훅 전송 테스트

TradingView에서 웹훅을 설정하기 전에 다음 명령으로 테스트 데이터를 보낼 수 있습니다:

```bash
curl -X POST http://localhost:8000/webhook/ \
  -H "Content-Type: application/json" \
  -d @storage/webhooks/webhook_test.json
```

### API 엔드포인트

- `POST /webhook/`: TradingView 웹훅 수신
- `GET /webhook/test`: 샘플 데이터로 분석 테스트
- `GET /webhook/history`: 수정 내역 확인
- `GET /webhook/status`: 시스템 상태 확인
- `GET /webhook/strategy/{filename}`: 특정 전략 코드 조회
- `GET /webhook/webhook/{filename}`: 특정 웹훅 데이터 조회

## TradingView 설정 방법

TradingView에서 알림을 설정하고 웹훅 URL을 다음과 같이 지정합니다:
```
http://your-server-address/webhook/
```

알림 메시지 형식은 다음과 같이 JSON 형식으로 설정해야 합니다:

```json
{
  "ticker": "{{ticker}}",
  "timestamp": "{{timenow}}",
  "strategy_name": "Advanced RSI Strategy",
  "timeframe": "{{interval}}",
  "performance": {
    "total_trades": 65,
    "profitable_trades": 24,
    "losing_trades": 41,
    "win_rate": 36.92,
    "profit_factor": 0.76,
    "max_drawdown": 12.4
  },
  "recent_trades": [
    {
      "timestamp": "{{timenow}}",
      "type": "{{strategy.order.action}}",
      "entry_price": {{strategy.order.price}},
      "exit_price": {{strategy.position_size}}
    }
  ],
  "trading_problem": "RSI 전략이 최근 상승 추세에서 수익성이 낮습니다. 과매수/과매도 기준이 현재 시장 상황에 최적화되지 않았으며, 이익실현 및 손절매 설정이 개선이 필요합니다.",
  "suggested_improvements": "RSI 과매도 기준을 낮추고, 이익실현 비율을 높이세요. 트레일링 스탑을 적용하고, 매도 신호에 볼린저 밴드를 활용하세요."
}
```

## 도커로 실행하기

1. 도커 이미지 빌드
```bash
docker build -t auto-trading-code-modifier .
```

2. 도커 컨테이너 실행
```bash
docker run -d -p 8000:8000 \
  -e OPENAI_API_KEY=your-api-key-here \
  --name trading-code-modifier \
  auto-trading-code-modifier
```

## 기여 방법

1. 이 저장소를 포크합니다
2. 새 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경 사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 브랜치를 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 라이선스

이 프로젝트는 MIT 라이선스에 따라 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요. 
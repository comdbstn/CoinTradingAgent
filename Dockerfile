FROM python:3.10-slim

WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p storage/webhooks storage/strategies static

# 샘플 파일 복사 (시작시 필요한 파일이 없을 경우를 대비)
RUN if [ ! -f storage/strategies/current.pine ]; then \
    echo '//@version=4\nstrategy("Simple RSI Strategy", overlay=true)\n\n// 입력 변수\nrsiLength = input(14, title="RSI 기간")\nrsiOverbought = input(70, title="RSI 과매수 기준")\nrsiOversold = input(33, title="RSI 과매도 기준")\ntakeProfitPct = input(5.0, title="이익 실현 %")\nstopLossPct = input(3.0, title="손절매 %")\n\n// RSI 계산\nrsiValue = rsi(close, rsiLength)\n\n// 진입 조건\nlongCondition = crossover(rsiValue, rsiOversold)\nshortCondition = crossunder(rsiValue, rsiOverbought)\n\n// 전략 실행\nif (longCondition)\n    strategy.entry("RSI_Long", strategy.long)\n\nif (shortCondition)\n    strategy.entry("RSI_Short", strategy.short)\n\n// 이익 실현 및 손절매 설정\nstrategy.exit("TP_SL_Long", "RSI_Long", profit=close*takeProfitPct/100, loss=close*stopLossPct/100)\nstrategy.exit("TP_SL_Short", "RSI_Short", profit=close*takeProfitPct/100, loss=close*stopLossPct/100)\n\n// 시각화\nplot(rsiValue, "RSI", color.blue)\nhline(rsiOverbought, "과매수 기준", color.red)\nhline(rsiOversold, "과매도 기준", color.green)' > storage/strategies/current.pine; \
fi

# 포트 설정
EXPOSE 8000

# 실행 명령
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 
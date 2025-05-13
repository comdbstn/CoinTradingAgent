"""
OpenAI API 호출을 모의로 구현하는 모듈입니다.
실제 API 키가 없을 때 테스트용으로 사용합니다.
"""

class ChatCompletion:
    @staticmethod
    def create(model, messages, temperature=0.7):
        """
        OpenAI의 ChatCompletion.create 메서드를 모의로 구현합니다.
        
        Args:
            model (str): 사용할 모델 이름
            messages (list): 대화 메시지 목록
            temperature (float): 생성 다양성 조절 파라미터
            
        Returns:
            dict: 모의 응답 객체
        """
        # 입력된 프롬프트 텍스트 추출
        prompt_text = messages[0]["content"] if messages else ""
        
        # 프롬프트에서 원본 코드와 로그 추출 (디버깅용)
        original_code_section = prompt_text.split("📄 원본 전략 코드:")[1].split("📊 최근 거래 로그:")[0].strip() if "📄 원본 전략 코드:" in prompt_text else "코드 추출 실패"
        
        # 모의 응답 생성
        mock_response = """
RSI 과매도 값이 너무 높게 설정되어 있습니다. 현재 33으로 설정된 값은 일반적인 RSI 과매도 기준(30)보다 높아서 과도한 매수 신호가 발생할 수 있습니다.

또한 이익 실현 및 손절매 설정 방식에 약간의 오류가 있습니다. 현재 코드는 백테스팅에서는 작동할 수 있지만, 실제 거래에서는 문제가 발생할 수 있습니다.

수정할 부분:
1. RSI 과매도 기준값을 33에서 30으로 낮춰 표준적인 과매도 기준을 적용합니다.
2. 이익 실현 및 손절매 계산 방식을 개선합니다.
3. 전략 파라미터에 대한 설명을 추가하여 가독성을 높입니다.

```pine
//@version=4
strategy("Simple RSI Strategy", overlay=true, pyramiding=0, default_qty_type=strategy.percent_of_equity, default_qty_value=10)

// 입력 변수
rsiLength = input(14, title="RSI 기간")
rsiOverbought = input(70, title="RSI 과매수 기준")
rsiOversold = input(30, title="RSI 과매도 기준") // 33에서 30으로 수정
takeProfitPct = input(5.0, title="이익 실현 %")
stopLossPct = input(3.0, title="손절매 %")

// RSI 계산
rsiValue = rsi(close, rsiLength)

// 진입 조건
longCondition = crossover(rsiValue, rsiOversold)
shortCondition = crossunder(rsiValue, rsiOverbought)

// 전략 실행
if (longCondition)
    strategy.entry("RSI_Long", strategy.long)

if (shortCondition)
    strategy.entry("RSI_Short", strategy.short)

// 이익 실현 및 손절매 설정 (개선된 방식)
longTakeProfitPrice = strategy.position_avg_price * (1 + takeProfitPct / 100)
longStopLossPrice = strategy.position_avg_price * (1 - stopLossPct / 100)
shortTakeProfitPrice = strategy.position_avg_price * (1 - takeProfitPct / 100)
shortStopLossPrice = strategy.position_avg_price * (1 + stopLossPct / 100)

if (strategy.position_size > 0)
    strategy.exit("TP_SL_Long", "RSI_Long", limit=longTakeProfitPrice, stop=longStopLossPrice)
else if (strategy.position_size < 0)
    strategy.exit("TP_SL_Short", "RSI_Short", limit=shortTakeProfitPrice, stop=shortStopLossPrice)

// 시각화
plot(rsiValue, "RSI", color.blue)
hline(rsiOverbought, "과매수 기준", color.red)
hline(rsiOversold, "과매도 기준", color.green)
```
"""
        
        # 모의 응답 객체 구성
        class MockChoice:
            def __init__(self, text):
                self.message = MockMessage(text)
        
        class MockMessage:
            def __init__(self, text):
                self.content = text
        
        return {
            "choices": [MockChoice(mock_response)],
            "model": model,
            "usage": {
                "prompt_tokens": len(prompt_text) // 4,  # 근사치 계산
                "completion_tokens": len(mock_response) // 4,
                "total_tokens": (len(prompt_text) + len(mock_response)) // 4
            }
        } 
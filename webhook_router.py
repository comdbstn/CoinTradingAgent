# webhook_router.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import json
from pathlib import Path
from pine_modifier import generate_modified_script, save_modified_code

router = APIRouter()

# 기본 디렉토리 설정 (main.py에서 재설정됨)
LOG_DIR = "storage/webhooks"
STRATEGY_DIR = "storage/strategies"

@router.post("/")
async def receive_webhook(request: Request):
    """
    TradingView 웹훅을 수신하고 자동으로 전략 코드를 분석 및 수정합니다.
    
    1. 웹훅 데이터 저장
    2. 원본 전략 코드 로드
    3. 자동 분석 및 수정
    4. 결과 저장 (수정된 코드, 메타 정보)
    """
    data = await request.json()
    
    # 웹훅 데이터 저장
    now = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(LOG_DIR, f"webhook_{now}.json")
    
    with open(log_path, "w") as f:
        json.dump(data, f, indent=2)
        
    # 가장 최근 웹훅 로그를 latest.json으로 복사
    latest_file = os.path.join(LOG_DIR, "latest.json")
    with open(latest_file, "w") as f:
        json.dump(data, f, indent=2)
    
    try:
        # 원본 전략 코드 로드
        strategy_path = os.path.join(STRATEGY_DIR, "current.pine")
        
        # Vercel 환경의 경우 샘플 전략 코드 생성
        if not os.path.exists(strategy_path):
            with open(strategy_path, "w") as f:
                f.write("""
//@version=4
strategy("Simple RSI Strategy", overlay=true)

// 입력 변수
rsiLength = input(14, title="RSI 기간")
rsiOverbought = input(70, title="RSI 과매수 기준")
rsiOversold = input(33, title="RSI 과매도 기준")
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

// 이익 실현 및 손절매 설정
strategy.exit("TP_SL_Long", "RSI_Long", profit=close*takeProfitPct/100, loss=close*stopLossPct/100)
strategy.exit("TP_SL_Short", "RSI_Short", profit=close*takeProfitPct/100, loss=close*stopLossPct/100)

// 시각화
plot(rsiValue, "RSI", color.blue)
hline(rsiOverbought, "과매수 기준", color.red)
hline(rsiOversold, "과매도 기준", color.green)
                """.strip())
        
        with open(strategy_path, "r") as f:
            original_code = f.read()
        
        # 자동 분석 및 수정
        result = generate_modified_script(original_code, json.dumps(data, indent=2))
        
        # 결과 저장
        modified_path = os.path.join(STRATEGY_DIR, f"modified_{now}.pine")
        with open(modified_path, "w") as f:
            f.write(result["modified_code"])
        
        # 메타 정보 저장 (웹앱 연동용)
        meta_path = os.path.join(STRATEGY_DIR, f"meta_{now}.json")
        with open(meta_path, "w") as f:
            json.dump({
                "timestamp": now,
                "reason": result["explanation"],
                "original_code_path": strategy_path,
                "modified_code_path": modified_path,
                "webhook_data_path": log_path
            }, f, indent=2)
        
        return {
            "status": "auto-analyzed", 
            "modified_file": modified_path,
            "explanation": result["explanation"]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"자동 분석 중 오류 발생: {str(e)}"}
        )

@router.post("/test-analyze")
async def test_analysis(request: Request):
    """
    테스트용 엔드포인트: 예제 전략 코드와 최근 웹훅 로그를 분석하여 수정된 코드를 생성합니다.
    """
    # 예제 전략 코드 파일이 존재하는지 확인
    example_file = os.path.join(STRATEGY_DIR, "example.pine")
    
    # Vercel 환경의 경우 샘플 전략 코드 생성
    if not os.path.exists(example_file):
        with open(example_file, "w") as f:
            f.write("""
//@version=4
strategy("Simple RSI Strategy", overlay=true)

// 입력 변수
rsiLength = input(14, title="RSI 기간")
rsiOverbought = input(70, title="RSI 과매수 기준")
rsiOversold = input(33, title="RSI 과매도 기준")
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

// 이익 실현 및 손절매 설정
strategy.exit("TP_SL_Long", "RSI_Long", profit=close*takeProfitPct/100, loss=close*stopLossPct/100)
strategy.exit("TP_SL_Short", "RSI_Short", profit=close*takeProfitPct/100, loss=close*stopLossPct/100)

// 시각화
plot(rsiValue, "RSI", color.blue)
hline(rsiOverbought, "과매수 기준", color.red)
hline(rsiOversold, "과매도 기준", color.green)
            """.strip())
    
    # 최근 웹훅 로그 파일이 존재하는지 확인
    latest_log_file = os.path.join(LOG_DIR, "latest.json")
    
    # Vercel 환경의 경우 샘플 웹훅 데이터 생성
    if not os.path.exists(latest_log_file):
        with open(latest_log_file, "w") as f:
            f.write(json.dumps({
                "strategy_name": "Simple RSI Strategy",
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "action": "buy",
                "price": 52000,
                "time": "2023-01-02T14:30:00Z",
                "rsi_value": 32.5,
                "last_trades": [
                    {"action": "buy", "price": 51800, "time": "2023-01-02T13:30:00Z", "result": "loss", "pnl": -2.3},
                    {"action": "buy", "price": 51500, "time": "2023-01-02T12:30:00Z", "result": "loss", "pnl": -1.8},
                    {"action": "buy", "price": 51200, "time": "2023-01-02T11:30:00Z", "result": "loss", "pnl": -2.0},
                    {"action": "buy", "price": 51000, "time": "2023-01-02T10:30:00Z", "result": "loss", "pnl": -2.2}
                ],
                "metrics": {
                    "win_rate": 0.20,
                    "avg_profit": 1.2,
                    "avg_loss": -2.1,
                    "max_drawdown": -8.3
                },
                "message": "RSI 기반 전략에서 지속적인 손실 발생. 과매도 기준 및 손절매 조정 필요"
            }, indent=2))
    
    # 파일 내용 읽기
    with open(example_file, "r") as f:
        original_code = f.read()
    
    with open(latest_log_file, "r") as f:
        recent_log = f.read()
    
    try:
        # LLM을 통한 코드 수정 요청
        result = generate_modified_script(original_code, recent_log)
        
        # 수정된 코드 저장
        output_file = save_modified_code(result["modified_code"])
        
        return {
            "explanation": result["explanation"],
            "file": output_file
        }
    except Exception as e:
        return {"error": f"분석 중 오류 발생: {str(e)}"}

@router.get("/history")
async def get_strategy_history():
    """
    전략 수정 히스토리를 반환합니다.
    메타 데이터 파일들을 읽어서 시간순으로 정렬된 목록을 제공합니다.
    """
    try:
        # meta_*.json 파일들을 찾아서 시간순으로 정렬
        meta_files = sorted(
            Path(STRATEGY_DIR).glob("meta_*.json"), 
            key=lambda x: x.name, 
            reverse=True
        )
        
        # 각 파일의 내용을 읽어서 목록에 추가
        result = []
        for file in meta_files:
            with open(file, "r") as f:
                meta_data = json.load(f)
                result.append(meta_data)
        
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"히스토리 조회 중 오류 발생: {str(e)}"}
        ) 
# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
from webhook_router import router as webhook_router

app = FastAPI(
    title="Auto-Trading Code Modifier",
    description="LLM 기반 자동 코드 수정 시스템을 갖춘 백엔드 서버입니다. TradingView에서 보내는 웹훅을 수신하고, Pine Script 코드를 자동으로 분석 및 개선합니다.",
    version="0.1.0",
)

# CORS 설정 추가 (Vercel 배포에 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용하는 것이 좋습니다
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 디렉토리 생성
static_dir = Path("static")
os.makedirs(static_dir, exist_ok=True)

# 스토리지 디렉토리 생성 (Vercel의 /tmp 사용)
if os.environ.get("VERCEL"):
    LOG_DIR = "/tmp/storage/webhooks"
    STRATEGY_DIR = "/tmp/storage/strategies"
else:
    LOG_DIR = "storage/webhooks"
    STRATEGY_DIR = "storage/strategies"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STRATEGY_DIR, exist_ok=True)

# 환경 변수 설정
webhook_router.LOG_DIR = LOG_DIR
webhook_router.STRATEGY_DIR = STRATEGY_DIR

# 정적 파일 제공
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    
    return {
        "message": "LLM 기반 자동 코드 수정 시스템이 실행 중입니다.",
        "endpoints": {
            "/webhook": "TradingView 웹훅 수신",
            "/webhook/test-analyze": "테스트용 전략 코드 분석 및 수정",
            "/webhook/history": "전략 수정 히스토리 조회"
        }
    }

app.include_router(webhook_router, prefix="/webhook") 
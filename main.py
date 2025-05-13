# main.py
import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from webhook_router import router as webhook_router

# 환경 변수 로드
load_dotenv()

# 기본 디렉토리 설정
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = BASE_DIR / "static"
STORAGE_DIR = BASE_DIR / "storage"
LOG_DIR = STORAGE_DIR / "webhooks"
STRATEGY_DIR = STORAGE_DIR / "strategies"

# 디렉토리가 없으면 생성
STATIC_DIR.mkdir(exist_ok=True)
STORAGE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
STRATEGY_DIR.mkdir(parents=True, exist_ok=True)

# FastAPI 앱 생성
app = FastAPI(
    title="Auto-Trading Code Modifier",
    description="LLM 기반 자동 코드 수정 시스템을 갖춘 백엔드 서버입니다. TradingView에서 보내는 웹훅을 수신하고, Pine Script 코드를 자동으로 분석 및 개선합니다.",
    version="0.1.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 서비스에서는 구체적인 도메인으로 제한하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 제공
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 환경 변수 설정
webhook_router.LOG_DIR = LOG_DIR
webhook_router.STRATEGY_DIR = STRATEGY_DIR

# 웹훅 라우터 포함
app.include_router(webhook_router, prefix="/webhook")

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    루트 경로에서 HTML 파일을 제공합니다.
    """
    index_file = STATIC_DIR / "index.html"
    
    # 파일이 존재하면 반환
    if index_file.exists():
        with open(index_file, "r") as f:
            return f.read()
    
    # 파일이 없으면 기본 응답
    return """
    <html>
        <head>
            <title>Auto-Trading Code Modifier</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333366; }
                .endpoint { margin-bottom: 15px; padding: 10px; background-color: #f8f8f8; border-radius: 5px; }
                .method { font-weight: bold; color: #009900; }
                .url { font-family: monospace; }
                .description { margin-top: 5px; color: #666; }
            </style>
        </head>
        <body>
            <h1>Auto-Trading Code Modifier API</h1>
            <p>
                TradingView에서 본 웹훅을 처리하여 거래 전략 코드를 자동으로 개선하는 시스템입니다.
            </p>
            <h2>사용 가능한 엔드포인트:</h2>
            <div class="endpoint">
                <div><span class="method">POST</span> <span class="url">/webhook/</span></div>
                <div class="description">TradingView에서 본 웹훅을 처리합니다.</div>
            </div>
            <div class="endpoint">
                <div><span class="method">GET</span> <span class="url">/webhook/test</span></div>
                <div class="description">샘플 데이터로 분석 테스트를 수행합니다.</div>
            </div>
            <div class="endpoint">
                <div><span class="method">GET</span> <span class="url">/webhook/history</span></div>
                <div class="description">수정 내역을 확인합니다.</div>
            </div>
            <div class="endpoint">
                <div><span class="method">GET</span> <span class="url">/webhook/status</span></div>
                <div class="description">시스템 상태를 확인합니다.</div>
            </div>
            <div class="endpoint">
                <div><span class="method">GET</span> <span class="url">/webhook/strategy/{filename}</span></div>
                <div class="description">특정 전략 코드를 조회합니다.</div>
            </div>
            <div class="endpoint">
                <div><span class="method">GET</span> <span class="url">/webhook/webhook/{filename}</span></div>
                <div class="description">특정 웹훅 데이터를 조회합니다.</div>
            </div>
        </body>
    </html>
    """ 
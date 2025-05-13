# main.py
import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from webhook_router import router as webhook_router
import uvicorn
import sys
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")

# 환경 변수 로드
load_dotenv()

# Vercel 환경 감지
is_vercel = os.environ.get("VERCEL") == "1"

# 기본 디렉토리 설정
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = BASE_DIR / "static"

# Vercel 환경에서는 임시 디렉토리를 사용
if is_vercel:
    STORAGE_DIR = Path("/tmp/storage")
else:
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
    title="자동 트레이딩 코드 수정기 - 리다이렉션",
    description="API 모듈로 요청을 리다이렉션합니다",
    version="1.0.0"
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

@app.get("/", include_in_schema=False)
async def root():
    """
    API 모듈로 리다이렉션합니다.
    """
    logger.debug("루트 엔드포인트 접근, API 모듈로 리다이렉션")
    return RedirectResponse(url="/api")

@app.get("/api", include_in_schema=False)
async def api_root():
    """
    API 모듈로 리다이렉션합니다.
    """
    logger.debug("API 엔드포인트 접근, API 인덱스로 리다이렉션")
    return {
        "status": "operational",
        "message": "자동 트레이딩 코드 수정 API가 작동 중입니다. API 모듈을 사용하세요.",
        "api_module": "/api/index.py"
    }

# API 모듈 임포트
try:
    logger.debug("API 모듈 임포트 시도")
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from api.index import app as api_app
    
    # API 모듈 마운트
    app.mount("/api", api_app)
    logger.debug("API 모듈 마운트 성공")
except Exception as e:
    logger.error(f"API 모듈 임포트 또는 마운트 실패: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# 직접 실행 시
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
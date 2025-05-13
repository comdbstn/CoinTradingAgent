# main.py
import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
import sys
import logging
import traceback
import datetime

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")

# 환경 변수 로드
load_dotenv()

# Vercel 환경 확인
is_vercel = os.environ.get("VERCEL", "") != ""
logger.debug(f"Vercel 환경 확인: {is_vercel}")

# 디렉토리 설정
def setup_vercel_directories():
    """Vercel 서버리스 환경에서 필요한 디렉토리를 생성합니다."""
    try:
        # 기본 스토리지 디렉토리 설정 (Vercel에서는 /tmp를 사용)
        storage_base = "/tmp/storage"
        
        # 웹훅 및 전략 디렉토리 경로
        webhook_dir = os.path.join(storage_base, "webhooks")
        strategy_dir = os.path.join(storage_base, "strategies")
        
        logger.debug(f"Vercel 디렉토리 설정 - 웹훅: {webhook_dir}, 전략: {strategy_dir}")
        
        # 디렉토리 생성
        os.makedirs(webhook_dir, exist_ok=True)
        os.makedirs(strategy_dir, exist_ok=True)
        
        # 환경 변수 설정
        os.environ["LOG_DIR"] = webhook_dir
        os.environ["STRATEGY_DIR"] = strategy_dir
        
        return {
            "storage_base": storage_base,
            "webhook_dir": webhook_dir,
            "strategy_dir": strategy_dir
        }
    except Exception as e:
        logger.error(f"Vercel 디렉토리 설정 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        # 오류 발생 시에도 기본값 설정
        os.environ["LOG_DIR"] = "/tmp/storage/webhooks"
        os.environ["STRATEGY_DIR"] = "/tmp/storage/strategies"
        return {
            "error": str(e),
            "webhook_dir": "/tmp/storage/webhooks",
            "strategy_dir": "/tmp/storage/strategies"
        }

# Vercel 환경이면 디렉토리 설정 실행
if is_vercel:
    logger.debug("Vercel 환경에서 디렉토리 설정 시작")
    directories = setup_vercel_directories()
    logger.debug(f"Vercel 디렉토리 설정 완료: {directories}")

# FastAPI 앱 생성
app = FastAPI(
    title="자동 트레이딩 코드 수정기",
    description="TradingView에서 웹훅을 받아 Pine Script 코드를 분석하고 개선하는 API",
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

# 웹훅 라우터 임포트 및 등록
try:
    logger.debug("웹훅 라우터 임포트 시도")
    # 현재 디렉토리를 경로에 추가
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # 디렉토리가 이미 존재하는지 확인
    if is_vercel:
        os.makedirs("/tmp/storage/webhooks", exist_ok=True)
        os.makedirs("/tmp/storage/strategies", exist_ok=True)
    
    # webhook_router.py 직접 임포트
    try:
        from webhook_router import router as webhook_router
        logger.debug("webhook_router.py 직접 임포트 성공")
    except ImportError:
        logger.warning("webhook_router.py 임포트 실패, api 패키지 시도")
        # API 패키지 내부에서 임포트 시도
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))
        from api.webhook_router import router as webhook_router
        logger.debug("api.webhook_router 임포트 성공")
    
    # 웹훅 라우터 등록
    app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])
    logger.debug("웹훅 라우터 등록 완료")
except Exception as e:
    logger.error(f"웹훅 라우터 등록 실패: {str(e)}")
    logger.error(traceback.format_exc())

@app.get("/", include_in_schema=False)
async def root():
    """
    루트 경로에서 API 정보를 반환합니다.
    """
    try:
        logger.debug("루트 엔드포인트 접근")
        
        return JSONResponse({
            "status": "operational",
            "message": "자동 트레이딩 코드 수정 API가 작동 중입니다.",
            "endpoints": {
                "webhook": "/webhook/ - TradingView 웹훅 수신 (POST)",
                "test": "/webhook/test - 테스트 분석 실행 (GET)",
                "history": "/webhook/history - 수정 내역 조회 (GET)",
                "status": "/webhook/status - 시스템 상태 조회 (GET)"
            },
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "environment": {
                "python_version": sys.version,
                "is_vercel": is_vercel,
                "python_path": sys.path,
                "env_vars": {k: v for k, v in dict(os.environ).items() 
                           if not k.startswith("AWS") 
                           and k not in ["OPENAI_API_KEY", "VERCEL_TOKEN"]
                           and not k.startswith("_")}
            }
        })
    except Exception as e:
        logger.error(f"루트 엔드포인트 처리 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse({
            "status": "error",
            "message": f"오류가 발생했습니다: {str(e)}",
            "traceback": traceback.format_exc()
        }, status_code=500)

@app.get("/api", include_in_schema=False)
async def api_root():
    """
    API 경로 정보를 반환합니다.
    """
    try:
        logger.debug("API 엔드포인트 접근")
        return RedirectResponse(url="/")
    except Exception as e:
        logger.error(f"API 엔드포인트 처리 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse({
            "status": "error",
            "message": f"오류가 발생했습니다: {str(e)}"
        }, status_code=500)

# 직접 실행 시
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
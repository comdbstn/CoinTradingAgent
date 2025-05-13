from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from pathlib import Path
import datetime
import sys
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("api")

# API 디렉토리의 상위 디렉토리를 sys.path에 추가하여 모듈 임포트 가능하게 함
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
logger.debug(f"sys.path: {sys.path}")

try:
    # 모듈 임포트
    from api.webhook_router import router as webhook_router
    logger.debug("webhook_router 모듈 임포트 성공")
except Exception as e:
    logger.error(f"webhook_router 모듈 임포트 실패: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# FastAPI 앱 생성
app = FastAPI(
    title="자동 트레이딩 코드 수정기",
    description="TradingView에서 웹훅을 받아 Pine Script 코드를 분석하고 개선하는 API",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용 (운영 환경에서는 제한해야 함)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디렉토리 설정
def setup_directories():
    """
    필요한 디렉토리를 생성합니다. Vercel 서버리스 환경에서는 /tmp를 사용합니다.
    """
    try:
        # Vercel 환경 확인
        is_vercel = bool(os.environ.get("VERCEL", ""))
        logger.debug(f"Vercel 환경: {is_vercel}")
        
        # 기본 스토리지 디렉토리 설정
        if is_vercel:
            # Vercel에서는 /tmp 디렉토리를 사용해야 함
            storage_base = "/tmp/storage"
        else:
            # 로컬 개발 환경에서는 프로젝트 루트의 storage 디렉토리 사용
            storage_base = "storage"
        
        # 웹훅 및 전략 디렉토리 경로
        webhook_dir = os.path.join(storage_base, "webhooks")
        strategy_dir = os.path.join(storage_base, "strategies")
        
        logger.debug(f"디렉토리 경로 - 웹훅: {webhook_dir}, 전략: {strategy_dir}")
        
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
        logger.error(f"디렉토리 설정 중 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# 서버 시작 시 디렉토리 설정
try:
    directories = setup_directories()
    logger.debug(f"디렉토리 설정 완료: {directories}")
except Exception as e:
    logger.error(f"디렉토리 설정 실패: {str(e)}")

# 라우터 등록
try:
    app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])
    logger.debug("웹훅 라우터 등록 완료")
except Exception as e:
    logger.error(f"웹훅 라우터 등록 실패: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

@app.get("/")
async def root():
    """
    API 루트 엔드포인트. 시스템 상태와 사용 가능한 엔드포인트를 보여줍니다.
    """
    try:
        return {
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
                "is_vercel": bool(os.environ.get("VERCEL", "")),
                "directories": directories if 'directories' in locals() else "설정 실패"
            }
        }
    except Exception as e:
        logger.error(f"루트 엔드포인트 처리 중 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"오류가 발생했습니다: {str(e)}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        } 
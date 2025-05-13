# webhook_router.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import os
import json
import datetime
from pathlib import Path
import pine_modifier

router = APIRouter()

# 기본 디렉토리 설정
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = BASE_DIR / "storage" / "webhooks"
STRATEGY_DIR = BASE_DIR / "storage" / "strategies"

# 디렉토리가 없으면 생성
LOG_DIR.mkdir(parents=True, exist_ok=True)
STRATEGY_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/")
async def receive_webhook(request: Request):
    """
    TradingView에서 보낸 웹훅을 처리합니다.
    """
    try:
        # 웹훅 데이터 받기
        webhook_data = await request.json()
        
        # 타임스탬프 생성
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 웹훅 데이터 로깅
        log_file = LOG_DIR / f"webhook_{timestamp}.json"
        with open(log_file, 'w') as f:
            json.dump(webhook_data, f, indent=4)
        
        # 샘플 전략 코드가 없으면 생성
        current_strategy_file = STRATEGY_DIR / "current.pine"
        if not current_strategy_file.exists():
            sample_strategy_file = STRATEGY_DIR / "example.pine"
            if sample_strategy_file.exists():
                # 샘플 전략 파일을 current.pine으로 복사
                with open(sample_strategy_file, 'r') as f:
                    sample_code = f.read()
                with open(current_strategy_file, 'w') as f:
                    f.write(sample_code)
            else:
                # 샘플 전략 파일이 없는 경우 기본 코드 생성
                with open(current_strategy_file, 'w') as f:
                    f.write("""
//@version=4
strategy("Simple RSI Strategy", overlay=true)
rsiLength = input(14, title="RSI 기간")
rsiOverbought = input(70, title="RSI 과매수 기준")
rsiOversold = input(30, title="RSI 과매도 기준")
rsiValue = rsi(close, rsiLength)
if (crossover(rsiValue, rsiOversold))
    strategy.entry("RSI_Long", strategy.long)
if (crossunder(rsiValue, rsiOverbought))
    strategy.entry("RSI_Short", strategy.short)
""")
        
        # 원본 전략 코드 로드
        with open(current_strategy_file, 'r') as f:
            original_code = f.read()
        
        # AI를 통한 수정된 코드 생성
        modified_code = pine_modifier.generate_modified_script(original_code, webhook_data)
        
        # 수정된 코드와 메타데이터 저장
        result = pine_modifier.save_modification(
            original_code, 
            modified_code, 
            webhook_data,
            str(STRATEGY_DIR)
        )
        
        return {
            "status": "success",
            "message": "웹훅 수신 및 전략 코드 수정 완료",
            "log_file": str(log_file),
            "modified_strategy": result["modified_file"],
            "metadata_file": result["metadata_file"]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"웹훅 처리 중 오류 발생: {str(e)}"
        }

@router.get("/test")
async def test_analysis():
    """
    샘플 전략 코드와 최근 웹훅 로그를 사용하여 테스트 분석을 수행합니다.
    """
    try:
        # 샘플 전략 코드 로드
        example_strategy_file = STRATEGY_DIR / "example.pine"
        with open(example_strategy_file, 'r') as f:
            example_code = f.read()
        
        # 최근 웹훅 로그 찾기
        webhook_files = list(LOG_DIR.glob("webhook_*.json"))
        if not webhook_files:
            return {
                "status": "error",
                "message": "웹훅 로그 파일이 없습니다."
            }
        
        # 가장 최근 파일 로드
        latest_webhook_file = max(webhook_files, key=lambda x: x.stat().st_mtime)
        with open(latest_webhook_file, 'r') as f:
            webhook_data = json.load(f)
        
        # AI를 통한 수정된 코드 생성
        modified_code = pine_modifier.test_analysis(example_code, webhook_data)
        
        return {
            "status": "success",
            "original_code": example_code,
            "modified_code": modified_code,
            "webhook_data": webhook_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"테스트 분석 중 오류 발생: {str(e)}"
        }

@router.get("/history")
async def get_modification_history():
    """
    수정 내역 메타데이터를 반환합니다.
    """
    try:
        # 메타데이터 파일 찾기
        metadata_files = list(STRATEGY_DIR.glob("metadata_*.json"))
        if not metadata_files:
            return {
                "status": "success",
                "history": []
            }
        
        # 최신 순으로 정렬
        metadata_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 메타데이터 로드
        history = []
        for file in metadata_files:
            try:
                with open(file, 'r') as f:
                    metadata = json.load(f)
                    
                # 중요 정보만 선택
                history.append({
                    "timestamp": metadata.get("timestamp", ""),
                    "original_strategy": metadata.get("original_strategy", ""),
                    "modified_strategy": metadata.get("modified_strategy", ""),
                    "performance_before": metadata.get("performance_before", {}),
                    "modification_summary": metadata.get("modification_summary", "")
                })
            except Exception as e:
                print(f"메타데이터 파일 '{file}' 처리 중 오류: {str(e)}")
        
        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"수정 내역 조회 중 오류 발생: {str(e)}"
        }

@router.get("/status")
async def get_system_status():
    """
    시스템 상태 정보를 반환합니다.
    """
    try:
        # 웹훅 로그 파일 카운트
        webhook_count = len(list(LOG_DIR.glob("webhook_*.json")))
        
        # 전략 파일 카운트
        strategy_count = len(list(STRATEGY_DIR.glob("*.pine")))
        
        # 수정 내역 메타데이터 카운트
        metadata_count = len(list(STRATEGY_DIR.glob("metadata_*.json")))
        
        # 최근 웹훅 데이터
        webhook_files = list(LOG_DIR.glob("webhook_*.json"))
        latest_webhook = None
        if webhook_files:
            latest_webhook_file = max(webhook_files, key=lambda x: x.stat().st_mtime)
            try:
                with open(latest_webhook_file, 'r') as f:
                    latest_webhook = {
                        "file": str(latest_webhook_file),
                        "timestamp": datetime.datetime.fromtimestamp(latest_webhook_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    }
            except Exception as e:
                latest_webhook = {"error": str(e)}
        
        # OpenAI API 키 상태
        api_key_status = "사용 가능" if pine_modifier.api_key is not None else "설정되지 않음"
        
        return {
            "status": "operational",
            "webhook_count": webhook_count,
            "strategy_count": strategy_count,
            "modification_count": metadata_count,
            "latest_webhook": latest_webhook,
            "api_key_status": api_key_status,
            "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"시스템 상태 조회 중 오류 발생: {str(e)}"
        }

@router.get("/strategy/{filename}")
async def get_strategy_code(filename: str):
    """
    특정 전략 코드를 반환합니다.
    """
    try:
        # 보안 체크: 파일명에 경로 문자가 포함되어 있는지 확인
        if "../" in filename or "..\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명 형식입니다.")
            
        strategy_file = STRATEGY_DIR / filename
        
        # 파일 존재 여부 확인
        if not strategy_file.exists():
            raise HTTPException(status_code=404, detail=f"전략 파일 '{filename}'을 찾을 수 없습니다.")
            
        # 파일이 디렉토리인지 확인
        if strategy_file.is_dir():
            raise HTTPException(status_code=400, detail=f"'{filename}'은 디렉토리입니다.")
            
        # 파일 접근 권한 확인
        if not os.access(strategy_file, os.R_OK):
            raise HTTPException(status_code=403, detail=f"전략 파일 '{filename}'에 접근할 수 없습니다.")
            
        # 파일 내용 읽기
        with open(strategy_file, 'r') as f:
            code = f.read()
            
        return {
            "status": "success",
            "filename": filename,
            "code": code
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전략 파일 읽기 중 오류 발생: {str(e)}")

@router.get("/webhook/{filename}")
async def get_webhook_data(filename: str):
    """
    특정 웹훅 데이터를 반환합니다.
    """
    try:
        # 보안 체크: 파일명에 경로 문자가 포함되어 있는지 확인
        if "../" in filename or "..\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명 형식입니다.")
            
        webhook_file = LOG_DIR / filename
        
        # 파일 존재 여부 확인
        if not webhook_file.exists():
            raise HTTPException(status_code=404, detail=f"웹훅 파일 '{filename}'을 찾을 수 없습니다.")
            
        # 파일이 디렉토리인지 확인
        if webhook_file.is_dir():
            raise HTTPException(status_code=400, detail=f"'{filename}'은 디렉토리입니다.")
            
        # 파일 접근 권한 확인
        if not os.access(webhook_file, os.R_OK):
            raise HTTPException(status_code=403, detail=f"웹훅 파일 '{filename}'에 접근할 수 없습니다.")
            
        # 파일 내용 읽기
        with open(webhook_file, 'r') as f:
            data = json.load(f)
            
        return {
            "status": "success",
            "filename": filename,
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"웹훅 파일 읽기 중 오류 발생: {str(e)}")
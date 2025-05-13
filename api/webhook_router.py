from fastapi import APIRouter, Request, HTTPException
import os
import json
import datetime
from pathlib import Path
import sys
import logging

# 로깅 설정
logger = logging.getLogger("api.webhook_router")

# API 디렉토리의 상위 디렉토리를 sys.path에 추가하여 모듈 임포트 가능하게 함
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
logger.debug(f"webhook_router - sys.path: {sys.path}")

# pine_modifier 모듈 임포트
try:
    from api.pine_modifier import generate_modified_script, save_modification, test_analysis, api_key
    logger.debug("pine_modifier 모듈 함수 임포트 성공")
except Exception as e:
    logger.error(f"pine_modifier 모듈 임포트 실패: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

router = APIRouter()

# 기본 디렉토리 설정 (나중에 index.py에서 설정됨)
LOG_DIR = os.getenv("LOG_DIR", "/tmp/storage/webhooks")
STRATEGY_DIR = os.getenv("STRATEGY_DIR", "/tmp/storage/strategies")
logger.debug(f"디렉토리 설정 - LOG_DIR: {LOG_DIR}, STRATEGY_DIR: {STRATEGY_DIR}")

@router.post("/")
async def receive_webhook(request: Request):
    """
    TradingView에서 보낸 웹훅을 처리합니다.
    """
    try:
        logger.debug("웹훅 수신 요청 시작")
        
        # 웹훅 데이터 받기
        webhook_data = await request.json()
        logger.debug(f"웹훅 데이터 수신 성공: {webhook_data.keys() if webhook_data else 'None'}")
        
        # 타임스탬프 생성
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 웹훅 데이터 로깅
        log_file = os.path.join(LOG_DIR, f"webhook_{timestamp}.json")
        logger.debug(f"로그 파일 경로: {log_file}")
        
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'w') as f:
                json.dump(webhook_data, f, indent=4)
            logger.debug("웹훅 데이터 로깅 완료")
        except Exception as write_error:
            logger.error(f"웹훅 데이터 저장 중 오류: {str(write_error)}")
        
        # 샘플 전략 코드가 없으면 생성
        current_strategy_file = os.path.join(STRATEGY_DIR, "current.pine")
        logger.debug(f"전략 파일 경로: {current_strategy_file}")
        
        if not os.path.exists(current_strategy_file):
            logger.debug("기본 전략 파일이 없어 생성 시작")
            try:
                os.makedirs(os.path.dirname(current_strategy_file), exist_ok=True)
                # 기본 코드 생성
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
                logger.debug("기본 전략 파일 생성 완료")
            except Exception as create_error:
                logger.error(f"기본 전략 파일 생성 중 오류: {str(create_error)}")
                raise
        
        # 원본 전략 코드 로드
        logger.debug("원본 전략 코드 로드 시작")
        try:
            with open(current_strategy_file, 'r') as f:
                original_code = f.read()
            logger.debug("원본 전략 코드 로드 완료")
        except Exception as read_error:
            logger.error(f"원본 전략 코드 로드 중 오류: {str(read_error)}")
            raise
        
        # AI를 통한 수정된 코드 생성
        logger.debug("AI를 통한 코드 수정 시작")
        try:
            modified_code = generate_modified_script(original_code, webhook_data)
            logger.debug("코드 수정 완료")
        except Exception as modify_error:
            logger.error(f"AI 코드 수정 중 오류: {str(modify_error)}")
            raise
        
        # 수정된 코드와 메타데이터 저장
        logger.debug("수정된 코드 저장 시작")
        try:
            result = save_modification(
                original_code, 
                modified_code, 
                webhook_data,
                STRATEGY_DIR
            )
            logger.debug(f"수정된 코드 저장 완료: {result}")
        except Exception as save_error:
            logger.error(f"수정된 코드 저장 중 오류: {str(save_error)}")
            raise
        
        return {
            "status": "success",
            "message": "웹훅 수신 및 전략 코드 수정 완료",
            "log_file": log_file,
            "modified_strategy": result["modified_file"],
            "metadata_file": result["metadata_file"]
        }
    except Exception as e:
        logger.error(f"웹훅 처리 중 오류 발생: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        logger.error(tb)
        return {
            "status": "error",
            "message": f"웹훅 처리 중 오류 발생: {str(e)}",
            "traceback": tb
        }

@router.get("/test")
async def test_analysis_endpoint():
    """
    샘플 전략 코드와 샘플 웹훅 데이터를 사용하여 테스트 분석을 수행합니다.
    """
    try:
        logger.debug("테스트 분석 시작")
        
        # 샘플 전략 코드
        sample_code = """
//@version=4
strategy("Simple RSI Strategy", overlay=true)
rsiLength = input(14, title="RSI 기간")
rsiOverbought = input(70, title="RSI 과매수 기준")
rsiOversold = input(33, title="RSI 과매도 기준")
rsiValue = rsi(close, rsiLength)
if (crossover(rsiValue, rsiOversold))
    strategy.entry("RSI_Long", strategy.long)
if (crossunder(rsiValue, rsiOverbought))
    strategy.entry("RSI_Short", strategy.short)
"""
        
        # 샘플 웹훅 데이터
        sample_webhook_data = {
            "trading_problem": "RSI 전략이 최근 상승 추세에서 수익성이 낮습니다. 과매수/과매도 기준이 현재 시장 상황에 최적화되지 않았으며, 이익실현 및 손절매 설정이 개선이 필요합니다.",
            "suggested_improvements": "RSI 과매도 기준을 28로 낮추고, 이익실현 비율을 5%에서 7%로 높이세요. 트레일링 스탑을 2%로 적용하고, 매도 신호에 볼린저 밴드 상단을 추가로 활용하여 더 정확한 매도 시점을 잡으세요."
        }
        
        logger.debug("샘플 데이터 준비 완료, AI 분석 시작")
        
        # AI를 통한 수정된 코드 생성
        try:
            modified_code = test_analysis(sample_code, sample_webhook_data)
            logger.debug("테스트 분석 완료")
        except Exception as analysis_error:
            logger.error(f"테스트 분석 중 오류: {str(analysis_error)}")
            raise
        
        return {
            "status": "success",
            "original_code": sample_code,
            "modified_code": modified_code,
            "webhook_data": sample_webhook_data
        }
    except Exception as e:
        logger.error(f"테스트 분석 중 오류 발생: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        logger.error(tb)
        return {
            "status": "error",
            "message": f"테스트 분석 중 오류 발생: {str(e)}",
            "traceback": tb
        }

@router.get("/history")
async def get_modification_history():
    """
    수정 내역 메타데이터를 반환합니다.
    """
    try:
        logger.debug("수정 내역 조회 시작")
        
        # 메타데이터 파일 찾기
        try:
            os.makedirs(STRATEGY_DIR, exist_ok=True)
            metadata_files = [os.path.join(STRATEGY_DIR, f) for f in os.listdir(STRATEGY_DIR) 
                            if f.startswith("metadata_") and f.endswith(".json")]
            logger.debug(f"메타데이터 파일 {len(metadata_files)}개 찾음")
        except Exception as list_error:
            logger.error(f"메타데이터 파일 목록 조회 중 오류: {str(list_error)}")
            metadata_files = []
        
        if not metadata_files:
            logger.debug("메타데이터 파일이 없음")
            return {
                "status": "success",
                "history": []
            }
        
        # 최신 순으로 정렬
        metadata_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
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
                logger.debug(f"메타데이터 파일 로드 성공: {file}")
            except Exception as e:
                logger.error(f"메타데이터 파일 '{file}' 처리 중 오류: {str(e)}")
        
        logger.debug(f"총 {len(history)}개의 수정 내역 로드 완료")
        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        logger.error(f"수정 내역 조회 중 오류 발생: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        logger.error(tb)
        return {
            "status": "error",
            "message": f"수정 내역 조회 중 오류 발생: {str(e)}",
            "traceback": tb
        }

@router.get("/status")
async def get_system_status():
    """
    시스템 상태 정보를 반환합니다.
    """
    try:
        logger.debug("시스템 상태 조회 시작")
        
        # 웹훅 로그 파일 카운트
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            webhook_count = len([f for f in os.listdir(LOG_DIR) if f.startswith("webhook_") and f.endswith(".json")])
            logger.debug(f"웹훅 로그 파일 카운트: {webhook_count}")
        except Exception as count_error:
            logger.error(f"웹훅 로그 파일 카운트 중 오류: {str(count_error)}")
            webhook_count = -1
        
        # 전략 파일 카운트
        try:
            os.makedirs(STRATEGY_DIR, exist_ok=True)
            strategy_count = len([f for f in os.listdir(STRATEGY_DIR) if f.endswith(".pine")])
            logger.debug(f"전략 파일 카운트: {strategy_count}")
        except Exception as count_error:
            logger.error(f"전략 파일 카운트 중 오류: {str(count_error)}")
            strategy_count = -1
        
        # 수정 내역 메타데이터 카운트
        try:
            metadata_count = len([f for f in os.listdir(STRATEGY_DIR) if f.startswith("metadata_") and f.endswith(".json")])
            logger.debug(f"메타데이터 파일 카운트: {metadata_count}")
        except Exception as count_error:
            logger.error(f"메타데이터 파일 카운트 중 오류: {str(count_error)}")
            metadata_count = -1
        
        # 최근 웹훅 데이터
        latest_webhook = None
        try:
            webhook_files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) 
                            if f.startswith("webhook_") and f.endswith(".json")]
            if webhook_files:
                latest_webhook_file = max(webhook_files, key=os.path.getmtime)
                try:
                    with open(latest_webhook_file, 'r') as f:
                        latest_webhook = {
                            "file": latest_webhook_file,
                            "timestamp": datetime.datetime.fromtimestamp(os.path.getmtime(latest_webhook_file)).strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    logger.debug(f"최근 웹훅 파일: {latest_webhook_file}")
                except Exception as read_error:
                    logger.error(f"최근 웹훅 파일 읽기 중 오류: {str(read_error)}")
                    latest_webhook = {"error": str(read_error)}
        except Exception as list_error:
            logger.error(f"웹훅 파일 목록 조회 중 오류: {str(list_error)}")
        
        # OpenAI API 키 상태
        api_key_status = "사용 가능" if api_key is not None else "설정되지 않음"
        logger.debug(f"API 키 상태: {api_key_status}")
        
        return {
            "status": "operational",
            "webhook_count": webhook_count,
            "strategy_count": strategy_count,
            "modification_count": metadata_count,
            "latest_webhook": latest_webhook,
            "api_key_status": api_key_status,
            "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "directories": {
                "LOG_DIR": LOG_DIR,
                "STRATEGY_DIR": STRATEGY_DIR
            }
        }
    except Exception as e:
        logger.error(f"시스템 상태 조회 중 오류 발생: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        logger.error(tb)
        return {
            "status": "error",
            "message": f"시스템 상태 조회 중 오류 발생: {str(e)}",
            "traceback": tb
        }

@router.get("/strategy/{filename}")
async def get_strategy_code(filename: str):
    """
    특정 전략 코드를 반환합니다.
    """
    try:
        logger.debug(f"전략 코드 조회 시작: {filename}")
        
        # 보안 체크: 파일명에 경로 문자가 포함되어 있는지 확인
        if "../" in filename or "..\\" in filename:
            logger.warning(f"잘못된 파일명 형식: {filename}")
            raise HTTPException(status_code=400, detail="잘못된 파일명 형식입니다.")
            
        strategy_file = os.path.join(STRATEGY_DIR, filename)
        logger.debug(f"전략 파일 경로: {strategy_file}")
        
        # 파일 존재 여부 확인
        if not os.path.exists(strategy_file):
            logger.warning(f"전략 파일을 찾을 수 없음: {filename}")
            raise HTTPException(status_code=404, detail=f"전략 파일 '{filename}'을 찾을 수 없습니다.")
            
        # 파일이 디렉토리인지 확인
        if os.path.isdir(strategy_file):
            logger.warning(f"전략 파일이 디렉토리임: {filename}")
            raise HTTPException(status_code=400, detail=f"'{filename}'은 디렉토리입니다.")
            
        # 파일 접근 권한 확인
        if not os.access(strategy_file, os.R_OK):
            logger.warning(f"전략 파일에 접근할 수 없음: {filename}")
            raise HTTPException(status_code=403, detail=f"전략 파일 '{filename}'에 접근할 수 없습니다.")
            
        # 파일 내용 읽기
        with open(strategy_file, 'r') as f:
            code = f.read()
        logger.debug(f"전략 코드 읽기 성공: {len(code)} 바이트")
            
        return {
            "status": "success",
            "filename": filename,
            "code": code
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전략 파일 읽기 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"전략 파일 읽기 중 오류 발생: {str(e)}")

@router.get("/webhook/{filename}")
async def get_webhook_data(filename: str):
    """
    특정 웹훅 데이터를 반환합니다.
    """
    try:
        logger.debug(f"웹훅 데이터 조회 시작: {filename}")
        
        # 보안 체크: 파일명에 경로 문자가 포함되어 있는지 확인
        if "../" in filename or "..\\" in filename:
            logger.warning(f"잘못된 파일명 형식: {filename}")
            raise HTTPException(status_code=400, detail="잘못된 파일명 형식입니다.")
            
        webhook_file = os.path.join(LOG_DIR, filename)
        logger.debug(f"웹훅 파일 경로: {webhook_file}")
        
        # 파일 존재 여부 확인
        if not os.path.exists(webhook_file):
            logger.warning(f"웹훅 파일을 찾을 수 없음: {filename}")
            raise HTTPException(status_code=404, detail=f"웹훅 파일 '{filename}'을 찾을 수 없습니다.")
            
        # 파일이 디렉토리인지 확인
        if os.path.isdir(webhook_file):
            logger.warning(f"웹훅 파일이 디렉토리임: {filename}")
            raise HTTPException(status_code=400, detail=f"'{filename}'은 디렉토리입니다.")
            
        # 파일 접근 권한 확인
        if not os.access(webhook_file, os.R_OK):
            logger.warning(f"웹훅 파일에 접근할 수 없음: {filename}")
            raise HTTPException(status_code=403, detail=f"웹훅 파일 '{filename}'에 접근할 수 없습니다.")
            
        # 파일 내용 읽기
        with open(webhook_file, 'r') as f:
            data = json.load(f)
        logger.debug(f"웹훅 데이터 읽기 성공: {len(str(data))} 바이트")
            
        return {
            "status": "success",
            "filename": filename,
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"웹훅 파일 읽기 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"웹훅 파일 읽기 중 오류 발생: {str(e)}") 
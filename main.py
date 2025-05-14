# main.py
import os
import json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn
import sys
import logging
import traceback
import datetime

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")

# 환경 변수 로드 (.env 파일)
try:
    load_dotenv()
    logger.debug("환경 변수 파일(.env)을 로드했습니다.")
except Exception as e:
    logger.warning(f"환경 변수 로드 중 오류: {str(e)}")

# 중요 환경 변수 확인
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    # 키의 일부만 로그에 표시 (보안)
    key_preview = OPENAI_API_KEY[:4] + "..." + OPENAI_API_KEY[-4:] if len(OPENAI_API_KEY) > 8 else "너무 짧음"
    logger.debug(f"OpenAI API 키가 설정되어 있습니다: {key_preview}")
    
    # API 키를 전역 환경 변수로 설정
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
else:
    logger.warning("OpenAI API 키가 설정되어 있지 않습니다. 일부 기능이 작동하지 않을 수 있습니다.")

# Vercel 환경인지 확인
is_vercel = os.environ.get("VERCEL", "") != ""
logger.debug(f"Vercel 환경 확인: {is_vercel}")

# 기본 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
LOG_DIR = os.getenv("LOG_DIR", os.path.join(BASE_DIR, "storage", "webhooks"))
STRATEGY_DIR = os.getenv("STRATEGY_DIR", os.path.join(BASE_DIR, "storage", "strategies"))

# Vercel 환경에서 디렉토리 설정 함수
def setup_vercel_directories():
    """Vercel 환경에서 필요한 디렉토리를 설정합니다."""
    try:
        # 임시 디렉토리에 필요한 폴더 생성
        tmp_root = "/tmp"
        log_dir = os.path.join(tmp_root, "storage", "webhooks")
        strategy_dir = os.path.join(tmp_root, "storage", "strategies")
        static_dir = os.path.join(tmp_root, "static")
        
        # 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(strategy_dir, exist_ok=True)
        os.makedirs(static_dir, exist_ok=True)
        
        # 환경 변수 설정
        os.environ["LOG_DIR"] = log_dir
        os.environ["STRATEGY_DIR"] = strategy_dir
        
        # 기본 index.html 생성
        index_html_path = os.path.join(static_dir, "index.html")
        if not os.path.exists(index_html_path):
            with open(index_html_path, "w") as f:
                f.write("""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>자동 트레이딩 코드 수정기</title>
    <style>
        body { font-family: 'Pretendard', -apple-system, sans-serif; background-color: #f9fafb; color: #111827; line-height: 1.6; margin: 0; padding: 2rem; }
        .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 2rem; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h1 { color: #1e40af; font-weight: 700; margin-top: 0; }
        .api-status { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; margin-left: 0.5rem; }
        .api-status.available { background-color: #dcfce7; color: #166534; }
        .api-status.unavailable { background-color: #fee2e2; color: #991b1b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>자동 트레이딩 코드 수정기</h1>
        <p>TradingView에서 웹훅을 받아 Pine Script 코드를 분석하고 개선하는 API입니다.</p>
        <div>
            <h2>API 상태 <span class="api-status" id="apiStatus">확인 중...</span></h2>
            <p id="apiMessage">API 상태를 확인하는 중입니다...</p>
        </div>
        <ul>
            <li><a href="/webhook/test">테스트 분석 실행</a></li>
            <li><a href="/webhook/history">수정 내역 조회</a></li>
            <li><a href="/webhook/status">시스템 상태 확인</a></li>
        </ul>
    </div>
    <script>
        // API 상태 확인
        fetch('/webhook/status')
        .then(response => response.json())
        .then(data => {
            const statusEl = document.getElementById('apiStatus');
            const messageEl = document.getElementById('apiMessage');
            
            if (data.api_key && data.api_key.status === '사용 가능') {
                statusEl.textContent = '사용 가능';
                statusEl.className = 'api-status available';
                messageEl.textContent = data.api_key.message || 'OpenAI API가 정상적으로 구성되었습니다.';
            } else {
                statusEl.textContent = '미설정';
                statusEl.className = 'api-status unavailable';
                messageEl.textContent = data.api_key.message || 'OpenAI API 키가 설정되지 않았습니다.';
            }
        })
        .catch(error => {
            const statusEl = document.getElementById('apiStatus');
            const messageEl = document.getElementById('apiMessage');
            statusEl.textContent = '오류';
            statusEl.className = 'api-status unavailable';
            messageEl.textContent = '서버 연결 중 오류가 발생했습니다.';
        });
    </script>
</body>
</html>
                """)
        
        logger.debug(f"Vercel 디렉토리 설정 완료: LOG_DIR={log_dir}, STRATEGY_DIR={strategy_dir}")
        return {
            "LOG_DIR": log_dir, 
            "STRATEGY_DIR": strategy_dir,
            "STATIC_DIR": static_dir
        }
    except Exception as e:
        logger.error(f"Vercel 디렉토리 설정 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

# 정적 파일 디렉토리 생성
try:
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    # 기본 HTML 파일 생성 (static 디렉토리에 index.html이 없을 경우)
    index_html_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_html_path):
        with open(index_html_path, "w") as f:
            f.write("""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>자동 트레이딩 코드 수정기</title>
    <style>
        body {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            background-color: #f9fafb;
            color: #111827;
            line-height: 1.6;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        header {
            background-color: #1e40af;
            color: white;
            padding: 1.5rem 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        header .container {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1, h2, h3 {
            font-weight: 700;
        }
        .card {
            background-color: white;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border-left: 4px solid #1e40af;
        }
        .error-card {
            background-color: #fee2e2;
            border-left: 4px solid #dc2626;
        }
        .success-card {
            background-color: #ecfdf5;
            border-left: 4px solid #10b981;
        }
        .button {
            display: inline-block;
            background-color: #1e40af;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 0.25rem;
            text-decoration: none;
            font-weight: 600;
            transition: background-color 0.3s;
        }
        .button:hover {
            background-color: #1c3879;
        }
        #api-status {
            padding: 1rem;
            border-radius: 0.25rem;
        }
        .status-operational {
            background-color: #ecfdf5;
            color: #065f46;
        }
        .status-error {
            background-color: #fee2e2;
            color: #991b1b;
        }
        .endpoint-list {
            list-style: none;
            padding: 0;
        }
        .endpoint-list li {
            margin-bottom: 0.5rem;
            padding: 0.75rem;
            background-color: #f3f4f6;
            border-radius: 0.25rem;
        }
        footer {
            text-align: center;
            padding: 2rem 0;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
            margin-top: 2rem;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>자동 트레이딩 코드 수정기</h1>
        </div>
    </header>

    <main class="container">
        <div class="card" id="api-info">
            <h2>API 상태</h2>
            <div id="api-status">상태 확인 중...</div>
            <div id="api-message"></div>
            <div id="api-time"></div>
        </div>

        <div class="card">
            <h2>API 엔드포인트</h2>
            <ul class="endpoint-list" id="endpoint-list">
                <li>엔드포인트 로딩 중...</li>
            </ul>
        </div>

        <div class="card">
            <h2>테스트 분석 실행</h2>
            <p>샘플 트레이딩 코드와 데이터를 사용하여 테스트 분석을 실행할 수 있습니다.</p>
            <a href="/webhook/test" class="button" id="test-button">테스트 실행</a>
            <div id="test-result" style="margin-top: 1rem;"></div>
        </div>

        <div class="card">
            <h2>웹훅 히스토리</h2>
            <p>지금까지 처리된 웹훅 요청과 수정 내역을 확인할 수 있습니다.</p>
            <a href="/webhook/history" class="button" id="history-button">히스토리 확인</a>
            <div id="history-result" style="margin-top: 1rem;"></div>
        </div>
    </main>

    <footer class="container">
        <p>© 2025 자동 트레이딩 코드 수정기 | Powered by OpenAI</p>
    </footer>

    <script>
        // API 상태 확인
        async function checkApiStatus() {
            try {
                const response = await fetch('/');
                if (response.ok) {
                    const data = await response.json();
                    
                    // 상태 표시
                    const statusElement = document.getElementById('api-status');
                    statusElement.textContent = data.status === 'operational' 
                        ? '정상 작동 중' 
                        : '오류 발생';
                    statusElement.className = data.status === 'operational' 
                        ? 'status-operational' 
                        : 'status-error';
                    
                    // 메시지 표시
                    document.getElementById('api-message').textContent = data.message || '';
                    
                    // 시간 표시
                    document.getElementById('api-time').textContent = 
                        data.timestamp ? `마지막 업데이트: ${data.timestamp}` : '';
                    
                    // 엔드포인트 목록 표시
                    if (data.endpoints) {
                        const endpointList = document.getElementById('endpoint-list');
                        endpointList.innerHTML = '';
                        
                        Object.entries(data.endpoints).forEach(([key, value]) => {
                            const listItem = document.createElement('li');
                            listItem.textContent = value;
                            endpointList.appendChild(listItem);
                        });
                    }
                } else {
                    setErrorStatus();
                }
            } catch (error) {
                console.error("API 상태 확인 중 오류:", error);
                setErrorStatus();
            }
        }
        
        function setErrorStatus() {
            const statusElement = document.getElementById('api-status');
            statusElement.textContent = '서버 연결 오류';
            statusElement.className = 'status-error';
            document.getElementById('api-message').textContent = '서버에 연결할 수 없거나 응답을 받지 못했습니다.';
        }
        
        // 테스트 분석 실행
        document.getElementById('test-button').addEventListener('click', async function(e) {
            e.preventDefault();
            const resultElement = document.getElementById('test-result');
            resultElement.innerHTML = '<p>테스트 분석 실행 중...</p>';
            
            try {
                const response = await fetch('/webhook/test');
                if (response.ok) {
                    const data = await response.json();
                    resultElement.innerHTML = `
                        <div class="card success-card">
                            <h3>테스트 분석 완료</h3>
                            <p>상태: ${data.status}</p>
                        </div>
                    `;
                } else {
                    resultElement.innerHTML = `
                        <div class="card error-card">
                            <h3>테스트 분석 실패</h3>
                            <p>상태 코드: ${response.status}</p>
                        </div>
                    `;
                }
            } catch (error) {
                console.error("테스트 분석 중 오류:", error);
                resultElement.innerHTML = `
                    <div class="card error-card">
                        <h3>테스트 분석 오류</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        });
        
        // 히스토리 확인
        document.getElementById('history-button').addEventListener('click', async function(e) {
            e.preventDefault();
            const resultElement = document.getElementById('history-result');
            resultElement.innerHTML = '<p>히스토리 로딩 중...</p>';
            
            try {
                const response = await fetch('/webhook/history');
                if (response.ok) {
                    const data = await response.json();
                    if (data.history && data.history.length > 0) {
                        let historyHtml = '<div class="card success-card"><h3>수정 내역</h3><ul>';
                        
                        data.history.forEach(item => {
                            historyHtml += `
                                <li>
                                    <strong>시간:</strong> ${item.timestamp}<br>
                                    <strong>원본 전략:</strong> ${item.original_strategy}<br>
                                    <strong>수정된 전략:</strong> ${item.modified_strategy}<br>
                                    <strong>수정 내용:</strong> ${item.modification_summary}
                                </li>
                            `;
                        });
                        
                        historyHtml += '</ul></div>';
                        resultElement.innerHTML = historyHtml;
                    } else {
                        resultElement.innerHTML = `
                            <div class="card">
                                <h3>수정 내역이 없습니다</h3>
                                <p>아직 처리된 웹훅이 없습니다.</p>
                            </div>
                        `;
                    }
                } else {
                    resultElement.innerHTML = `
                        <div class="card error-card">
                            <h3>히스토리 로드 실패</h3>
                            <p>상태 코드: ${response.status}</p>
                        </div>
                    `;
                }
            } catch (error) {
                console.error("히스토리 로드 중 오류:", error);
                resultElement.innerHTML = `
                    <div class="card error-card">
                        <h3>히스토리 로드 오류</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        });
        
        // 페이지 로드 시 API 상태 확인
        document.addEventListener('DOMContentLoaded', checkApiStatus);
        
        // 30초마다 API 상태 확인
        setInterval(checkApiStatus, 30000);
    </script>
</body>
</html>
            """)
        logger.debug("기본 index.html 파일 생성 완료")
except Exception as e:
    logger.error(f"정적 파일 디렉토리 생성 중 오류: {str(e)}")
    logger.error(traceback.format_exc())

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

# 정적 파일 제공 설정 (오류가 발생해도 계속 진행)
try:
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    logger.debug(f"정적 파일 마운트 완료: {STATIC_DIR}")
except Exception as e:
    logger.error(f"정적 파일 마운트 중 오류: {str(e)}")
    logger.error(traceback.format_exc())

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
        try:
            from api.webhook_router import router as webhook_router
            logger.debug("api.webhook_router 임포트 성공")
        except ImportError:
            logger.error("webhook_router를 어디에서도 임포트할 수 없습니다.")
            # 더미 라우터 생성
            from fastapi import APIRouter
            webhook_router = APIRouter()
            
            @webhook_router.get("/")
            async def dummy_webhook():
                return {"status": "error", "message": "웹훅 라우터를 로드할 수 없습니다."}
    
    # 웹훅 라우터 등록
    app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])
    logger.debug("웹훅 라우터 등록 완료")
except Exception as e:
    logger.error(f"웹훅 라우터 등록 실패: {str(e)}")
    logger.error(traceback.format_exc())

@app.get("/", include_in_schema=False)
async def root():
    """
    루트 경로에서 API 정보를 반환하거나 정적 HTML 페이지를 제공합니다.
    """
    try:
        logger.debug("루트 엔드포인트 접근")
        
        # 헤더 확인 - HTML 요청인지 확인
        accept_header = "text/html"  # 기본값
        
        # HTML이 요청되면 index.html 반환
        if accept_header.startswith("text/html"):
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r") as f:
                    content = f.read()
                return HTMLResponse(content=content)
        
        # API 정보 반환
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
                "python_path": sys.path
            }
        })
    except Exception as e:
        logger.error(f"루트 엔드포인트 처리 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 오류가 발생해도 기본 HTML 반환
        fallback_html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>자동 트레이딩 코드 수정기</title>
            <style>
                body {{ font-family: 'Pretendard', -apple-system, sans-serif; background-color: #f9fafb; color: #111827; line-height: 1.6; margin: 0; padding: 2rem; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 2rem; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                h1 {{ color: #1e40af; font-weight: 700; margin-top: 0; }}
                .error {{ background-color: #fee2e2; color: #991b1b; padding: 1rem; border-radius: 0.25rem; margin: 1rem 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>자동 트레이딩 코드 수정기</h1>
                <p>API 서버가 현재 연결 상태를 확인하는 중입니다.</p>
                <div class="error">
                    <p>서버에서 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.</p>
                </div>
                <p>기본 기능은 계속 이용하실 수 있습니다.</p>
                <ul>
                    <li><a href="/webhook/test">테스트 분석 실행</a></li>
                    <li><a href="/webhook/history">수정 내역 조회</a></li>
                    <li><a href="/webhook/status">시스템 상태 확인</a></li>
                </ul>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=fallback_html)

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

# 오류 핸들러 등록
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP 예외 발생: {exc.detail}")
    
    # HTML 응답 요청인지 확인
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        # HTML 오류 페이지 반환
        error_html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>오류 발생 - 자동 트레이딩 코드 수정기</title>
            <style>
                body {{ font-family: 'Pretendard', -apple-system, sans-serif; background-color: #f9fafb; color: #111827; line-height: 1.6; margin: 0; padding: 2rem; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 2rem; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                h1 {{ color: #dc2626; font-weight: 700; margin-top: 0; }}
                .error {{ background-color: #fee2e2; color: #991b1b; padding: 1rem; border-radius: 0.25rem; margin: 1rem 0; }}
                .button {{ display: inline-block; background-color: #1e40af; color: white; padding: 0.5rem 1rem; text-decoration: none; border-radius: 0.25rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>오류가 발생했습니다</h1>
                <div class="error">
                    <p><strong>상태 코드:</strong> {exc.status_code}</p>
                    <p><strong>오류 메시지:</strong> {exc.detail}</p>
                </div>
                <p>홈페이지로 돌아가서 다시 시도해 주세요.</p>
                <a href="/" class="button">홈페이지로 이동</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=exc.status_code)
    
    # JSON 응답
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"일반 예외 발생: {str(exc)}")
    logger.error(traceback.format_exc())
    
    # HTML 응답 요청인지 확인
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        # HTML 오류 페이지 반환
        error_html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>서버 오류 - 자동 트레이딩 코드 수정기</title>
            <style>
                body {{ font-family: 'Pretendard', -apple-system, sans-serif; background-color: #f9fafb; color: #111827; line-height: 1.6; margin: 0; padding: 2rem; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 2rem; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                h1 {{ color: #dc2626; font-weight: 700; margin-top: 0; }}
                .error {{ background-color: #fee2e2; color: #991b1b; padding: 1rem; border-radius: 0.25rem; margin: 1rem 0; }}
                .button {{ display: inline-block; background-color: #1e40af; color: white; padding: 0.5rem 1rem; text-decoration: none; border-radius: 0.25rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>서버 오류가 발생했습니다</h1>
                <div class="error">
                    <p>서버에서 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.</p>
                </div>
                <p>홈페이지로 돌아가서 다시 시도해 주세요.</p>
                <a href="/" class="button">홈페이지로 이동</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)
    
    # JSON 응답
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": f"서버 오류가 발생했습니다: {str(exc)}"}
    )

# 직접 실행 시
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
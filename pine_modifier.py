# pine_modifier.py
import os
import re
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv
import openai

# 환경 변수 로드
load_dotenv()

# API 키 확인 및 적절한 모듈 선택
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    use_mock = False
    print("실제 OpenAI API를 사용합니다.")
else:
    use_mock = True
    print("API 키가 없어 모의 OpenAI API를 사용합니다.")

openai.api_key = api_key

def load_prompt_template():
    """프롬프트 템플릿을 로드합니다."""
    template_path = "prompt_template.txt"
    
    # 파일이 없으면 기본 템플릿 생성 (Vercel 환경용)
    if not os.path.exists(template_path):
        with open(template_path, "w") as f:
            f.write("""
📄 원본 전략 코드:
{original_code}

📊 최근 거래 로그:
{recent_log}

🔍 전략 코드의 문제점을 분석하고, Pine Script 코드를 자동으로 개선해주세요.

요구사항:
1. 문제점이 무엇인지 요약해주세요
2. 어떤 부분을 어떻게 수정해야 하는지 설명해주세요
3. 수정된 Pine Script 코드를 전체 출력해주세요
            """.strip())
    
    with open(template_path, "r") as f:
        return f.read()

def load_strategy_code(strategy_file):
    """전략 코드 파일을 로드합니다."""
    with open(strategy_file, 'r') as file:
        return file.read()

def generate_modified_script(original_code, webhook_data):
    """
    OpenAI를 사용하여 거래 성능 분석 및 입력 데이터를 기반으로 수정된 트레이딩 스크립트를 생성합니다.
    """
    try:
        # 데이터 준비
        analysis = webhook_data.get("trading_problem", "성능 데이터 없음")
        suggestions = webhook_data.get("suggested_improvements", "개선 제안 없음")
        
        # API 요청
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """
                당신은 트레이딩 전략 최적화 전문가입니다. TradingView의 Pine Script로 작성된 트레이딩 전략을 
                분석하고 개선하는 일을 담당합니다. 제공된 성능 데이터와 문제점을 분석하여 거래 전략을 
                최적화하세요. 수정된 전체 코드를 반환해야 합니다.
                """},
                {"role": "user", "content": f"""
                # 원본 Pine Script 코드:
                ```
                {original_code}
                ```
                
                # 성능 분석:
                {analysis}
                
                # 개선 제안:
                {suggestions}
                
                # 요구사항:
                1. 위 개선 제안을 반영하여 Pine Script 코드를 수정해주세요.
                2. 기존 코드의 구조를 최대한 유지하면서 핵심 로직을 개선해주세요.
                3. 수정된 전체 코드를 반환해주세요.
                4. 코드에 중요한 변경 사항에 주석을 추가해주세요.
                ```
                """}
            ],
            temperature=0.2,
            max_tokens=2500
        )
        
        # 응답에서 코드 추출
        modified_code = response.choices[0].message.content
        
        # 코드 블록 추출
        if "```" in modified_code:
            code_blocks = modified_code.split("```")
            for block in code_blocks:
                # pine, pinescript 등으로 시작하는 코드 블록이나 코드 블록만 있는 경우
                if block.strip().startswith("pine") or not block.strip().startswith(("pine", "#")):
                    clean_code = block.replace("pine", "").replace("pinescript", "").strip()
                    if clean_code and not clean_code.startswith("#"):
                        return clean_code
        
        # 코드 블록이 없는 경우 전체 응답 반환
        return modified_code
        
    except Exception as e:
        print(f"AI 수정 오류: {e}")
        return original_code + f"\n\n// AI 수정 실패: {e}"

def save_modification(strategy_code, modified_code, webhook_data, strategy_dir):
    """
    수정된 전략 코드와 메타데이터를 저장합니다.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 수정된 전략 코드 저장
    strategy_dir_path = Path(strategy_dir)
    modified_file = strategy_dir_path / f"modified_{timestamp}.pine"
    with open(modified_file, 'w') as file:
        file.write(modified_code)
    
    # 메타데이터 저장
    metadata = {
        "timestamp": timestamp,
        "original_strategy": "current.pine",
        "modified_strategy": f"modified_{timestamp}.pine",
        "webhook_data": webhook_data,
        "performance_before": webhook_data.get("performance", {}),
        "modification_summary": webhook_data.get("suggested_improvements", "")
    }
    
    metadata_file = strategy_dir_path / f"metadata_{timestamp}.json"
    with open(metadata_file, 'w') as file:
        json.dump(metadata, file, indent=4)
    
    return {
        "timestamp": timestamp,
        "modified_file": str(modified_file),
        "metadata_file": str(metadata_file)
    }

def test_analysis(strategy_code, sample_webhook_data):
    """
    테스트 분석을 위한 메서드
    """
    return generate_modified_script(strategy_code, sample_webhook_data)

def parse_response(response_text: str) -> dict:
    """
    LLM의 응답을 파싱하여 설명과 수정된 코드를 분리합니다.
    
    Args:
        response_text (str): LLM의 전체 응답 텍스트
        
    Returns:
        dict: 설명과 수정된 코드를 포함한 딕셔너리
    """
    # 코드 블록을 찾기 위한 정규식
    code_pattern = r"```(?:pine)?(.*?)```"
    
    # 코드 블록 추출
    code_matches = re.findall(code_pattern, response_text, re.DOTALL)
    
    if not code_matches:
        return {
            "explanation": response_text,
            "modified_code": "// 코드를 추출할 수 없었습니다. 원본 응답:\n" + response_text
        }
    
    # 수정된 코드 (마지막 코드 블록 사용)
    modified_code = code_matches[-1].strip()
    
    # 설명 부분 (첫 번째 코드 블록 이전의 모든 텍스트)
    first_code_block_start = response_text.find("```")
    explanation = response_text[:first_code_block_start].strip() if first_code_block_start > 0 else ""
    
    return {
        "explanation": explanation,
        "modified_code": modified_code
    }

def save_modified_code(modified_code: str, filename: str = "modified.pine") -> str:
    """
    수정된 코드를 저장합니다.
    
    Args:
        modified_code (str): 수정된 Pine Script 코드
        filename (str, optional): 저장할 파일명. 기본값은 "modified.pine"
        
    Returns:
        str: 저장된 파일의 경로
    """
    # Vercel 환경의 경우 /tmp 디렉토리 사용
    if os.environ.get("VERCEL"):
        save_dir = "/tmp/storage/strategies"
    else:
        save_dir = "storage/strategies"
    
    os.makedirs(save_dir, exist_ok=True)
    
    filepath = os.path.join(save_dir, filename)
    
    with open(filepath, "w") as f:
        f.write(modified_code)
    
    return filepath
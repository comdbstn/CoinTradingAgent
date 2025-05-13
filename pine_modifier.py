# pine_modifier.py
import os
import re
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 키 확인 및 적절한 모듈 선택
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    use_mock = False
    print("실제 OpenAI API를 사용합니다.")
else:
    from mock_openai import ChatCompletion
    use_mock = True
    print("API 키가 없어 모의 OpenAI API를 사용합니다.")

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

def generate_modified_script(original_code: str, recent_log: str) -> dict:
    """
    원본 전략 코드와 최근 거래 로그를 기반으로 LLM을 통해 수정된 코드를 생성합니다.
    
    Args:
        original_code (str): Pine Script 원본 코드
        recent_log (str): 최근 거래 로그 (JSON 형식)
        
    Returns:
        dict: 설명과 수정된 코드를 포함한 딕셔너리
    """
    prompt = load_prompt_template().format(
        original_code=original_code,
        recent_log=recent_log
    )

    # API 호출 (실제 또는 모의)
    if use_mock:
        response = ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        result = response["choices"][0].message.content
    else:
        try:
            # 최신 OpenAI 클라이언트 버전 사용
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            result = response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API 호출 중 오류 발생: {str(e)}")
            # 오류 발생 시 모의 응답으로 대체
            from mock_openai import ChatCompletion
            response = ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            result = response["choices"][0].message.content

    return parse_response(result)

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
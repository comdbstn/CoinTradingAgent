# pine_modifier.py
import os
import re
import json
import datetime
import traceback
from pathlib import Path
from dotenv import load_dotenv
import openai
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("pine_modifier")

# 환경 변수 로드
load_dotenv()

# API 키 확인 및 적절한 모듈 선택
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    use_mock = False
    print("실제 OpenAI API를 사용합니다.")
    openai.api_key = api_key
else:
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

def load_strategy_code(strategy_file):
    """전략 코드 파일을 로드합니다."""
    with open(strategy_file, 'r') as file:
        return file.read()

def generate_modified_script(original_code, webhook_data):
    """
    웹훅 데이터와 원본 전략 코드를 기반으로 OpenAI API를 사용하여 수정된 코드를 생성합니다.
    """
    if not api_key:
        logger.warning("API 키가 없어 코드 수정을 건너뜁니다.")
        return original_code + "\n\n// OpenAI API 키가 설정되지 않아 코드 수정이 불가능합니다."
    
    try:
        logger.debug("전략 코드 수정 시작")
        
        # 원본 코드에서 전략 이름 추출
        strategy_name = "Unknown Strategy"
        for line in original_code.split("\n"):
            if 'strategy("' in line:
                start_idx = line.find('strategy("') + len('strategy("')
                end_idx = line.find('"', start_idx)
                if start_idx >= 0 and end_idx >= 0:
                    strategy_name = line[start_idx:end_idx]
                    break
        logger.debug(f"원본 전략 이름: {strategy_name}")
        
        # 웹훅 데이터 구성
        trading_problem = webhook_data.get("trading_problem", "전략 최적화가 필요합니다.")
        suggested_improvements = webhook_data.get("suggested_improvements", "전략의 매개변수를 현재 시장 상황에 맞게 조정하세요.")
        
        # 성과 데이터 추출
        performance = webhook_data.get("performance", {})
        profit_factor = performance.get("profit_factor", "불명")
        win_rate = performance.get("win_rate", "불명")
        avg_profit = performance.get("avg_profit", "불명")
        max_drawdown = performance.get("max_drawdown", "불명")
        
        # 최근 트레이드 데이터
        recent_trades = webhook_data.get("recent_trades", [])
        trades_summary = ""
        if recent_trades:
            trades_summary = f"최근 {len(recent_trades)}개 거래 요약:\n"
            for i, trade in enumerate(recent_trades):
                direction = trade.get("direction", "불명")
                result = trade.get("result", "불명")
                profit_pct = trade.get("profit_pct", "불명")
                trades_summary += f"- 거래 {i+1}: {direction}, 결과: {result}, 수익률: {profit_pct}%\n"
        
        logger.debug(f"웹훅 데이터 처리 완료, OpenAI API 요청 준비")
        
        # API 요청을 위한 프롬프트 구성
        prompt = f"""
당신은 Pine Script 전략 코드 최적화 전문가입니다. 다음 트레이딩 전략 코드를 분석하고 개선해야 합니다.

## 원본 전략: {strategy_name}
```pine
{original_code}
```

## 전략 성과:
- 수익 팩터: {profit_factor}
- 승률: {win_rate}
- 평균 수익: {avg_profit}
- 최대 낙폭: {max_drawdown}

## 문제점:
{trading_problem}

## 제안된 개선사항:
{suggested_improvements}

{trades_summary}

위 정보를 바탕으로 전략 코드를 개선해주세요. 다음 규칙을 따라주세요:
1. 전략의 핵심 로직은 유지하되, 매개변수와 조건을 최적화하세요.
2. 추가 기능이나 지표를 통합하여 성능을 향상시킬 수 있습니다.
3. 코드는 Pine Script 문법에 맞게 작성해야 합니다.
4. 코드 설명 주석을 추가하여 변경 사항을 명확히 해주세요.
5. 전체 Pine Script 코드만 반환하세요.

개선된 Pine Script 코드:
"""
        
        # 모의 응답 모드 (디버깅용)
        if os.environ.get("DEBUG_MODE") == "true":
            logger.info("디버그 모드: 모의 응답 반환")
            return original_code + "\n\n// 이것은 디버그 모드의 모의 응답입니다. OpenAI API가 호출되지 않았습니다."
        
        logger.debug("OpenAI API 요청 시작")
        
        # OpenAI API 호출
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 Pine Script와 트레이딩 전략에 전문적인 지식을 갖춘 AI 조수입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # 수정된 코드 추출
            modified_code = response.choices[0].message.content.strip()
            logger.debug(f"OpenAI API 응답 수신: {len(modified_code)} 문자")
            
            # 코드 블록이 있으면 추출
            if "```pine" in modified_code:
                start_idx = modified_code.find("```pine") + 7
                end_idx = modified_code.find("```", start_idx)
                if start_idx >= 0 and end_idx >= 0:
                    modified_code = modified_code[start_idx:end_idx].strip()
                    logger.debug("```pine 코드 블록에서 코드 추출")
            elif "```" in modified_code:
                start_idx = modified_code.find("```") + 3
                end_idx = modified_code.find("```", start_idx)
                if start_idx >= 0 and end_idx >= 0:
                    modified_code = modified_code[start_idx:end_idx].strip()
                    logger.debug("``` 코드 블록에서 코드 추출")
            
            logger.info("전략 코드 수정 완료")
            return modified_code
            
        except Exception as api_error:
            logger.error(f"OpenAI API 호출 오류: {str(api_error)}")
            logger.error(traceback.format_exc())
            # 오류 발생 시 원본 코드에 오류 메시지 추가
            return original_code + f"\n\n// OpenAI API 오류가 발생했습니다: {str(api_error)}"
    
    except Exception as e:
        logger.error(f"전략 코드 수정 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())
        return original_code + f"\n\n// 코드 수정 중 오류 발생: {str(e)}"

def generate_mock_response(original_code, analysis, suggestions):
    """
    API 키가 없거나 OpenAI API 호출에 실패한 경우 모의 응답을 생성합니다.
    """
    # 기본 RSI 값 변경
    if "RSI" in original_code and "과매도 기준" in original_code:
        modified_code = original_code.replace("rsiOversold = input(33", "rsiOversold = input(28")
        modified_code = modified_code.replace("rsiOversold = input(30", "rsiOversold = input(28")
        
        # 이익 실현 비율 변경
        if "이익 실현 %" in modified_code:
            modified_code = modified_code.replace("takeProfitPct = input(5.0", "takeProfitPct = input(7.0")
            
        # 볼린저 밴드 활성화
        if "useBollingerBands = input(false" in modified_code:
            modified_code = modified_code.replace("useBollingerBands = input(false", "useBollingerBands = input(true")
            
        # 트레일링 스탑 추가
        if "useTrailingStop" not in modified_code and "strateg" in modified_code:
            # 기존 변수 뒤에 추가
            if "bbMultiplier" in modified_code:
                modified_code = modified_code.replace("bbMultiplier = input(2.0", 
                    "bbMultiplier = input(2.0"
                    + "\nuseTrailingStop = input(true, title=\"트레일링 스탑 사용\", tooltip=\"트레일링 스탑을 적용합니다.\")"
                    + "\ntrailingStopPct = input(2.0, title=\"트레일링 스탑 %\", tooltip=\"트레일링 스탑 비율입니다.\")")
            
        # 트레일링 스탑 로직 추가
        if "strategy.exit" in modified_code and "trail_points" not in modified_code:
            modified_code = modified_code.replace("strategy.exit(\"TP_SL_Long\", \"RSI_Long\", profit=close * takeProfitPct / 100, loss=close * stopLossPct / 100)",
                "if (useTrailingStop)\n    strategy.exit(\"TP_TS_Long\", \"RSI_Long\", profit=close * takeProfitPct / 100, loss=close * stopLossPct / 100, trail_points=close * trailingStopPct / 100)\nelse\n    strategy.exit(\"TP_SL_Long\", \"RSI_Long\", profit=close * takeProfitPct / 100, loss=close * stopLossPct / 100)")
            
            modified_code = modified_code.replace("strategy.exit(\"TP_SL_Short\", \"RSI_Short\", profit=close * takeProfitPct / 100, loss=close * stopLossPct / 100)",
                "if (useTrailingStop)\n    strategy.exit(\"TP_TS_Short\", \"RSI_Short\", profit=close * takeProfitPct / 100, loss=close * stopLossPct / 100, trail_points=close * trailingStopPct / 100)\nelse\n    strategy.exit(\"TP_SL_Short\", \"RSI_Short\", profit=close * takeProfitPct / 100, loss=close * stopLossPct / 100)")
        
        # 전략 이름 변경
        modified_code = modified_code.replace("strategy(\"Simple RSI Strategy", "strategy(\"Optimized RSI Strategy")
        
        # 주석 추가
        modified_code += "\n\n// 모의 API를 통해 자동 생성된 코드:\n"
        modified_code += "// 1. RSI 과매도 기준을 28로 낮춤\n"
        modified_code += "// 2. 이익실현 비율을 7%로 높임\n"
        modified_code += "// 3. 볼린저 밴드를 활성화하여 더 정확한 매도 시점 제공\n"
        modified_code += "// 4. 2% 트레일링 스탑 적용하여 추세 변화에 유연하게 대응\n"
        
        return modified_code
    else:
        # RSI 관련 코드가 없는 경우 원본 코드 반환
        return original_code + "\n\n// 모의 API: 코드를 수정할 수 없습니다. 분석 요약:\n// " + analysis

def save_modification(strategy_code, modified_code, webhook_data, strategy_dir):
    """
    수정된 전략 코드와 메타데이터를 저장합니다.
    """
    try:
        logger.debug("수정된 코드 저장 시작")
        
        # 타임스탬프 생성
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 디렉토리 확인 및 생성
        try:
            os.makedirs(strategy_dir, exist_ok=True)
            logger.debug(f"디렉토리 생성 완료: {strategy_dir}")
        except Exception as dir_error:
            logger.error(f"디렉토리 생성 중 오류: {str(dir_error)}")
            logger.error(traceback.format_exc())
            raise
        
        # 수정된 코드 파일명
        modified_file = os.path.join(strategy_dir, f"modified_{timestamp}.pine")
        
        # 메타데이터 파일명
        metadata_file = os.path.join(strategy_dir, f"metadata_{timestamp}.json")
        
        logger.debug(f"파일 경로 설정 - 수정된 코드: {modified_file}, 메타데이터: {metadata_file}")
        
        # 원본 코드에서 전략 이름 추출
        original_strategy = "Unknown Strategy"
        for line in strategy_code.split("\n"):
            if 'strategy("' in line:
                start_idx = line.find('strategy("') + len('strategy("')
                end_idx = line.find('"', start_idx)
                if start_idx >= 0 and end_idx >= 0:
                    original_strategy = line[start_idx:end_idx]
                    break
        
        # 수정된 코드에서 전략 이름 추출
        modified_strategy = "Modified Strategy"
        for line in modified_code.split("\n"):
            if 'strategy("' in line:
                start_idx = line.find('strategy("') + len('strategy("')
                end_idx = line.find('"', start_idx)
                if start_idx >= 0 and end_idx >= 0:
                    modified_strategy = line[start_idx:end_idx]
                    break
        
        logger.debug(f"전략 이름 추출 - 원본: {original_strategy}, 수정됨: {modified_strategy}")
        
        # 수정 요약 생성
        modification_summary = webhook_data.get("suggested_improvements", "전략 코드가 최적화되었습니다.")
        
        # 메타데이터 생성
        metadata = {
            "timestamp": timestamp,
            "original_strategy": original_strategy,
            "modified_strategy": modified_strategy,
            "performance_before": webhook_data.get("performance", {}),
            "recent_trades": webhook_data.get("recent_trades", []),
            "trading_problem": webhook_data.get("trading_problem", ""),
            "modification_summary": modification_summary
        }
        
        logger.debug("메타데이터 생성 완료")
        
        # 파일 저장
        try:
            with open(modified_file, 'w') as f:
                f.write(modified_code)
            logger.debug(f"수정된 코드 저장 완료: {modified_file}")
                
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=4)
            logger.debug(f"메타데이터 저장 완료: {metadata_file}")
                
            return {
                "timestamp": timestamp,
                "modified_file": modified_file,
                "metadata_file": metadata_file
            }
        except Exception as file_error:
            logger.error(f"파일 저장 중 오류: {str(file_error)}")
            logger.error(traceback.format_exc())
            raise
    except Exception as e:
        logger.error(f"수정된 코드 저장 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "error": f"수정된 코드 저장 중 오류: {str(e)}"
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
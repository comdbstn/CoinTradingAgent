import os
import json
import openai
import datetime
from pathlib import Path
import logging

# 로깅 설정
logger = logging.getLogger("api.pine_modifier")

# OpenAI API 키 설정
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    openai.api_key = api_key
    logger.info("OpenAI API 키가 설정되었습니다.")
else:
    logger.warning("OpenAI API 키가 설정되지 않았습니다.")

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
        # return original_code + "\n\n// 이것은 모의 응답입니다. OpenAI API가 호출되지 않았습니다."
        
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
            # 오류 발생 시 원본 코드에 오류 메시지 추가
            return original_code + f"\n\n// OpenAI API 오류가 발생했습니다: {str(api_error)}"
    
    except Exception as e:
        logger.error(f"전략 코드 수정 중 오류 발생: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        logger.error(tb)
        return original_code + f"\n\n// 코드 수정 중 오류 발생: {str(e)}"

def test_analysis(strategy_code, webhook_data):
    """
    전략 코드와 웹훅 데이터를 이용한 테스트 분석을 수행합니다.
    """
    logger.debug("테스트 분석 시작")
    result = generate_modified_script(strategy_code, webhook_data)
    logger.debug("테스트 분석 완료")
    return result

def save_modification(original_code, modified_code, webhook_data, strategy_dir):
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
            raise
        
        # 수정된 코드 파일명
        modified_file = os.path.join(strategy_dir, f"modified_{timestamp}.pine")
        
        # 메타데이터 파일명
        metadata_file = os.path.join(strategy_dir, f"metadata_{timestamp}.json")
        
        logger.debug(f"파일 경로 설정 - 수정된 코드: {modified_file}, 메타데이터: {metadata_file}")
        
        # 원본 코드에서 전략 이름 추출
        original_strategy = "Unknown Strategy"
        for line in original_code.split("\n"):
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
            raise
    except Exception as e:
        logger.error(f"수정된 코드 저장 중 오류: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        logger.error(tb)
        raise Exception(f"수정된 코드 저장 중 오류: {str(e)}") 
import os
import json
import openai
import datetime
from pathlib import Path

# OpenAI API 키 설정
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    openai.api_key = api_key

def generate_modified_script(original_code, webhook_data):
    """
    웹훅 데이터와 원본 전략 코드를 기반으로 OpenAI API를 사용하여 수정된 코드를 생성합니다.
    """
    if not api_key:
        return original_code + "\n\n// OpenAI API 키가 설정되지 않아 코드 수정이 불가능합니다."
    
    try:
        # 원본 코드에서 전략 이름 추출
        strategy_name = "Unknown Strategy"
        for line in original_code.split("\n"):
            if 'strategy("' in line:
                start_idx = line.find('strategy("') + len('strategy("')
                end_idx = line.find('"', start_idx)
                if start_idx >= 0 and end_idx >= 0:
                    strategy_name = line[start_idx:end_idx]
                    break
        
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
        
        # OpenAI API 호출
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
        
        # 코드 블록이 있으면 추출
        if "```pine" in modified_code:
            start_idx = modified_code.find("```pine") + 7
            end_idx = modified_code.find("```", start_idx)
            if start_idx >= 0 and end_idx >= 0:
                modified_code = modified_code[start_idx:end_idx].strip()
        elif "```" in modified_code:
            start_idx = modified_code.find("```") + 3
            end_idx = modified_code.find("```", start_idx)
            if start_idx >= 0 and end_idx >= 0:
                modified_code = modified_code[start_idx:end_idx].strip()
        
        return modified_code
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return original_code + f"\n\n// 코드 수정 중 오류 발생: {str(e)}"

def test_analysis(strategy_code, webhook_data):
    """
    전략 코드와 웹훅 데이터를 이용한 테스트 분석을 수행합니다.
    """
    return generate_modified_script(strategy_code, webhook_data)

def save_modification(original_code, modified_code, webhook_data, strategy_dir):
    """
    수정된 전략 코드와 메타데이터를 저장합니다.
    """
    # 타임스탬프 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 디렉토리 확인 및 생성
    os.makedirs(strategy_dir, exist_ok=True)
    
    # 수정된 코드 파일명
    modified_file = os.path.join(strategy_dir, f"modified_{timestamp}.pine")
    
    # 메타데이터 파일명
    metadata_file = os.path.join(strategy_dir, f"metadata_{timestamp}.json")
    
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
    
    # 파일 저장
    try:
        with open(modified_file, 'w') as f:
            f.write(modified_code)
            
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)
            
        return {
            "timestamp": timestamp,
            "modified_file": modified_file,
            "metadata_file": metadata_file
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"수정된 코드 저장 중 오류: {str(e)}") 
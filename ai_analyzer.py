#!/usr/bin/env python3
"""
AI Analyzer for Azure Pipeline
Analyzes issue text for Chinese content using AI API
"""

import json
import sys
import os
import re
import requests


def clean_html_text(text):
    """
    Remove HTML tags and entities from text
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', ' ', text)
    # Replace HTML entities
    text = re.sub(r'&nbsp;', ' ', text)
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_prompt(issue_id, clean_text):
    """
    Generate the prompt for AI analysis
    """
    prompt = f"""あなたは日本語レビューアです。

Issue ID:
{issue_id}

対象テキスト:
{clean_text}

■タスク1: 中国語判定
対象テキストに簡体字中国語（中国大陸で使用される中国語の文章）が含まれているか判定してください。

判定ルール:
- ファイル名、パス、URLなどの技術的なテキストは判定対象外（例：ItemInfo.csv、config.xml）
- 日本語の漢字（例：内容、入力、画面、変更、エラー）は中国語ではありません
- 英数字、記号、コード表記は判定対象外です
- 繁体字中文は判定対象外です
- 簡体字の自然言語文章のみが対象です

■タスク2: 日語最適化と内容抽出
下記の手順に従って処理してください：

ステップ1: 日語最適化
対象テキストの日語を以下のように最適化してください：
- 日語の誤字・誤りを修正する
- 表現が不十分な部分を改善する
- 商務礼貌用語に修正する
- 【重要】第一人称視点は変更しないこと（「私」「我が」など）

ステップ2: 内容抽出と背景・質問・提案の特定
対象テキストから以下の3つを **ユーザーの内容に基づいて** 抽出してください：
- 背景：ユーザーが述べている問題の背景や原因
- 質問内容：ユーザーが提示している具体的な問題や質問
- 提案：ユーザーが既に述べている改善案や提案

【重要な制約】
- 背景、質問内容、提案は「なし」で記入しないでください
- ユーザーの内容に明確に記述されていない情報は追加しないでください
- 推測や発散的な提案は絶対にしないでください
- ユーザーが述べた内容を補完・整理するだけです

以下のJSONのみ返却してください（マークダウンやコメントは不要）：

{{
  "has_chinese": false,
  "chinese_text": [],
  "recommendation": {{
    "background": "ユーザーが述べた問題の背景・原因（ユーザーの内容から抽出のみ）",
    "question_content": "ユーザーが述べた具体的な問題や質問（ユーザーの内容から抽出のみ）",
    "proposal": "ユーザーが述べた改善案や提案（ユーザーの内容から抽出のみ）"
  }}
}}"""
    
    return prompt


def call_ai_api(prompt, api_url, max_tokens=500):
    """
    Call the AI API to analyze the prompt
    """
    try:
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        
        result = response.json()
        print(f"DEBUG: Full API Response: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        
        # Try to get 'response' field first, then fall back to the result itself
        ai_result = result.get("response", None)
        
        # If 'response' field is not present, check if the result itself is a string
        if ai_result is None:
            if isinstance(result, dict):
                # If it's a dict with has_chinese field, it's already the parsed response
                if "has_chinese" in result:
                    ai_result = json.dumps(result)
                else:
                    print(f"Error: Unexpected API response structure: {result}", file=sys.stderr)
                    sys.exit(1)
            elif isinstance(result, str):
                ai_result = result
            else:
                print(f"Error: Unexpected response type: {type(result)}", file=sys.stderr)
                sys.exit(1)
        
        # Ensure ai_result is a string
        if not isinstance(ai_result, str):
            ai_result = json.dumps(ai_result)
        
        return ai_result
    
    except requests.exceptions.RequestException as e:
        print(f"Error calling AI API: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from API: {e}", file=sys.stderr)
        sys.exit(1)


def parse_ai_response(ai_response_text):
    """
    Parse AI response and extract JSON
    """
    try:
        # Ensure input is a string
        if not isinstance(ai_response_text, str):
            print(f"Error: Response is not a string, got type: {type(ai_response_text)}", file=sys.stderr)
            print(f"Response value: {ai_response_text}", file=sys.stderr)
            sys.exit(1)
        
        # Try to parse directly as JSON first
        try:
            result = json.loads(ai_response_text)
            return result
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', ai_response_text)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return result
            else:
                print(f"Error: Could not find JSON in response: {ai_response_text}", file=sys.stderr)
                sys.exit(1)
    
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        print(f"Response text: {ai_response_text}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to analyze issue text
    """
    # Get environment variables
    issue_id = os.getenv("WORK_ITEM_ID", "")
    question_text = os.getenv("QUESTION", "")
    api_url = os.getenv("AI_API_URL", "https://devtoolbox-api.devtoolbox-api.workers.dev/ai/generate")
    
    if not issue_id or not question_text:
        print("Error: WORK_ITEM_ID and QUESTION environment variables must be set", file=sys.stderr)
        sys.exit(1)
    
    print("=" * 40)
    print(f"Issue ID: {issue_id}")
    print(f"Original Question:\n{question_text}")
    print("=" * 40)
    
    # Clean the text
    clean_text = clean_html_text(question_text)
    print(f"Cleaned Text:\n{clean_text}")
    print("=" * 40)
    
    # Generate prompt
    prompt = generate_prompt(issue_id, clean_text)
    print(f"Generated Prompt:\n{prompt}")
    print("=" * 40)
    
    # Call AI API
    print("Calling AI API...")
    try:
        ai_response = call_ai_api(prompt, api_url)
        print(f"DEBUG: AI Response (type: {type(ai_response).__name__}): {ai_response[:500]}", file=sys.stderr)
    except Exception as e:
        print(f"Error calling AI API: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Parse response
    try:
        result = parse_ai_response(ai_response)
    except Exception as e:
        print(f"Error parsing AI response: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Extract results
    has_chinese = result.get("has_chinese", False)
    chinese_text = result.get("chinese_text", [])
    recommendation = result.get("recommendation", {
        "background": "なし",
        "question_content": "なし",
        "proposal": "なし"
    })
    
    print(f"Has Chinese: {has_chinese}")
    print(f"Chinese Text: {json.dumps(chinese_text)}")
    print(f"Recommendation: {json.dumps(recommendation, ensure_ascii=False)}")
    
    # Output as Azure Pipeline variables (use JSON encoding for multi-line values)
    print(f"##vso[task.setvariable variable=HasChinese]{json.dumps(has_chinese).lower()}")
    print(f"##vso[task.setvariable variable=ChineseText]{json.dumps(chinese_text)}")
    # Use JSON encoding to preserve multi-line content with special characters
    background = recommendation.get('background', 'なし')
    question_content = recommendation.get('question_content', 'なし')
    proposal = recommendation.get('proposal', 'なし')
    print(f"##vso[task.setvariable variable=RecommendationBackground]{json.dumps(background)}")
    print(f"##vso[task.setvariable variable=RecommendationQuestionContent]{json.dumps(question_content)}")
    print(f"##vso[task.setvariable variable=RecommendationProposal]{json.dumps(proposal)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

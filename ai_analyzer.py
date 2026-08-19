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

対象テキストに中国語が含まれているか判定してください。

ルール:
- 中国語が含まれている場合 has_chinese=true
- 中国語がない場合 has_chinese=false
- 中国語箇所を chinese_text に格納する

以下のJSONのみ返却してください。

{{
  "has_chinese": false,
  "chinese_text": []
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
        ai_result = result.get("response", "")
        
        return ai_result
    
    except requests.exceptions.RequestException as e:
        print(f"Error calling AI API: {e}", file=sys.stderr)
        sys.exit(1)


def parse_ai_response(ai_response_text):
    """
    Parse AI response and extract JSON
    """
    try:
        # Try to extract JSON from response
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
    ai_response = call_ai_api(prompt, api_url)
    
    # Parse response
    result = parse_ai_response(ai_response)
    
    # Extract results
    has_chinese = result.get("has_chinese", False)
    chinese_text = result.get("chinese_text", [])
    
    print(f"Has Chinese: {has_chinese}")
    print(f"Chinese Text: {json.dumps(chinese_text)}")
    
    # Output as Azure Pipeline variables
    print(f"##vso[task.setvariable variable=HasChinese]{json.dumps(has_chinese).lower()}")
    print(f"##vso[task.setvariable variable=ChineseText]{json.dumps(chinese_text)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

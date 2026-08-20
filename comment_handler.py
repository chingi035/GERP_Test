#!/usr/bin/env python3
"""
Comment Handler for Azure Pipeline
Adds AI analysis result comments to work items
"""

import json
import sys
import os
import requests
from typing import Optional


def get_auth_headers(access_token: str) -> dict:
    """
    Generate authorization headers for Azure DevOps API
    """
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def generate_comment(has_chinese: bool, chinese_text: Optional[list] = None, 
                     background: str = "なし", question_content: str = "なし", 
                     proposal: str = "なし") -> str:
    """
    Generate comment text based on analysis result
    Uses HTML <br/> tags for line breaks to ensure proper formatting in Azure DevOps
    """
    lines = []
    
    # Add Chinese detection result
    lines.append("【AIチェック結果】")
    
    if has_chinese:
        lines.append("❌ 中国語が検出されました")
        lines.append("")
        lines.append("検出内容:")
        
        # Format chinese_text for display
        if isinstance(chinese_text, str):
            try:
                chinese_text = json.loads(chinese_text)
            except (json.JSONDecodeError, TypeError):
                chinese_text = [chinese_text]
        
        if not isinstance(chinese_text, list):
            chinese_text = [chinese_text]
        
        if chinese_text:
            for item in chinese_text:
                lines.append(f"- {str(item)}")
        else:
            lines.append("N/A")
    else:
        lines.append("✅ 中国語は検出されませんでした")
    
    # Add recommendation template with HTML line breaks
    lines.append("")
    lines.append("")
    lines.append("以下の点について改善をご検討いただけますと幸いです。")
    lines.append("")
    lines.append("背景：")
    lines.append(str(background))
    lines.append("")
    lines.append("質問内容：")
    lines.append(str(question_content))
    lines.append("")
    lines.append("提案：")
    lines.append(str(proposal))
    
    # Join with HTML <br/> tags for Azure DevOps compatibility
    result = "<br/>".join(lines)
    return result
    lines.append("")
    lines.append(str(question_content))
    lines.append("")
    lines.append("**提案：**")
    lines.append("")
    lines.append(str(proposal))
    
    return "\n".join(lines)


def add_comment_to_workitem(
    work_item_id: str,
    comment: str,
    collection_uri: str,
    project: str,
    access_token: str,
    api_version: str = "7.1-preview.3"
) -> bool:
    """
    Add comment to Azure DevOps work item via REST API
    """
    try:
        url = f"{collection_uri}{project}/_apis/wit/workItems/{work_item_id}/comments?api-version={api_version}"
        
        body = {
            "text": comment
        }
        
        headers = get_auth_headers(access_token)
        
        response = requests.post(
            url,
            json=body,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        
        print(f"Comment successfully added to work item {work_item_id}")
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"Error adding comment to work item: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to handle comment posting
    """
    # Get environment variables
    work_item_id = os.getenv("WORK_ITEM_ID", "")
    has_chinese_str = os.getenv("HAS_CHINESE", "false").lower()
    chinese_text = os.getenv("CHINESE_TEXT", "[]")
    background_raw = os.getenv("RECOMMENDATION_BACKGROUND", json.dumps("なし"))
    question_content_raw = os.getenv("RECOMMENDATION_QUESTION_CONTENT", json.dumps("なし"))
    proposal_raw = os.getenv("RECOMMENDATION_PROPOSAL", json.dumps("なし"))
    
    collection_uri = os.getenv("SYSTEM_COLLECTION_URI", "")
    project = os.getenv("SYSTEM_TEAM_PROJECT", "")
    access_token = os.getenv("SYSTEM_ACCESS_TOKEN", "")
    
    # Decode JSON-encoded environment variables
    try:
        # Try to parse as JSON first (handles both quoted and unquoted strings)
        if background_raw.startswith('"'):
            background = json.loads(background_raw)
        else:
            background = background_raw
            
        if question_content_raw.startswith('"'):
            question_content = json.loads(question_content_raw)
        else:
            question_content = question_content_raw
            
        if proposal_raw.startswith('"'):
            proposal = json.loads(proposal_raw)
        else:
            proposal = proposal_raw
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Warning: Failed to parse JSON-encoded variables: {e}", file=sys.stderr)
        background = background_raw
        question_content = question_content_raw
        proposal = proposal_raw
    
    # Validate required variables
    required_vars = [
        ("WORK_ITEM_ID", work_item_id),
        ("SYSTEM_COLLECTION_URI", collection_uri),
        ("SYSTEM_TEAM_PROJECT", project),
        ("SYSTEM_ACCESS_TOKEN", access_token),
    ]
    
    missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}", file=sys.stderr)
        sys.exit(1)
    
    # Convert string to boolean
    has_chinese = has_chinese_str == "true"
    
    print("=" * 40)
    print(f"Work Item ID: {work_item_id}")
    print(f"Has Chinese: {has_chinese}")
    print(f"Chinese Text: {chinese_text}")
    print(f"Background: {background}")
    print(f"Question Content: {question_content}")
    print(f"Proposal: {proposal}")
    print("=" * 40)
    
    # Generate comment
    comment = generate_comment(has_chinese, chinese_text, background, question_content, proposal)
    print(f"Generated Comment:\n{comment}")
    print("=" * 40)
    
    # Add comment to work item
    print("Adding comment to work item...")
    add_comment_to_workitem(
        work_item_id=work_item_id,
        comment=comment,
        collection_uri=collection_uri,
        project=project,
        access_token=access_token
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

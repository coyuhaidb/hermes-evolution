"""飞书消息推送 — push_feishu.py 和 monitor.py 共用模块"""

import json
import os
import subprocess
import sys
import time

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.config import FEISHU_CHAT_ID, LARK_CLI


def send_markdown(markdown_text, max_retries=2):
    """发送 Markdown 消息到飞书群，失败自动重试"""
    cmd = [
        LARK_CLI, "im", "+messages-send",
        "--chat-id", FEISHU_CHAT_ID,
        "--markdown", markdown_text,
    ]

    last_error = ""
    for attempt in range(1 + max_retries):
        if attempt > 0:
            wait = 2 ** attempt
            print(f"  ⏳ 第 {attempt} 次重试（等待 {wait}s）...")
            time.sleep(wait)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            last_error = "超时"
            continue
        except Exception as e:
            last_error = str(e)
            continue

        if result.returncode != 0:
            last_error = result.stderr[:200]
            continue

        try:
            resp = json.loads(result.stdout)
            if resp.get("ok"):
                return True, resp["data"]["message_id"]
            last_error = str(resp)
        except json.JSONDecodeError:
            last_error = result.stdout[:200]

    return False, last_error

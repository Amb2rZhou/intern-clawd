"""飞书 API 工具函数（共享）"""

import json
import subprocess
from pathlib import Path

CONFIG_ENV = Path.home() / ".claude-to-im" / "config.env"


def load_feishu_config():
    if not CONFIG_ENV.exists():
        return None, None
    config = {}
    for line in CONFIG_ENV.read_text().strip().split("\n"):
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            config[k.strip()] = v.strip()
    return config.get("CTI_FEISHU_APP_ID"), config.get("CTI_FEISHU_APP_SECRET"), config.get("CTI_FEISHU_CHAT_NAME", "")


def curl_json(method, url, headers=None, data=None):
    cmd = ["curl", "-s", "-X", method, url]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
    if data:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return json.loads(result.stdout) if result.stdout else {}
    except Exception as e:
        print(f"[feishu] curl 失败: {e}")
        return {}


def send_feishu_message(text, tag="feishu"):
    app_id, app_secret, chat_name = load_feishu_config()
    if not app_id or not app_secret:
        print(f"[{tag}] 未找到飞书凭证")
        return False

    resp = curl_json("POST", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                     data={"app_id": app_id, "app_secret": app_secret})
    token = resp.get("tenant_access_token")
    if not token:
        print(f"[{tag}] 获取 token 失败")
        return False

    resp = curl_json("GET", "https://open.feishu.cn/open-apis/im/v1/chats?page_size=20",
                     headers={"Authorization": f"Bearer {token}"})
    items = resp.get("data", {}).get("items", [])
    if not items:
        print(f"[{tag}] 未找到群聊")
        return False

    # 按群名匹配（config.env 里设 CTI_FEISHU_CHAT_NAME），没设就用第一个
    chat_id = items[0]["chat_id"]
    if chat_name:
        for item in items:
            if chat_name in item.get("name", ""):
                chat_id = item["chat_id"]
                break
    content = json.dumps({"text": text})
    resp = curl_json("POST", "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
                     headers={"Authorization": f"Bearer {token}"},
                     data={"receive_id": chat_id, "msg_type": "text", "content": content})

    if resp.get("code") == 0:
        print(f"[{tag}] 已发送到飞书")
        return True
    else:
        print(f"[{tag}] 发送失败: {resp}")
        return False

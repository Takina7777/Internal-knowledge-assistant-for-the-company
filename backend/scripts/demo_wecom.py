"""企业微信无真实环境演示：模拟企微服务器回调，验证完整链路
（GET URL 验证用官方样例向量；POST 消息解密 → handler → 假客户端推送）。
全程不请求真实企微 API。

用法（在 backend 目录下）：
    .venv\\Scripts\\python scripts\\demo_wecom.py
预期：
    [1] GET  /api/v1/wecom/callback（官方样例）-> 200 + 1616140317555161061
    [2] POST /api/v1/wecom/callback（加密消息）-> 200 + success
    [3] handler 收到问题、假推送客户端收到回复文本
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# 官方样例的 Token / EncodingAESKey（43 位）；corpid 必须与官方向量一致
TOKEN = "QDG6eK"
AES_KEY = "jWmYm7qr5nMoAUwZRjGtBxmz3KA1tkAj3ykkR6q2B2C"
CORP_ID = "wx5823bf96d3bd56c7"

# 模拟"已配置"环境（必须在 import app.* 之前设置）
os.environ["WECOM_CORP_ID"] = CORP_ID
os.environ["WECOM_AGENT_ID"] = "1000002"
os.environ["WECOM_SECRET"] = "fake-secret-for-demo"
os.environ["WECOM_TOKEN"] = TOKEN
os.environ["WECOM_AES_KEY"] = AES_KEY

from fastapi.testclient import TestClient  # noqa: E402

import app.wecom.routes as wecom_routes  # noqa: E402
from app.main import app  # noqa: E402
from app.wecom.crypto import WXBizMsgCrypt  # noqa: E402
from app.wecom.handler import WeComHandler  # noqa: E402


class FakeClient:
    """假企微客户端：不发真实请求，记录推送内容。"""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_text(self, to_user: str, content: str) -> dict:
        self.sent.append((to_user, content))
        return {"errcode": 0}


received_questions: list[str] = []


def fake_agent(question: str) -> str:
    received_questions.append(question)
    return f"已检索知识库：{question}"


def main() -> None:
    # 用假客户端 + 记录 agent 替换真实 handler（避免真实请求企微 API）
    wecom_routes._handler_instance = WeComHandler(client=FakeClient(), agent_fn=fake_agent)
    client = TestClient(app)

    print("\n== [1] GET URL 验证（官方样例向量，端到端验证验签+解密+路由）==")
    resp = client.get(
        "/api/v1/wecom/callback",
        params={
            "msg_signature": "5c45ff5e21c57e6ad56bac8758b79b1d9ac89fd3",
            "timestamp": "1409659589",
            "nonce": "263014780",
            "echostr": "P9nAzCzyDtyTWESHep1vC5X9xho/qYX3Zpb4yKa9SKld1DsH3Iyt3tP3zNdtp+4RPcs8TgAE7OaBO+FZXvnaqQ==",
        },
    )
    print(f"   状态 {resp.status_code}, 返回: {resp.text}")
    assert resp.status_code == 200 and resp.text == "1616140317555161061", "URL 验证失败"

    print("\n== [2] POST 接收消息（模拟企微服务器推送加密文本消息）==")
    crypt = WXBizMsgCrypt(TOKEN, AES_KEY, CORP_ID)
    msg_xml = (
        "<xml><ToUserName><![CDATA[ww-demo]]></ToUserName>"
        "<FromUserName><![CDATA[zhangsan]]></FromUserName>"
        "<CreateTime>1234567890</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        "<Content><![CDATA[新员工年假怎么算？]]></Content>"
        "<MsgId>1001</MsgId><AgentID><![CDATA[1000002]]></AgentID></xml>"
    )
    encrypt, msg_signature = crypt.encrypt(msg_xml, nonce="1372623149", timestamp="1409659813")
    resp = client.post(
        "/api/v1/wecom/callback",
        params={"msg_signature": msg_signature, "timestamp": "1409659813", "nonce": "1372623149"},
        content=encrypt,
        headers={"Content-Type": "text/xml"},
    )
    print(f"   状态 {resp.status_code}, 返回: {resp.text!r}")
    assert resp.status_code == 200 and resp.text == "success"

    time.sleep(0.8)  # 等后台线程处理
    print("\n== [3] handler 异步处理结果 ==")
    print("   agent 收到问题:", received_questions)
    print("   假客户端推送:", wecom_routes._handler_instance.client.sent)
    assert received_questions == ["新员工年假怎么算？"]
    assert wecom_routes._handler_instance.client.sent and "已检索知识库" in wecom_routes._handler_instance.client.sent[0][1]

    print("\n企微演示全部通过 ✅（未请求真实企微 API）")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ 演示失败: {exc}", file=sys.stderr)
        sys.exit(1)

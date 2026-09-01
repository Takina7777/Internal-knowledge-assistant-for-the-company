"""企业微信接入（已实现）。

模块结构：
  - crypto.py   WXBizMsgCrypt：回调消息 AES 加解密 + 签名校验（官方算法）
  - client.py   WeCom API 客户端：access_token 缓存、主动发消息
  - handler.py  消息解析 → 调 Agent → 异步回复（5 秒内先回 success）
  - routes.py   回调路由：GET 验证 URL / POST 接收消息（挂载于 /api/v1/wecom/callback）

启用步骤：
  1. 企业微信管理后台创建自建应用，获取 corpid / agentid / secret；
  2. 配置消息接收回调 URL（公网 HTTPS，指向 /api/v1/wecom/callback）
     与随机 Token / EncodingAESKey；
  3. 在 backend/.env 填入 WECOM_CORP_ID / WECOM_AGENT_ID / WECOM_SECRET /
     WECOM_TOKEN / WECOM_AES_KEY，重启后端即可。
"""

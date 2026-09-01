"""企业微信接入（Phase 2，暂缓实现）。

预留模块结构：
  - crypto.py   WXBizMsgCrypt：回调消息 AES 加解密 + 签名校验（官方算法）
  - client.py   WeCom API 客户端：access_token 缓存、主动发消息
  - handler.py  消息解析 → 调 agent → 异步回复（5s 内先回 success）
  - routes      回调路由：GET 校验 URL / POST 接收消息

启用步骤（见 README「企业微信机器人」）：
  1. 企业微信后台创建自建应用，获取 corpid / agentid / secret；
  2. 配置回调 URL 与 Token / EncodingAESKey（填 backend/.env 的 WECOM_*）；
  3. 实现本模块后挂载路由。
"""

# Checklist — ipinfo_api 渠道迁移

## 类结构
- [x] IpinfoApiChannel 继承 BaseChannelAdapter
- [x] channel_name = "ipinfo_api"
- [x] 构造函数接受 token（必填）和 timeout（默认 30.0），不依赖 Settings
- [x] 仅负责 Token 认证模式，无免费回退

## _validate_key
- [x] Token 为空/空白 → 抛 ChannelPermanentError（S65）
- [x] Token 有效（HTTP 200）→ 正常返回
- [x] Token 无效（HTTP 401/403）→ 抛 ChannelPermanentError（S65）
- [x] 验证请求网络错误 → 异常向上抛出（基类捕获）

## _request
- [x] 成功时返回 API JSON dict（透传所有字段）
- [x] HTTP 401/403 → ChannelPermanentError（Token 无效，S65）
- [x] HTTP 429 → ChannelPermanentError（限流，disabled=True）
- [x] requests.Timeout → ChannelError（S63）
- [x] requests.ConnectionError → ChannelError（S63）
- [x] 其他 HTTP 错误 → ChannelError + 状态码（S63）
- [x] 其他异常 → ChannelError（S64）

## fetch 调用链
- [x] 继承 BaseChannelAdapter.fetch()，无需覆盖
- [x] 返回 dict 包含 query_time（基类注入）
- [x] ChannelPermanentError 设 disabled=True
- [x] ChannelError 不改变 disabled

## validate 集成
- [x] Token 有效时 validate() 返回 True + disabled=False
- [x] Token 无效时 validate() 返回 False + disabled=True

## ChannelProtocol 一致性
- [x] isinstance(instance, ChannelProtocol) 返回 True

## 代码质量
- [x] ruff format 通过
- [x] ruff check 通过
- [x] 全量 pytest 通过（含已有 store/channel 测试）
- [x] 不修改 legacy/ 中的任何文件

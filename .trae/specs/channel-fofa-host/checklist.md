# Checklist — fofa_host 渠道迁移

## 类结构
- [x] FofaHostChannel 继承 BaseChannelAdapter
- [x] channel_name = "fofa_host"
- [x] 构造函数接受 key（必填）和 timeout（默认 30.0），不依赖 Settings

## _validate_key
- [x] Key 为空/空白 → 抛 ChannelPermanentError（S38）
- [x] Key 有效（API 返回 error=false）→ 正常返回
- [x] Key 无效（API 返回 error=true）→ 抛 ChannelPermanentError（S38）
- [x] 验证请求网络错误 → 异常向上抛出（基类捕获）

## _request
- [x] 成功时（HTTP 200 + error=false）返回 API JSON dict（S33-S35）
- [x] Key 无效（error=true + -700）→ ChannelPermanentError（S38）
- [x] 业务错误（error=true + 其他）→ ChannelError（S39）
- [x] requests.Timeout → ChannelError（S36）
- [x] requests.ConnectionError → ChannelError（S36）
- [x] HTTP 错误 → ChannelError + 状态码（S36）
- [x] 其他异常 → ChannelError（S37）

## fetch 调用链
- [x] 继承 BaseChannelAdapter.fetch()，无需覆盖
- [x] 返回 dict 包含 query_time（基类注入）
- [x] ChannelPermanentError 设 disabled=True
- [x] ChannelError 不改变 disabled

## validate 集成
- [x] Key 有效时 validate() 返回 True + disabled=False
- [x] Key 无效时 validate() 返回 False + disabled=True

## ChannelProtocol 一致性
- [x] isinstance(instance, ChannelProtocol) 返回 True

## 代码质量
- [x] ruff format 通过
- [x] ruff check 通过
- [x] 全量 pytest 通过（含已有 store/channel 测试）
- [x] 不修改 legacy/ 中的任何文件

# Checklist — fofa_search 渠道迁移

## 类结构
- [x] FofaSearchChannel 继承 BaseChannelAdapter
- [x] channel_name = "fofa_search"
- [x] FIELDS 类常量
- [x] 构造函数接受 key（必填）和 timeout（默认 30.0）

## _validate_key
- [x] Key 为空 → ChannelPermanentError（S112）
- [x] Key 有效 → 正常返回
- [x] Key 无效（error=true）→ ChannelPermanentError（S113）
- [x] 网络错误 → 异常向上抛出

## _request
- [x] 成功有结果 → 返回 JSON dict（S107、S110）
- [x] 成功无结果 → 返回空 results dict（S109、S111）
- [x] query_suffix 追加条件 → qbase64 编码正确（S108）
- [x] Key 无效(-700) → ChannelPermanentError（S113）
- [x] 业务错误 → ChannelError（S114）
- [x] Timeout → ChannelError（S114）
- [x] ConnectionError → ChannelError（S114）
- [x] HTTP 错误 → ChannelError（S114）
- [x] 非 JSON 响应 → ChannelError（S116）
- [x] 其他异常 → ChannelError（S115）

## fetch + validate + protocol
- [x] fetch 返回 query_time
- [x] ChannelPermanentError → disabled=True
- [x] ChannelError → disabled 不变
- [x] validate 成功/失败
- [x] isinstance(ChannelProtocol)

## 代码质量
- [x] ruff 通过
- [x] 全量 pytest 通过
- [x] 不修改 legacy/

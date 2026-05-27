# Checklist — chinaz 渠道迁移

## 类结构
- [x] ChinazChannel 继承 BaseChannelAdapter
- [x] channel_name = "chinaz"
- [x] REQUIRED_COOKIE_KEYS 常量
- [x] 构造函数接受 cookie（必填）和 timeout（默认 15.0）
- [x] 覆盖 _parse()

## _validate_key
- [x] Cookie 为空 → ChannelPermanentError（S59）
- [x] Cookie 缺少必需字段 → ChannelPermanentError（S59）
- [x] Cookie 有效 → 正常返回
- [x] 网络错误 → 异常向上抛出

## _request
- [x] 成功 → 返回 HTML text
- [x] Timeout → ChannelError（S56）
- [x] ConnectionError → ChannelError（S56）
- [x] HTTP 错误 → ChannelError（S56）

## _parse
- [x] 提取归属地 + 运营商（S51）
- [x] 提取域名含起止日期（S52）
- [x] 域名去重 + 上限20 + 过滤无点号（S54）
- [x] 无关联域名 → 空列表（S55）
- [x] 页面结构异常 → ChannelError（S57）

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

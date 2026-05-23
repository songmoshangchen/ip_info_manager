# Checklist — aizhan 渠道迁移

## 类结构
- [x] AizhanChannel 继承 BaseChannelAdapter
- [x] channel_name = "aizhan"
- [x] 构造函数接受 cookie（必填）和 timeout（默认 15.0）
- [x] 覆盖 _parse()（_request 返回 str，_parse 解析 HTML）

## _validate_key
- [x] Cookie 为空 → ChannelPermanentError（S49）
- [x] Cookie 有效（HTTP 200）→ 正常返回
- [x] Cookie 失效（HTTP 301/302）→ ChannelPermanentError（S49）
- [x] Cookie 无效（HTTP 403）→ ChannelPermanentError（S49）
- [x] 网络错误 → 异常向上抛出

## _request
- [x] 成功 → 返回 HTML text
- [x] HTTP 403 → ChannelPermanentError（S49）
- [x] Timeout → ChannelError（S46）
- [x] ConnectionError → ChannelError（S46）
- [x] HTTP 错误 → ChannelError（S46）

## _parse
- [x] 中国地域格式化为"中国省份城市"（S41）
- [x] 非中国地域保留原样（S41）
- [x] 提取域名列表 + 去重 + 上限20 + 过滤无点号（S44）
- [x] 无关联域名 → 空列表（S45）
- [x] 页面缺少 dns-infos/dns-content → ChannelError（S47）
- [x] 无 tbody → ChannelError（S47）

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

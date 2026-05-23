# Checklist — ipinfo_free 渠道迁移

## 类结构
- [x] IpinfoFreeChannel 继承 BaseChannelAdapter
- [x] channel_name = "ipinfo_free"
- [x] 构造函数接受 timeout 参数，默认 30.0，不依赖 Settings

## validate
- [x] 不覆盖 _validate_key()，使用基类默认空实现
- [x] validate() 永远返回 True

## _request
- [x] 成功时返回 API JSON dict（透传所有字段）
- [x] requests.Timeout 抛出 ChannelError（S69）
- [x] requests.ConnectionError 抛出 ChannelError（S69）
- [x] HTTP 429 抛出 ChannelPermanentError（S70，禁用渠道）
- [x] 其他 HTTP 错误抛出 ChannelError + 状态码（S69）
- [x] 其他异常抛出 ChannelError（S69）

## fetch 调用链
- [x] 继承 BaseChannelAdapter.fetch()，无需覆盖
- [x] 返回 dict 包含 query_time（基类注入）
- [x] ChannelError 透传，不吞异常
- [x] ChannelPermanentError（429）设 disabled=True

## ChannelProtocol 一致性
- [x] isinstance(instance, ChannelProtocol) 返回 True

## 代码质量
- [x] ruff format 通过
- [x] ruff check 通过
- [x] 全量 pytest 通过（含已有 store/channel 测试）
- [x] 不修改 legacy/ 中的任何文件

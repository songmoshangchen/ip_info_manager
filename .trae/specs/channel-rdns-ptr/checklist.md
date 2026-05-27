# Checklist — rdns_ptr 渠道迁移

## 类结构
- [x] RdnsPtrChannel 继承 BaseChannelAdapter
- [x] channel_name = "rdns_ptr"
- [x] 构造函数接受 timeout 参数，默认 3.0，不依赖 Settings

## validate
- [x] 不覆盖 _validate_key()，使用基类默认空实现
- [x] validate() 永远返回 True

## _request
- [x] 成功时返回 hostname, aliases, ip_addresses, ptr_count, has_ptr=True, query_ip
- [x] socket.herror 返回 has_ptr=False（非错误）
- [x] socket.gaierror 返回 has_ptr=False（非错误）
- [x] socket.timeout 返回 has_ptr=False + 超时信息（非错误，S76）
- [x] 其他异常抛出 ChannelError（网络错误，S78）

## fetch 调用链
- [x] 继承 BaseChannelAdapter.fetch()，无需覆盖
- [x] 返回 dict 包含 query_time（基类注入）
- [x] ChannelError 透传，不吞异常

## ChannelProtocol 一致性
- [x] isinstance(instance, ChannelProtocol) 返回 True

## 代码质量
- [x] ruff format 通过
- [x] ruff check 通过
- [x] 全量 pytest 通过（含已有 store/channel 测试）
- [x] 不修改 legacy/ 中的任何文件

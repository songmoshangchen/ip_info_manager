# Tasks

- [x] Task 1: 实现 WhoisQueryChannel 类
  - [x] SubTask 1.1: 创建 `src/ip_info/channel/whois_query.py`，实现 `WhoisQueryChannel` 类
    - `channel_name = "whois_query"`
    - `__init__(self, timeout: float = 10.0)`
    - `_request(ip, **kwargs)`: 调用 `whois_query(ip)`，处理 None / timeout / 其他异常
    - `_parse(raw, ip)`: 解析 whois 对象属性为标准 dict
  - [x] SubTask 1.2: 确认 import 路径正确（`from whois import whois as whois_query`）

- [x] Task 2: 编写单元测试 `tests/unit/channel/test_whois_query.py`
  - [x] SubTask 2.1: TestWhoisQueryRequest — _request 方法各种网络场景
    - 正常返回 whois 对象
    - whois_query 返回 None（无记录）
    - socket.timeout → ChannelError
    - 其他异常 → ChannelError
  - [x] SubTask 2.2: TestWhoisQueryFetch — fetch 完整流程（面向结果）
    - 有 WHOIS 数据的完整返回
    - 无 WHOIS 记录（None）的完整返回
    - 多值字段取第一个
    - 日期字段转 ISO 字符串
    - name_servers / status 列表包装
    - ChannelError 透传
  - [x] SubTask 2.3: TestWhoisQueryProtocol — 协议合规
    - channel_name 正确
    - validate() 返回 True
    - disabled 默认 False

# Task Dependencies

- Task 2 depends on Task 1

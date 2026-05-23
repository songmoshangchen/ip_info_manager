# Tasks — ipinfo_api 渠道迁移

- [x] Task 1: 创建 IpinfoApiChannel 类骨架
  - [x] 1.1: 创建 `src/ip_info/channel/ipinfo_api.py`，定义 `IpinfoApiChannel(BaseChannelAdapter)` 类
  - [x] 1.2: 实现 `__init__(self, token: str, timeout: float = 30.0)`
  - [x] 1.3: 实现 `_validate_key()` — Token 非空检查 + 实际请求验证
  - [x] 1.4: 实现 `_request(ip)` — HTTP GET + Bearer Token + 状态码异常分层

- [x] Task 2: 编写 _validate_key 测试（TDD RED）
  - [x] 2.1: 测试 Token 有效（HTTP 200）— 正常返回
  - [x] 2.2: 测试 Token 为空 — 抛 ChannelPermanentError
  - [x] 2.3: 测试 Token 无效（HTTP 401）— 抛 ChannelPermanentError
  - [x] 2.4: 测试验证请求网络错误 — 异常向上抛出

- [x] Task 3: 编写 _request 测试（TDD RED）
  - [x] 3.1: 测试查询成功（HTTP 200）— 返回 API JSON dict
  - [x] 3.2: 测试 Token 无效（HTTP 401）— 抛 ChannelPermanentError
  - [x] 3.3: 测试请求限流（HTTP 429）— 抛 ChannelPermanentError
  - [x] 3.4: 测试网络超时 — 抛 ChannelError
  - [x] 3.5: 测试连接失败 — 抛 ChannelError
  - [x] 3.6: 测试其他 HTTP 错误（HTTP 500）— 抛 ChannelError
  - [x] 3.7: 测试其他非预期异常 — 抛 ChannelError

- [x] Task 4: 编写 fetch 集成测试
  - [x] 4.1: 测试 fetch 完整流程（delay → _request → query_time 注入）
  - [x] 4.2: 测试 fetch 透传 timeout 给 _request
  - [x] 4.3: 测试 fetch Token 无效设 disabled=True
  - [x] 4.4: 测试 fetch 网络错误不改变 disabled

- [x] Task 5: 编写 validate 集成测试
  - [x] 5.1: 测试 validate 成功（Token 有效）返回 True + disabled=False
  - [x] 5.2: 测试 validate 失败（Token 无效）返回 False + disabled=True

- [x] Task 6: 编写 ChannelProtocol 一致性测试
  - [x] 6.1: 测试 isinstance(instance, ChannelProtocol) 返回 True

- [x] Task 7: 运行全量测试 + pre-commit 检查

- [x] Task 8: git-commit（含中文翻译）

# Task Dependencies
- Task 2 ~ 6 依赖 Task 1（类骨架）
- Task 7 依赖 Task 1 ~ 6
- Task 8 依赖 Task 7

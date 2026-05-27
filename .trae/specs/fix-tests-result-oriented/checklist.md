# Checklist — 修复测试为面向结果

## 核心原则
- [x] 所有 fetch 测试不再使用 `patch.object(channel, "_request")`
- [x] 所有 fetch 测试改为 mock 底层网络调用（`requests.get` 或 `socket`）
- [x] fetch 测试不再验证底层调用参数（URL、timeout、headers）
- [x] fetch 测试只验证最终返回值或异常行为

## 各渠道
- [x] rdns_ptr fetch 测试面向结果
- [x] ipinfo_free fetch 测试面向结果
- [x] ipinfo_api fetch 测试面向结果
- [x] fofa_host fetch 测试面向结果
- [x] fofa_search fetch 测试面向结果
- [x] aizhan fetch 错误测试面向结果
- [x] chinaz fetch 错误测试面向结果

## 代码质量
- [x] ruff 通过
- [x] 全量 pytest 通过（252 passed）
- [x] 不修改任何源码（只改测试）

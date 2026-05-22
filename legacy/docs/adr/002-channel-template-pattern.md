# ADR-002: 渠道模板模式（Channel Template Pattern）

## 状态

已采纳

## 上下文

项目需要对接 10+ 个外部数据源（API 和爬虫），每个数据源的请求方式、认证方式、响应格式各不相同。需要一种统一的开发模式来保证一致性和可维护性。

## 决策

采用 **渠道模板模式**，通过 `channel/_template.py` 定义标准 5 部分结构：

```
1. validate_channel_key()   — 凭证校验
2. request_channel()        — 网络请求（仅请求）
3. parse_response()         — 响应解析（仅解析）
4. fetch_channel()          — 采集入口（组合 request + parse + delay）
5. main()                   — CLI 入口
```

标准调用链：
```
apply_delay(delay) → request_channel() → parse_response() → format_output()
```

## 理由

1. **关注点分离** — 请求和解析解耦，可独立测试
2. **一致性** — 所有渠道遵循相同模式，降低学习成本
3. **可扩展** — 新渠道按模板开发，10 分钟可完成骨架
4. **可测试性** — `request_channel` 和 `parse_response` 可分别 mock

## 后果

**优势：**
- 新增渠道只需实现 3-5 个函数
- 批量脚本可复用 `fetch_channel()` 函数
- 错误处理统一（`raw_error` 标记）

**劣势：**
- 部分渠道不需要所有步骤（如 API 类可省略 `parse_response`）
- 模板约束可能限制特殊渠道的自定义需求

**渠道分类：**

| 类型 | 代表 | 特点 |
|------|------|------|
| API 类 | fofa, ipinfo, zoomeye | JSON 响应，通常不需要 parse_response |
| 爬虫类 | aizhan, chinaz | HTML 响应，必须实现 parse_response |
| 本地类 | rdns_ptr, ssl_cert, port_scan | 无外部 API，本地执行命令或 DNS 查询 |

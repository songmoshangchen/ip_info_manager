# 修复：限流错误分类修正

## Why

HTTP 429（请求限流）是临时性错误，过一段时间后重试可能成功。当前 ipinfo_free 和 ipinfo_api 将 429 归类为 `ChannelPermanentError`（永久错误），导致渠道被 disabled，后续 IP 全部跳过。这与错误分类原则不符：只有 Key/Cookie 失效等**百分百重复失败**的情况才应设为永久错误。

## 错误分类原则（确认）

| 错误类型 | 异常类 | 理由 |
|----------|--------|------|
| Key/Cookie 未配置 | `ChannelPermanentError` | 100% 失败，必须修改配置 |
| Key/Cookie 无效（401/403） | `ChannelPermanentError` | 100% 失败，必须更换 Key |
| 请求限流（429） | `ChannelError` | 临时性，过一段时间可重试 |
| 网络超时/连接失败 | `ChannelError` | 临时性，网络恢复后可重试 |
| 其他 HTTP 错误（500 等） | `ChannelError` | 临时性，服务恢复后可重试 |
| 非预期异常 | `ChannelError` | 临时性，可能偶发 |

## What Changes

- **ipinfo_free**：HTTP 429 从 `ChannelPermanentError` 改为 `ChannelError`
- **ipinfo_api**：HTTP 429 从 `ChannelPermanentError` 改为 `ChannelError`
- 对应测试用例同步更新

## Impact

- Affected code: `src/ip_info/channel/ipinfo_free.py`、`src/ip_info/channel/ipinfo_api.py`
- Affected tests: `tests/unit/channel/test_ipinfo_free.py`、`tests/unit/channel/test_ipinfo_api.py`

---

## MODIFIED Requirements

### Requirement: ipinfo_free — HTTP 429 错误分类（修改 S70）

429 限流 SHALL 抛出 `ChannelError`（临时性错误），不改变 `disabled` 状态。

**原实现**：`ChannelPermanentError`（disabled=True）
**新实现**：`ChannelError`（不改变 disabled）

理由：限流是临时性错误，过一段时间后重试可能成功。只有 Key 失效等百分百重复失败的情况才应设为永久错误。

### Requirement: ipinfo_api — HTTP 429 错误分类（修改）

429 限流 SHALL 抛出 `ChannelError`（临时性错误），不改变 `disabled` 状态。

**原实现**：`ChannelPermanentError`（disabled=True）
**新实现**：`ChannelError`（不改变 disabled）

理由：同上。ipinfo_api 的 HTTP 401/403（Token 无效）仍保持 `ChannelPermanentError`，因为 Token 失效是百分百重复失败的永久性错误。

## 上层熔断机制（确认）

`ChannelError` 和 `ChannelPermanentError` 都会从 `fetch()` 向上透传：
- `ChannelPermanentError`：被基类 `fetch()` 捕获 → 设 `disabled=True` → **raise 透传**
- `ChannelError`：**直接透传**（不被 `fetch()` 捕获）

上层（批量查询层）可统一用 `try/except ChannelError` 捕获所有错误（`ChannelPermanentError` 是其子类）。上层保险设计：**同一渠道连续 N 次 `ChannelError` → 跳过该渠道后续 IP**（在批量查询层实现，不在渠道层）。

# 修复：测试改为面向结果

## Why

部分 fetch 测试使用 `patch.object(channel, "_request")` mock 内部方法，跳过了 `_request → _parse` 的真实执行链路。这是面向过程的白盒测试——它测试的是"fetch 是否调用了 _request"，而非"fetch 的最终输出是否正确"。

正确做法（aizhan/chinaz 已采用）：mock 底层 `requests.get`，让 `fetch → _request → _parse` 真实执行，验证最终返回的 dict。

## 修改原则

| 测试类 | 应 mock 什么 | 不应 mock 什么 |
|--------|-------------|---------------|
| TestXxxRequest | `requests.get`（或 `socket`） | 不 mock `_request` |
| TestXxxValidateKey | `requests.get` | 不 mock `_validate_key` |
| TestXxxParse | 直接调用 `_parse(html, ip)` | — |
| TestXxxFetch | `requests.get`（或 `socket`） | **不 mock `_request`** |
| TestXxxValidate | `requests.get`（或底层） | 不 mock `_validate_key` |
| TestXxxProtocol | 无需 mock | — |

## What Changes

### 问题 1：fetch "完整流程" 测试 mock 了 `_request`（5 个文件）

这些测试应改为 mock 底层网络调用（`requests.get` 或 `socket`），让 `_request` 和 `_parse` 真实执行。

- `test_rdns_ptr.py` — `test_fetch完整流程_包含query_time`
- `test_ipinfo_free.py` — `test_fetch完整流程_包含query_time`
- `test_ipinfo_api.py` — `test_fetch完整流程_包含query_time`
- `test_fofa_host.py` — `test_fetch完整流程_包含query_time`
- `test_fofa_search.py` — `test_fetch完整流程_包含query_time`

### 问题 2：fetch 错误处理测试 mock 了 `_request`（7 个文件）

这些测试应改为 mock 底层网络调用，让 `_request` 真实抛出异常。

- `test_rdns_ptr.py` — `test_fetch网络错误透传ChannelError`
- `test_ipinfo_free.py` — `test_fetch网络错误透传ChannelError`、`test_fetch限流时不改变disabled`
- `test_ipinfo_api.py` — `test_fetch_Token无效设disabled为True`、`test_fetch_网络错误不改变disabled`
- `test_fofa_host.py` — `test_fetch_Key无效设disabled为True`、`test_fetch_网络错误不改变disabled`
- `test_fofa_search.py` — `test_fetch_Key无效设disabled为True`、`test_fetch_网络错误不改变disabled`
- `test_aizhan.py` — `test_fetch_Cookie无效设disabled为True`、`test_fetch_网络错误不改变disabled`
- `test_chinaz.py` — `test_fetch_Cookie无效设disabled为True`、`test_fetch_网络错误不改变disabled`

### 问题 3：fetch timeout 透传测试验证了底层调用参数（2 个文件）

这些测试验证 `requests.get` 的调用参数（URL、timeout），属于越界验证。应改为验证最终结果。

- `test_ipinfo_free.py` — `test_fetch透传timeout给_request`
- `test_ipinfo_api.py` — `test_fetch透传timeout给_request`

### 不修改的测试（确认合理）

- `_request` 测试中验证 URL/headers/params — 合理（这是 `_request` 的契约）
- `_validate_key` 测试中 mock `requests.get` — 合理
- `validate` 测试中用 `patch.object` mock `_validate_key` — 合理（验证基类 validate 行为）
- `_parse` 测试直接调用 `_parse(html, ip)` — 合理

## Impact

- Affected tests: 7 个测试文件中的 fetch 相关测试
- 不修改任何源码（只改测试）

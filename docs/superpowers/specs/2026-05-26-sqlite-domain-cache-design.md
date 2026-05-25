# SqliteDomainCache 完善设计

> 日期：2026-05-26
> 状态：已批准

## Why

`SqliteDomainCache` 已有基本实现，但存在以下问题：
1. **Bug**：`__init__` 未创建父目录，当 `db_path` 包含不存在的子目录时抛出 `OperationalError`
2. **导出缺失**：`DomainCache`、`InMemoryDomainCache`、`SqliteDomainCache` 未在 `__init__.py` 导出
3. **类型注解缺失**：`BatchDnsVerify` 的 `domain_cache` 参数无类型注解
4. **表结构可优化**：`data` 字段存 JSON blob，`status` 和 `resolved_ips` 不可直接 SQL 查询

## What Changes

### 1. Bug 修复：父目录自动创建

`SqliteDomainCache.__init__` 在连接数据库前先创建父目录，与 `IPWriter` 行为一致：

```python
def __init__(self, db_path: str):
    self._db_path = db_path
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    self._local = threading.local()
    self._init_db()
```

### 2. 表结构拆分

从 `data` JSON blob 拆为独立字段：

```sql
CREATE TABLE IF NOT EXISTS domain_cache (
    domain TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    resolved_ips TEXT NOT NULL,   -- JSON 数组
    updated_at TEXT NOT NULL
)
```

- `set()` 时从 dict 提取 `status`、`resolved_ips` 写入各列
- `get()` 时重新组装为 `{"domain": ..., "status": ..., "resolved_ips": ...}` 返回
- `DomainCache` Protocol 接口暂不修改，保持 `get() -> dict | None` / `set(domain, data: dict)`

### 3. `__init__.py` 导出补充

新增导出 `DomainCache`、`InMemoryDomainCache`、`SqliteDomainCache`。

### 4. 类型注解集成

`BatchDnsVerify.__init__` 的 `domain_cache` 参数加类型注解：

```python
def __init__(self, ..., domain_cache: DomainCache | None = None):
```

### 5. 测试补充

- 修复 `test_数据库文件自动创建`（验证子目录自动创建）
- 新增：损坏数据读取（`resolved_ips` 不是合法 JSON 时返回 None）
- 新增：`set` 时缺少 `status` 或 `resolved_ips` 字段的行为
- 新增：`get` 返回的 dict 结构验证（包含 domain/status/resolved_ips 三个键）

## 不做的事

- 不修改 `DomainCache` Protocol（后续再改）
- 不增加 `delete`/`clear` 方法
- 不增加 TTL 自动清理

## Impact

- Affected code: `src/ip_info/store/sqlite_cache.py`、`src/ip_info/store/__init__.py`、`src/ip_info/processors/dns_verify/runner.py`、`tests/unit/store/test_sqlite_cache.py`
- 不修改 `DomainCache` Protocol
- 不修改 `InMemoryDomainCache`

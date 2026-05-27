# 存储层（Store Layer）规格文档

> **对应重构方案**：第六节 "Skills 使用推荐"，Step 1.1-1.10
>
> **Skills 链**：`brainstorming`（Step 1.1）→ `setup-pre-commit`（Step 1.1 后）→ `tdd` + `git-commit`（Step 1.2-1.10 每个 Step 循环一次）
>
> **特殊情况 Skills**：`diagnose`（测试失败时）、`grill-me`（设计审查时）

## Why

存储层是整个 ip_info_manager 系统的最内层核心，所有上层（渠道层、批量查询层、流水线层）都依赖它来读写 IP 数据。当前代码分散在 `legacy/writer.py`、`legacy/reader.py`、`legacy/protocols.py` 中，存在 Protocol/实现/测试替身混放、依赖 `config.Settings` 耦合等问题。需要将其重构为独立的 `src/ip_info/store/` 包，先协议后实现，支持依赖注入。

## What Changes

- 从 `legacy/protocols.py` 提取 `IPDataWriter` 和 `IPDataReader` Protocol，放入 `src/ip_info/store/protocols.py`
- 从 `legacy/protocols.py` 提取 `InMemoryIPWriter` 和 `InMemoryIPReader` 测试替身，放入 `src/ip_info/store/in_memory.py`
- 从 `legacy/writer.py` 提取 `IPWriter`（JSON 文件实现），放入 `src/ip_info/store/json_store.py`，**去除对 `config.Settings` 的直接依赖**，改为通过构造函数注入 `storage_file` 完整路径
- 从 `legacy/reader.py` 提取 `IPReader`（JSON 文件实现），合并到 `src/ip_info/store/json_store.py`，同样去除 `config.Settings` 依赖
- **新增批量查询接口**：`get_ips_data(ips)` 和 `list_all_ips_data(exclude_ips)`
- **新增 IO 异常透传策略**：文件操作失败时抛出 `OSError`，由上层捕获处理
- 新增 `src/ip_info/store/__init__.py` 统一导出
- 新增 `tests/unit/store/` 存放新测试
- 新增 `pyproject.toml` 使 `pip install -e .` 可用

## Impact

- Affected specs: 无前置 spec，这是第一个 spec
- Affected code: `src/ip_info/store/`（全新）、`tests/unit/store/`（全新）、`pyproject.toml`（新增）
- 不修改 `legacy/` 中的任何文件

---

## ADDED Requirements

### Requirement: IPDataWriter Protocol

系统 SHALL 提供 `IPDataWriter` Protocol（`@runtime_checkable`），定义写入接口：

```python
@runtime_checkable
class IPDataWriter(Protocol):
    def add_or_update_ip(self, ip: str, channel: str, data: dict) -> bool: ...
    def delete_ip(self, ip: str) -> bool: ...
    def delete_channel(self, ip: str, channel: str) -> bool: ...
```

#### Scenario: isinstance 检查通过
- **WHEN** 一个类实现了 `add_or_update_ip`、`delete_ip`、`delete_channel` 三个方法（签名匹配）
- **THEN** `isinstance(instance, IPDataWriter)` 返回 `True`

---

### Requirement: IPDataReader Protocol

系统 SHALL 提供 `IPDataReader` Protocol（`@runtime_checkable`），定义读取接口：

```python
@runtime_checkable
class IPDataReader(Protocol):
    def get_ip_data(self, ip: str) -> dict | None: ...
    def get_channel_data(self, ip: str, channel: str) -> dict | None: ...
    def list_all_ips(self) -> list[str]: ...
    def list_ip_channels(self, ip: str) -> list[str]: ...
    def search_ips_by_channel(self, channel: str, key: str = None, value: str = None) -> list[str]: ...
    def get_ips_data(self, ips: list[str]) -> dict[str, dict]: ...
    def list_all_ips_data(self, exclude_ips: list[str] | None = None) -> dict[str, dict]: ...
```

#### Scenario: isinstance 检查通过
- **WHEN** 一个类实现了上述 7 个方法（签名匹配）
- **THEN** `isinstance(instance, IPDataReader)` 返回 `True`

---

### Requirement: InMemoryIPWriter 测试替身

系统 SHALL 提供 `InMemoryIPWriter` 类，实现 `IPDataWriter` Protocol，同时提供读取能力（即也实现 `IPDataReader` 接口），用于测试。

#### Scenario: 创建新 IP 记录
- **WHEN** 调用 `add_or_update_ip('1.2.3.4', 'rdns_ptr', {'hostname': 'example.com'})` 且 IP 不存在
- **THEN** 内部存储中创建 `{'1.2.3.4': {'ip': '1.2.3.4', 'rdns_ptr': {'hostname': 'example.com'}}}`，返回 `True`

#### Scenario: 追加渠道到已有 IP
- **WHEN** 调用 `add_or_update_ip('1.2.3.4', 'ipinfo_api', {'country': 'CN'})` 且 IP 已存在
- **THEN** 在已有 IP 记录上追加 `ipinfo_api` 渠道数据，不影响已有渠道，返回 `True`

#### Scenario: 覆盖已有渠道（整体替换）
- **WHEN** 调用 `add_or_update_ip('1.2.3.4', 'rdns_ptr', {'new': 'data'})` 且该渠道已存在
- **THEN** 整个渠道数据被替换为 `{'new': 'data'}`（旧字段全部消失），返回 `True`

#### Scenario: 删除整个 IP 记录
- **WHEN** 调用 `delete_ip('1.2.3.4')` 且 IP 存在
- **THEN** 从存储中移除该 IP 的全部数据，返回 `True`

#### Scenario: 删除不存在的 IP
- **WHEN** 调用 `delete_ip('9.9.9.9')` 且 IP 不存在
- **THEN** 不做任何修改，返回 `False`

#### Scenario: 删除指定渠道
- **WHEN** 调用 `delete_channel('1.2.3.4', 'rdns_ptr')` 且 IP 和渠道都存在
- **THEN** 仅移除该渠道，IP 记录和其他渠道保留，返回 `True`

#### Scenario: 删除不存在 IP 的渠道
- **WHEN** 调用 `delete_channel('9.9.9.9', 'rdns_ptr')` 且 IP 不存在
- **THEN** 返回 `False`

#### Scenario: 删除不存在的渠道
- **WHEN** 调用 `delete_channel('1.2.3.4', 'nonexistent')` 且 IP 存在但渠道不存在
- **THEN** 返回 `False`

---

### Requirement: InMemoryIPReader 测试替身

系统 SHALL 提供 `InMemoryIPReader` 类，实现 `IPDataReader` Protocol，通过构造函数注入数据字典。

#### Scenario: 读取完整 IP 数据
- **WHEN** 调用 `get_ip_data('1.2.3.4')` 且 IP 存在
- **THEN** 返回完整 IP 记录 dict（含 `ip` 字段和各渠道数据）

#### Scenario: 读取不存在的 IP
- **WHEN** 调用 `get_ip_data('9.9.9.9')` 且 IP 不存在
- **THEN** 返回 `None`

#### Scenario: 读取指定渠道数据
- **WHEN** 调用 `get_channel_data('1.2.3.4', 'rdns_ptr')` 且 IP 和渠道都存在
- **THEN** 返回该渠道的 dict

#### Scenario: 读取不存在 IP 的渠道
- **WHEN** 调用 `get_channel_data('9.9.9.9', 'rdns_ptr')` 且 IP 不存在
- **THEN** 返回 `None`

#### Scenario: 读取不存在的渠道
- **WHEN** 调用 `get_channel_data('1.2.3.4', 'nonexistent')` 且 IP 存在但渠道不存在
- **THEN** 返回 `None`

#### Scenario: 列出所有 IP
- **WHEN** 调用 `list_all_ips()`
- **THEN** 返回所有 IP 地址的 list（即存储字典的 keys）

#### Scenario: 列出 IP 的渠道（排除 `ip` 字段）
- **WHEN** 调用 `list_ip_channels('1.2.3.4')` 且 IP 存在
- **THEN** 返回该 IP 下所有渠道名 list，**不包含** `'ip'` 键

#### Scenario: 列出不存在 IP 的渠道
- **WHEN** 调用 `list_ip_channels('9.9.9.9')` 且 IP 不存在
- **THEN** 返回空 list `[]`

#### Scenario: 按渠道搜索 IP（无过滤）
- **WHEN** 调用 `search_ips_by_channel('rdns_ptr')`（不传 key/value）
- **THEN** 返回所有拥有该渠道的 IP list

#### Scenario: 按渠道 + key 搜索
- **WHEN** 调用 `search_ips_by_channel('rdns_ptr', key='hostname')` 且渠道中存在该 key
- **THEN** 返回匹配 IP list

#### Scenario: 按渠道 + key + value 搜索
- **WHEN** 调用 `search_ips_by_channel('rdns_ptr', key='hostname', value='host1.com')`
- **THEN** 仅返回渠道数据中 `hostname == 'host1.com'` 的 IP

#### Scenario: 搜索时 key 不存在于渠道数据中
- **WHEN** 调用 `search_ips_by_channel('rdns_ptr', key='nonexistent_key')`
- **THEN** 该 IP 被排除，返回空 list

---

### Requirement: 批量查询接口

`IPDataReader` SHALL 提供两个批量查询方法，所有实现（InMemory、JSON）都必须支持。

#### Scenario: 批量获取多个 IP 的完整数据
- **WHEN** 调用 `get_ips_data(['1.2.3.4', '5.6.7.8', '9.9.9.9'])`
- **THEN** 返回 dict，key 为存在的 IP 地址，value 为对应完整记录。不存在的 IP 不包含在结果中（非 None）
- **示例**：若 `9.9.9.9` 不存在，返回 `{'1.2.3.4': {...}, '5.6.7.8': {...}}`

#### Scenario: 批量获取空列表
- **WHEN** 调用 `get_ips_data([])`
- **THEN** 返回空 dict `{}`

#### Scenario: 列出所有 IP 数据（无排除）
- **WHEN** 调用 `list_all_ips_data()`（不传 exclude_ips）
- **THEN** 返回所有 IP 的完整数据 dict，key 为 IP 地址

#### Scenario: 列出所有 IP 数据并排除部分 IP
- **WHEN** 调用 `list_all_ips_data(exclude_ips=['1.2.3.4'])`
- **THEN** 返回结果中不包含 `1.2.3.4`，其他 IP 正常返回

#### Scenario: 排除不存在的 IP（无副作用）
- **WHEN** 调用 `list_all_ips_data(exclude_ips=['9.9.9.9'])` 且该 IP 不在存储中
- **THEN** 正常返回所有存在的 IP 数据，忽略排除列表中不存在的 IP

---

### Requirement: 读写一致性

`InMemoryIPWriter` SHALL 同时实现 `IPDataReader` 接口（即也具备 `get_ip_data`、`get_channel_data`、`list_all_ips`、`list_ip_channels`、`search_ips_by_channel`、`get_ips_data`、`list_all_ips_data` 方法），使通过 Writer 写入的数据可通过 Reader 方法读回。

#### Scenario: 通过 Writer 写入后通过 Reader 接口读回
- **WHEN** 通过 `InMemoryIPWriter` 写入数据
- **THEN** 通过同一实例的 `get_ip_data` / `get_channel_data` / `list_all_ips` 等方法能正确读回

---

### Requirement: IO 异常透传策略

JSON 文件实现（`IPWriter`、`IPReader`）在遇到文件系统错误时 SHALL 透传 `OSError` 异常，由上层捕获处理。不做静默吞异常或返回 False。

#### Scenario: 写入时文件权限不足
- **WHEN** `add_or_update_ip` 写入文件时遇到 `PermissionError`（OSError 子类）
- **THEN** 直接抛出 `PermissionError`，不做吞异常处理

#### Scenario: 读取时文件权限不足
- **WHEN** `get_ip_data` 读取文件时遇到 `PermissionError`
- **THEN** 直接抛出 `PermissionError`

#### Scenario: 文件不存在时的读取行为（非异常）
- **WHEN** JSON 文件不存在（正常场景，如首次使用）
- **THEN** `get_ip_data` 返回 `None`，`list_all_ips` 返回 `[]`，**不抛异常**

---

### Requirement: JSON 文件 IPWriter

系统 SHALL 提供 `IPWriter` 类，实现 `IPDataWriter` Protocol，将数据持久化到 JSON 文件。通过构造函数接收 `storage_file` 完整路径（由应用层管理路径拼接）。

#### Scenario: 文件和目录不存在时自动创建
- **WHEN** 构造 `IPWriter` 时目录和 JSON 文件均不存在
- **THEN** 自动创建目录和空 JSON 文件 `{}`

#### Scenario: 写入数据到 JSON 文件
- **WHEN** 调用 `add_or_update_ip('1.2.3.4', 'rdns_ptr', {'hostname': 'test.com'})`
- **THEN** JSON 文件中包含该数据

#### Scenario: 从 JSON 文件删除 IP
- **WHEN** 调用 `delete_ip('1.2.3.4')` 且文件中有该 IP
- **THEN** JSON 文件中该 IP 被移除，返回 `True`

#### Scenario: 从 JSON 文件删除渠道
- **WHEN** 调用 `delete_channel('1.2.3.4', 'rdns_ptr')` 且文件中有该 IP 和渠道
- **THEN** JSON 文件中该渠道被移除，返回 `True`

#### Scenario: 线程安全
- **WHEN** 多个线程并发调用 `add_or_update_ip`
- **THEN** 不丢失数据（所有写入都成功持久化），通过 `threading.Lock` 保护

---

### Requirement: JSON 文件 IPReader

系统 SHALL 提供 `IPReader` 类，实现 `IPDataReader` Protocol（含批量查询接口），从 JSON 文件读取数据。通过构造函数接收 `storage_file` 完整路径。

#### Scenario: 从 JSON 文件读取 IP 数据
- **WHEN** 调用 `get_ip_data('1.2.3.4')` 且文件中有该 IP
- **THEN** 返回完整 IP 记录 dict

#### Scenario: 文件不存在时返回空数据
- **WHEN** JSON 文件不存在
- **THEN** `get_ip_data` 返回 `None`，`list_all_ips` 返回 `[]`

#### Scenario: 端到端读写闭环
- **WHEN** 通过 `IPWriter` 写入数据后，用同一文件路径构造 `IPReader` 读取
- **THEN** 读取结果与写入数据一致

#### Scenario: 端到端批量查询闭环
- **WHEN** 通过 `IPWriter` 写入多条数据后，通过 `IPReader` 调用 `get_ips_data` 和 `list_all_ips_data`
- **THEN** 批量查询结果与写入数据一致

---

### Requirement: 项目骨架 pyproject.toml

系统 SHALL 提供 `pyproject.toml` 配置文件，使 `pip install -e .` 可用，且 `import ip_info` 能正常工作。

#### Scenario: 安装后可导入
- **WHEN** 执行 `pip install -e .`
- **THEN** `import ip_info` 成功，无报错

---

## MODIFIED Requirements

无（全新构建）。

## REMOVED Requirements

### Requirement: 对 config.Settings 的直接依赖
**Reason**: 存储层不应直接依赖应用配置层，违反依赖倒置原则。新实现通过构造函数注入完整路径。
**Migration**: 应用层（pipeline/scenario）负责路径拼接（如 `data/{storage_dir}/{storage_name}.json`），将完整路径传入存储层。

### Requirement: writer.py / reader.py 的 CLI 入口（main 函数）
**Reason**: 存储层是库代码，不应包含 CLI 入口。CLI 功能由上层应用或独立脚本提供。
**Migration**: 如需 CLI 功能，在 `scripts/` 或 `tools/` 层单独实现。

---

## 数据结构约定

IP 数据在存储中的 JSON 结构：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "rdns_ptr": {"hostname": "example.com", "has_ptr": true},
    "ipinfo_api": {"country": "CN", "org": "ISP-A"}
  },
  "5.6.7.8": {
    "ip": "5.6.7.8",
    "rdns_ptr": {"hostname": "host2.com", "has_ptr": true}
  }
}
```

关键约定：
- 每个 IP 记录必须包含 `"ip"` 字段，值等于 IP 地址字符串
- 渠道名作为 key，渠道数据作为 value（dict）
- `list_ip_channels` 返回时排除 `"ip"` 字段
- `add_or_update_ip` 对渠道数据做整体替换（非合并）

## 与 legacy 的差异

| 项目 | Legacy | 新实现 |
|------|--------|--------|
| Settings 依赖 | `from config import Settings`，构造函数可选传入 | **无依赖**，通过 `storage_file` 完整路径注入 |
| 文件路径逻辑 | 自动拼接 `data/{storage_dir}/{storage_name}.json` | 调用者传入完整路径，应用层管理路径拼接 |
| 目录自动创建 | `_init_storage` 中 `os.makedirs` | 保留，构造时自动创建目录和文件 |
| InMemory 替身 | `InMemoryIPWriter` 也实现 Reader 接口 | **保留此行为** |
| `get_all()` 方法 | `InMemoryIPWriter.get_all()` 返回内部 store | **保留**，作为测试辅助方法 |
| 线程安全 | `IPWriter` 使用 `threading.Lock` | **保留** |
| 批量查询 | 无 | **新增** `get_ips_data` 和 `list_all_ips_data` |
| IO 异常处理 | 无显式处理 | **新增** 透传 OSError，由上层捕获 |

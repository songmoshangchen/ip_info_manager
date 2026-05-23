# port_scan 渠道迁移规格文档

> **对应重构方案**：Step 2.5（渠道迁移第 10 个，共 11 个，zoomeye 暂跳过）
>
> **Skills 链**：`/spec`（本文档）→ 用户审核 → `tdd` → `git-commit`
>
> **Legacy 源文件**：`legacy/channel/port_scan.py`
>
> **PRD 需求**：S94-S106（参考）

## Why

port_scan 渠道通过调用 `nmap` 工具扫描目标 IP 的开放端口，获取端口、服务、产品信息。它还支持历史端口验证（对比 fofa_host/zoomeye 数据）。这是唯一需要覆盖 `_validate_key()` 的无认证渠道——验证的是 nmap 工具可用性而非 API Key。

## What Changes

- 新建 `src/ip_info/channel/port_scan.py`，包含 `PortScanChannel` 类（继承 `BaseChannelAdapter`）
- 新建 `tests/unit/channel/test_port_scan.py`，包含完整单元测试
- 新增 `python-nmap` 依赖（`pip install python-nmap`）
- 不修改 `legacy/` 中的任何文件

## Impact

- Affected specs: 依赖 `channel-layer-core` spec（`BaseChannelAdapter`、`ChannelError`、`ChannelPermanentError`）
- Affected code: `src/ip_info/channel/`（新增文件）、`tests/unit/channel/`（新增文件）

---

## ADDED Requirements

### Requirement: PortScanChannel 类

系统 SHALL 提供 `PortScanChannel` 类，继承 `BaseChannelAdapter`，使用 `python-nmap` 库封装 nmap 端口扫描逻辑。

```python
import nmap

class PortScanChannel(BaseChannelAdapter):
    channel_name = "port_scan"

    def __init__(self, nmap_path: str = "nmap", timeout: float = 30.0): ...
    def _validate_key(self) -> None: ...
    def _request(self, ip: str, **kwargs) -> nmap.PortScanner: ...
    def _parse(self, raw, ip: str) -> dict: ...
```

**构造函数约定**：
- `nmap_path`：nmap 可执行文件路径，默认 `"nmap"`（从 PATH 查找）
- `timeout`：nmap 扫描超时时间（秒），默认 30.0
- 不依赖 `config.Settings`，通过构造函数注入

---

### Requirement: _validate_key — nmap 可用性检查（S101、S102）

`_validate_key()` SHALL 通过 `nmap.PortScanner()` 初始化来检查 nmap 工具是否可用。

#### Scenario: nmap 可用（S101）
- **WHEN** `nmap.PortScanner()` 初始化成功
- **THEN** 正常返回（不抛异常）

#### Scenario: nmap 不可用（S101）
- **WHEN** `nmap.PortScanner()` 抛出 `nmap.PortScannerError`（nmap 未安装）
- **THEN** 抛出 `ChannelPermanentError`，消息格式为 `"nmap 不可用: {nmap_path}"`

---

### Requirement: _request — 执行 nmap 扫描（S94、S103）

`_request(ip, **kwargs)` SHALL 使用 `nmap.PortScanner` 执行扫描，返回 `PortScanner` 对象。

#### Scenario: 成功执行 nmap 扫描（S94）
- **WHEN** `nm.scan(ip, ports, arguments)` 成功
- **THEN** 返回 `PortScanner` 对象

#### Scenario: nmap 命令不存在（S103）
- **WHEN** `nmap.PortScanner.scan()` 抛出 `nmap.PortScannerError`
- **THEN** 抛出 `ChannelError`，消息格式为 `"nmap 扫描错误: {ip} - {error}"`

#### Scenario: nmap 扫描超时（S103）
- **WHEN** scan 执行超时
- **THEN** 抛出 `ChannelError`，消息格式为 `"nmap 扫描超时: {ip}（超过 {timeout} 秒）"`

#### Scenario: 其他异常（S103、S104）
- **WHEN** 抛出非预期异常
- **THEN** 抛出 `ChannelError`，消息格式为 `"nmap 扫描异常: {ip} - {error}"`

#### Scenario: 端口列表参数（S96）
- **WHEN** `kwargs` 包含 `port_string`（如 `"80,443,8080"`）
- **THEN** 传入 `nm.scan(ip, ports=port_string)`
- **WHEN** `kwargs` 不包含 `port_string` 或为空
- **THEN** 不指定 ports 参数（扫描常用端口）

#### Scenario: nmap 扫描参数
- **THEN** arguments 包含：`-sT -T4 -Pn --open`
- **AND** 通过 `nm.scan(ip, ports=port_string, arguments="-sT -T4 -Pn --open")` 调用

---

### Requirement: _parse — 解析 nmap 扫描结果（S95、S97、S98、S100）

`_parse(raw, ip)` SHALL 将 `PortScanner` 对象转换为结构化结果 dict。

#### Scenario: 成功解析扫描结果（S97、S98）
- **WHEN** `raw` 是 `PortScanner` 对象且包含扫描结果
- **THEN** 返回 dict：
  ```python
  {
      "query_target": ip,
      "engine": "nmap",
      "host_alive": bool,
      "open_ports": [
          {
              "port": int,
              "protocol": str,     # "tcp"
              "state": "open",
              "service": str,      # 服务名称（可选）
              "product": str,      # 产品信息（可选）
              "version": str,      # 版本信息（可选）
          }
      ],
      "total_scanned": int,
      "open_count": int,
      "historical_ports_verified": list[int],
      "historical_ports_closed": list[int],
  }
  ```

#### Scenario: 主机无扫描结果（S99、S100）
- **WHEN** `PortScanner` 对象中不包含该 IP 的数据（`ip not in nm.all_hosts()`）
- **THEN** 返回空结果（host_alive=False, open_ports=[], open_count=0）

#### Scenario: nmap 扫描返回错误信息
- **WHEN** `nm.scaninfo()` 包含 error 信息（如 `"error"` key）
- **THEN** 结果中包含 `"nmap_error": error_message`
- **AND** 仍返回基础结构（host_alive=False, open_ports=[], open_count=0）

#### Scenario: 主机无响应（S99）
- **WHEN** 主机存在但状态不为 `"up"`
- **THEN** `host_alive=False`

#### Scenario: 端口信息提取（S95、S98）
- **WHEN** 端口状态为 `"open"`
- **THEN** 提取 `port`（int）、`protocol`、`state`
- **AND** 如果有 service 信息，提取 `service`（name）、`product`、`version`

#### Scenario: 历史端口验证
- **WHEN** `kwargs` 或实例属性中包含 `historical_ports`（如 `[80, 443]`）
- **THEN** 将扫描结果中的开放端口与历史端口对比
- **AND** `historical_ports_verified` 包含仍然开放的历史端口
- **AND** `historical_ports_closed` 包含已关闭的历史端口

**实现策略**：`_request` 将 historical_ports 存入实例属性 `self._historical_ports`，`_parse` 从中读取。

---

### Requirement: fetch 调用链完整性

`PortScanChannel` 继承 `BaseChannelAdapter.fetch()` 的标准调用链，无需覆盖。

#### Scenario: fetch 完整流程
- **WHEN** 调用 `fetch("1.2.3.4", port_string="80,443", historical_ports=[80, 443])`
- **THEN** 执行链路：`delay → _request(ip, port_string=..., historical_ports=...) → _parse(raw, ip) → setdefault(query_time)`

#### Scenario: fetch 网络错误透传 ChannelError
- **WHEN** `_request()` 抛出 `ChannelError`
- **THEN** `fetch()` 直接透传异常

#### Scenario: validate 成功（nmap 可用）
- **WHEN** nmap 可用
- **THEN** `validate()` 返回 `True`，`disabled` 设为 `False`

#### Scenario: validate 失败（nmap 不可用）
- **WHEN** nmap 不可用
- **THEN** `validate()` 返回 `False`，`disabled` 设为 `True`

---

### Requirement: 满足 ChannelProtocol

#### Scenario: isinstance 检查通过
- **WHEN** 创建 `PortScanChannel()` 实例
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

---

## 与 Legacy 的差异

| 项目 | Legacy | 新实现 |
|------|--------|--------|
| 结构 | 模块级函数 + `PortScanChannel` 类 | 仅 `PortScanChannel` 类（继承 `BaseChannelAdapter`） |
| nmap 调用 | `subprocess.run` 手动构建命令 | **python-nmap 库**（`nmap.PortScanner`） |
| XML 解析 | 手动 `xml.etree.ElementTree` 解析 | **python-nmap 内部处理** |
| Settings 依赖 | `from config import TraceIPSettings` | **无依赖**，nmap_path/timeout 通过构造函数注入 |
| validate | `validate_engine()` 返回路径或 None | `_validate_key()` 检查 nmap 可用性，失败抛 `ChannelPermanentError` |
| 网络错误信号 | `{"raw_error": True, ...}` dict | 抛出 `ChannelError` 异常 |
| 端口列表文件 | `load_port_list()` 从文件读取 | **不在渠道层**，由上层准备 port_string 传入 |
| 历史端口提取 | `extract_historical_ports()` 从 ip_data 提取 | **不在渠道层**，由上层准备 historical_ports 传入 |
| delay / format_output | 模块级函数 | **基类统一提供** |
| CLI main() | 文件末尾 | **不在渠道层**，由上层处理 |
| 日志 | `get_channel_logger('port_scan')` | 基类不内置 logger，子类按需添加 |

## 关键设计决策

1. **使用 python-nmap 库**（brainstorming 确认）：通过 `nmap.PortScanner` 封装 nmap 调用，无需手动构建命令和解析 XML，代码更简洁可靠
2. **覆盖 `_validate_key()`**：port_scan 是无认证渠道中唯一需要验证的——验证 nmap 工具可用性。失败抛 `ChannelPermanentError`，使 `validate()` 返回 False 并设置 `disabled=True`（S101）
3. **nmap_path 通过构造函数注入**：默认 `"nmap"`，支持绝对路径配置（S102）
4. **port_string 通过 kwargs 传递**：端口列表由上层准备，渠道层只负责扫描
5. **historical_ports 通过 kwargs 传递**：历史端口对比由上层传入数据
6. **nmap 扫描参数**：`-sT -T4 -Pn --open`，与 legacy 一致
7. **渠道层只负责单 IP 扫描**（brainstorming 确认）：批量 IP 并发调度由上层 Layer 3/4 处理
8. **本期不实现 load_port_list 和 extract_historical_ports**：这些是上层逻辑，不属于渠道层
9. **构造函数注入 timeout**：不依赖 Settings，默认 30.0 秒

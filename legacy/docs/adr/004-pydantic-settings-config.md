# ADR-004: Pydantic Settings 配置管理

## 状态

已采纳

## 上下文

项目有大量可配置项：API Key、Cookie、查询间隔、超时、渠道开关等。需要一种类型安全、可验证的配置管理方案。

## 决策

使用 **Pydantic Settings** 进行配置管理，环境变量统一 `IP_` 前缀。

### 配置类继承体系

```python
BaseIPSettings
  ├── Settings           # 通用（存储路径、项目名）
  ├── FofaSettings       # API Key + 超时 + 延迟
  ├── IpinfoSettings     # Token + 超时 + 延迟
  ├── AizhanSettings     # Cookie + 超时 + 延迟
  ├── ChinazSettings     # Cookie + 超时 + 延迟
  ├── WhoisSettings      # 超时 + 延迟
  ├── RdnsSettings       # 超时 + 延迟
  ├── ZoomeyeSettings    # API Key + 超时 + 延迟
  ├── SslCertSettings    # 端口 + 超时 + 延迟
  ├── TraceIPSettings    # 7 阶段渠道开关 + 端口扫描
  ├── IPDomainLookupSettings  # 6 渠道开关
  └── IpTaggerSettings   # 配置目录
```

### 管理工具

通过 `tools/config_tool.py` 管理，禁止直接编辑 `.env`：

```bash
python tools/config_tool.py set IP_FOFA_API_KEY "xxx"
python tools/config_tool.py status    # 查看配置状态
python tools/config_tool.py check     # 检查完整性
```

### 安全措施

- 路径遍历校验：`_validate_path_no_traversal()`
- 保留名称校验：`FORBIDDEN_STORAGE_DIRS = {'ip_domain_lookup', 'trace_ip'}`
- 简单名称校验：`_validate_simple_name()` 禁止路径分隔符

## 理由

1. **类型安全** — 自动类型转换和验证
2. **环境变量集成** — `IP_` 前缀自动映射
3. **文档化** — Field description 即配置文档
4. **多配置类** — 按渠道/场景分离，避免单一大类

## 后果

**优势：**
- 配置错误在启动时即可发现
- API Key 缺失时给出明确错误
- 新增配置项只需添加 Field

**劣势：**
- 配置类数量较多（11 个），但每个类职责单一
- 环境变量命名较长（如 `IP_TRACE_IP_PHASE5_PORT_SCAN_ENABLED`）

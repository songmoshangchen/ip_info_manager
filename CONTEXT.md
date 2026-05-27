# IP Info Manager - 项目上下文

## 项目定位

IP 信息管理工具，批量采集、存储、查询 IP 的多维度情报。面向安全分析师，支撑 IP 溯源、域名反查等安全运营场景。

正在从 legacy 代码重构为新架构（从内向外：store → channel → batch → pipeline）。

## 技术栈

| 层面 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.12+ | |
| 配置 | pydantic-settings V2 | `ChannelConfig` 基类，`.env` 读取 |
| 存储 | JSON 文件 | 无数据库，按 IP + 渠道组织 |
| HTTP | requests | |
| HTML 解析 | beautifulsoup4 | 爱站/站长之家 |
| 测试 | pytest | `-p no:dash` |

## 核心领域概念

| 术语 | 定义 |
|------|------|
| **Channel（渠道）** | 一个数据采集源（API 或爬虫），如 fofa_host、rdns_ptr |
| **ChannelProtocol** | 渠道结构化接口：`channel_name` + `validate()` + `fetch()` |
| **ChannelRegistry** | 渠道注册表，统一管理注册/查找/验证/查询 |
| **Store** | IP 数据的读写层，基于 JSON 文件 |
| **BaseBatchQuery** | 批量查询具体类，构造函数注入渠道，含熔断保护 |
| **ProgressTracker** | 断点续查协议，File 实现持久化到 .progress 文件 |
| **Pipeline** | 多阶段流水线（未开始重构） |

## 当前架构

```
src/ip_info/
├── store/       # 存储层 ✅ — IPDataWriter/IPDataReader 协议 + JSON 实现
├── channel/     # 渠道层 ✅ — BaseChannelAdapter + 10 个渠道 + 配置系统
├── batch/       # 批量查询层（核心✅, CLI 待做）— BaseBatchQuery + ProgressTracker
└── pipeline/    # 流水线层（未开始）
```

## 重构进度

| 层级 | 状态 | 说明 |
|------|------|------|
| store | ✅ 完成 | IPDataWriter/Reader 协议 + InMemory/JSON 实现 |
| channel | ✅ 完成 | BaseChannelAdapter + 10 渠道 + ChannelConfig 配置系统 |
| batch 核心 | ✅ 完成 | BaseBatchQuery + BatchResult + ProgressTracker |
| batch CLI | 🚧 待做 | scripts/ 目录 + 9 个 CLI 脚本 + RDNS 并发 |
| pipeline | ⬜ 未开始 | PhaseRunner + ProgressManager + 各 phase |

## 关键设计决策

- **依赖注入**：构造函数注入所有依赖，不依赖全局设置
- **协议驱动**：先定义 Protocol，再实现测试替身和真实实现
- **配置优先级**：显式参数 > .env > 代码默认值（pydantic-settings）
- **日志**：各层 `logging.getLogger(__name__)`，调用方配置 handler
- **测试**：面向结果，不访问私有属性
- **熔断保护**：连续 N 次 ChannelError 后自动停止查询

## 渠道清单

| 渠道 | 适配器 | 必填配置 | default_delay |
|------|--------|---------|---------------|
| rdns_ptr | RdnsPtrChannel | 无 | 0.1 |
| ipinfo_api | IpinfoApiChannel | token | 1.2 |
| ipinfo_free | IpinfoFreeChannel | 无 | 1.2 |
| fofa_host | FofaHostChannel | key | 2.0 |
| fofa_search | FofaSearchChannel | key | 2.0 |
| aizhan | AizhanChannel | cookie | 2.0 |
| chinaz | ChinazChannel | 无（可选 cookie） | 2.0 |
| whois_query | WhoisQueryChannel | 无 | 0.5 |
| ssl_cert | SslCertChannel | 无 | 0.5 |
| port_scan | PortScanChannel | 无 | 0 |

## 配置体系

所有渠道配置通过 `src/ip_info/channel/config.py` 管理，基于 pydantic-settings：

```
ChannelConfig（env_prefix="IP_", .env 读取）
  ├── RdnsConfig
  ├── IpInfoApiConfig（token 必填）
  ├── IpInfoFreeConfig
  ├── FofaHostConfig（key 必填）
  ├── FofaSearchConfig（key 必填）
  ├── AizhanConfig（cookie 必填）
  ├── ChinazConfig（cookie 可选）
  ├── WhoisConfig
  ├── SslCertConfig
  ├── ZoomEyeConfig
  └── PortScanConfig
```

## 编码约定

- 测试运行：`python -m pytest tests/ -q`
- 进度文件：`{prefix}.{channel}.progress`
- 日志文件：`data/logs/{channel_name}.log`
- 环境配置：`.env`（真实）、`.env.example`（模板）、`tests/.env.test`（测试 mock）

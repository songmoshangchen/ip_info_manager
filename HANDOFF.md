# Handoff 文档 — ip_info_manager 重构项目

> 生成时间: 2026-05-26（第十四次更新）
> 项目路径: `E:\12_trae_skills\ip_info_manager`

---

## 一、已完成工作总览

### 1. 存储层 ✅
- `src/ip_info/store/` — IPDataWriter/IPDataReader/DomainCache 协议 + JSON/InMemory/SQLite 实现
- SqliteDomainCache: threading.local + WAL 模式 + INSERT OR REPLACE

### 2. 渠道层 ✅
- `src/ip_info/channel/` — BaseChannelAdapter + 10 个渠道 + ChannelConfig 配置系统
- **default_delay 已修复**：所有 9 个 Channel 的 default_delay 从 Config 读取（不再硬编码）
- timeout 也从 Config 读取（一直正常）
- fofa key: `d6741fd4f6cae5736ea8b640ee242f51`

### 3. 通用工具层 ✅
- `src/ip_info/utils/` — `load_ips()`（含 IP 格式校验）+ ProgressTracker 协议 + 实现

### 4. 批量查询层 ✅
- BaseBatchQuery + run_concurrent + BatchRunner Protocol
- 13 个 batch CLI 脚本

### 5. Processors 层 ✅
- **processors/core/base.py**: BaseProcessor 基类
- **tagger/classifier/dns_verify**: 均继承 BaseProcessor

### 6. Pipeline 编排框架 ✅
- Phase Protocol + PhaseResult + Pipeline 类
- Phase 1-4 具体实现完成
- Phase 2-3 之间有 filter_ips_by_classification

### 7. 分渠道断点续传 ✅
- ProgressTracker 协议: `is_processed(ip, channel="")` / `mark_processed(ip, channel="")`
- FileProgressTracker（deprecated）+ InMemoryProgressTracker + **SqliteProgressTracker**

### 8. SqliteProgressTracker ✅ (本会话完成)
- 表结构: `progress(ip TEXT, channel TEXT, PRIMARY KEY(ip, channel))`
- 缓冲区 + flush 批量写入
- threading.local + WAL 模式，并发安全
- 支持 `import_from` 从旧 FileProgressTracker 文件导入
- run_concurrent / BaseBatchQuery 新增 `flush_interval` 参数

### 9. run_pipeline.py 增强 ✅ (本会话完成)
- `--skip` 参数支持临时禁用渠道
- 使用 SqliteProgressTracker 替代 FileProgressTracker

### 10. 测试现状
- **710 个测试全部通过**
- 运行命令：`python -m pytest tests/unit/ -q`

---

## 二、待处理 Issue（新建）

Issue 存放在 `issues/` 目录（已加入 .gitignore）。

### Issue 1: 临时 IP 快速查询脚本
- **文件**: `issues/001-quick-query-script.md`
- **目标**: 创建 `scripts/quick_query.py`
- **功能**: 命令行直接传 IP，自动生成独立输出目录，不与已有数据冲突
- **用法**: `python scripts/quick_query.py 8.8.8.8 1.1.1.1 --phase 1,3 --skip aizhan`

### Issue 2: IP-域名映射验证脚本
- **文件**: `issues/002-verify-ip-domain-mapping.md`
- **目标**: 创建 `scripts/verify_mapping.py`
- **功能**: 给定 IP-域名对，验证域名是否仍然解析到该 IP
- **输入方式**: 命令行 IP-域名对 / 文件 / 已有 ip_data.json
- **复用**: `processors/dns_verify/verifier.py` 的 `verify_one()` 函数

---

## 三、架构速览

```
src/ip_info/
  ├── utils/                      # 通用工具 ✅
  │   ├── progress.py             # ProgressTracker 协议 + File/InMemory/Sqlite 实现
  │   └── load_ips.py             # IP 加载 + 格式校验 ✅
  ├── store/                      # 存储层 ✅
  │   ├── protocols.py            # IPDataWriter/IPDataReader/DomainCache 协议
  │   ├── json_store.py           # JSON 实现（progress_tracker 返回 SqliteProgressTracker）
  │   ├── in_memory.py            # InMemory 实现
  │   └── sqlite_cache.py         # SqliteDomainCache
  ├── channel/                    # 渠道层 ✅ (10 个渠道)
  │   ├── config.py               # ChannelConfig（pydantic-settings, .env 读取）
  │   └── *.py                    # 各渠道（default_delay 从 Config 读取）
  ├── processors/                 # 非渠道批量处理器 ✅
  │   ├── core/base.py            # BaseProcessor 基类
  │   ├── tagger/                 # BatchTagger
  │   ├── classifier/             # BatchClassifier
  │   └── dns_verify/             # BatchDnsVerify + verifier.py（verify_one）
  ├── batch/                      # 批量查询层 ✅
  │   └── core/
  │       ├── query.py            # BaseBatchQuery（含 flush_interval）
  │       └── concurrent.py       # run_concurrent（含 flush_interval）
  └── pipeline/                   # 流水线层 ✅
      ├── phase.py                # Phase Protocol + PhaseResult
      ├── pipeline.py             # Pipeline 编排器
      ├── filter_ips.py           # filter_ips_by_classification
      └── phases/
          ├── phase1_basic.py     # BasicCollectPhase
          ├── phase2_classify.py  # ClassifyTagPhase
          ├── phase3_deep.py      # DeepQueryPhase
          └── phase4_verify_scan.py # VerifyScanPhase
scripts/
  └── run_pipeline.py             # 完整流水线（支持 --skip 渠道禁用）
issues/                           # Issue 跟踪（.gitignore）
  ├── 001-quick-query-script.md
  └── 002-verify-ip-domain-mapping.md
```

---

## 四、关键文件索引

| 文件 | 说明 |
|------|------|
| `src/ip_info/utils/progress.py` | ProgressTracker 协议 + Sqlite/File/InMemory 三种实现 |
| `src/ip_info/processors/core/base.py` | BaseProcessor 基类（含 _flush_progress） |
| `src/ip_info/batch/core/concurrent.py` | run_concurrent（含 flush_interval） |
| `src/ip_info/batch/core/query.py` | BaseBatchQuery（含 flush_interval） |
| `src/ip_info/processors/dns_verify/verifier.py` | verify_one() — 单域名 DNS 验证（Issue 2 需要复用） |
| `src/ip_info/channel/config.py` | ChannelConfig — pydantic-settings 从 .env 读取 |
| `scripts/run_pipeline.py` | 完整流水线脚本（--skip 支持） |

---

## 五、提交记录（最新）

```
7045f32 feat(progress): 实现 SqliteProgressTracker + flush_interval 批量写入
cdbec0f test(progress): 分渠道断点续传测试 + Phase delay/tracker 测试
4319294 refactor(progress): 分渠道断点续传 + processors/core 基类抽取
```

**未提交**: Channel default_delay 修复（9 个文件）、run_pipeline.py --skip 支持、.gitignore 更新

---

## 六、Git 提交规范

- 中文翻译的 conventional commit 格式
- PowerShell 用分号 `;` 分隔命令

---

## 七、建议的下一步技能

- **tdd**: 用 TDD 实现 Issue 1（quick_query.py）或 Issue 2（verify_mapping.py）
- **git-commit**: 先提交未提交的 default_delay 修复和 --skip 支持

---

## 八、0518-0524 任务命令

用户需要继续跑 0518-0524 的 IP 列表：

```powershell
cd E:\12_trae_skills\ip_info_manager; python scripts/run_pipeline.py "E:\07数据\xwechat_files\wxid_ryizq74rvwt022_8600\msg\file\2026-05\0518-0524IP.txt" data/0518-0524
```

可选跳过渠道：
```powershell
--skip aizhan,fofa_host,port_scan
```

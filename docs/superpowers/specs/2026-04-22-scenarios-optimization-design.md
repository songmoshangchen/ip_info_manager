# Scenarios 模块优化设计

日期: 2026-04-22
状态: 已批准

## 背景

`scenarios/trace_ip.py` 是溯源 IP 处理流水线的核心文件（657 行），承担了所有职责：流水线编排、分类引擎、进度管理、报告生成、CLI 参数解析。随着项目发展，该文件暴露出以下问题：

1. **单文件过大** — 所有逻辑堆在一个 `TraceIPPipeline` 类中，难以维护和测试
2. **全部使用 `print()`** — 项目已有 `logger_utils.py` 日志系统，但 scenarios 未接入
3. **分类器与流水线紧耦合** — 分类逻辑无法独立使用或测试
4. **IPWriter 性能隐患** — 每次 `add_or_update_ip` 都全量读写 JSON 文件
5. **缺乏错误处理** — 网络请求、文件操作没有 try/except
6. **无并行能力** — Phase 1/3 逐个渠道顺序查询，效率低

## 目标

- **结构重构**：拆分为独立模块，职责单一
- **性能优化**：批量写入替代逐次全量读写
- **功能增强**：跨渠道并行查询、渠道级超时控制
- **日志集成**：统一 logging 替代 print
- **可扩展性**：Reporter 可替换（未来支持 HTML/Word）

## 约束

- 数据存储保持 JSON 格式（不迁移 SQLite）
- 并行策略仅跨渠道并行（同一 IP 的多个渠道同时查询），不做多 IP 并行
- 同一渠道内保持顺序执行，遵守限速规则
- 允许 CLI 接口破坏性变更

## 模块结构

```
scenarios/
├── __init__.py                  # 公共 API（导出各场景入口）
│
├── trace_ip/                    # 溯源 IP 场景
│   ├── __init__.py              # 导出 TraceIPPipeline
│   ├── trace_ip.py              # CLI 入口（argparse + main，~80 行）
│   ├── classifier.py            # 分类引擎（纯逻辑，无 IO，~120 行）
│   ├── progress.py              # 进度管理 + 批量写入（~150 行）
│   ├── reporter.py              # 报告生成（抽象基类 + 文本实现，~100 行）
│   ├── pipeline.py              # 流水线编排 + 并行调度（~250 行）
│   └── classifiers/
│       ├── builtin_rules.json   # 不变
│       └── custom_rules.json    # 不变
│
├── future_scenario/             # 未来其他场景
│   └── ...
```

每个场景自包含，互不干扰。`scenarios/` 作为场景容器，未来可添加共享工具。

## 模块详细设计

### classifier.py — 分类引擎

纯逻辑模块，不依赖任何 IO 操作。

```python
@dataclass
class ClassifyResult:
    category: str
    label: str
    description: str
    matched_by: list = field(default_factory=list)
    need_deep_query: bool = True
    classify_time: str = ""

class IPClassifier:
    def __init__(self, builtin_path: str, custom_path: Optional[str] = None):
        """加载并合并内置规则和自定义规则"""
        self._rules = self._load_and_merge_rules(builtin_path, custom_path)

    def classify(self, ip_data: dict) -> ClassifyResult:
        """对单个 IP 数据进行分类，返回 ClassifyResult"""

    @property
    def categories(self) -> list[str]:
        """返回所有分类名称"""
```

设计要点：
- 返回 `dataclass` 而非 dict，类型安全
- 规则在 `__init__` 中一次性加载
- `classify()` 只接收 `ip_data`，纯函数式
- `_extract_field` 和 `_match_pattern` 保持现有逻辑不变
- 规则合并使用 `OrderedDict`，内置规则优先

### progress.py — 进度管理与批量写入

```python
class ProgressManager:
    def __init__(self, output_dir: str, prefix: str):
        self._buffer: dict[int, set[str]] = {}
        self._dirty = False

    def load_completed(self, phase: int) -> set[str]:
        """从磁盘加载已完成的 IP 集合，缓存到内存"""

    def record(self, ip: str, phase: int):
        """记录 IP 完成（先写内存缓冲）"""

    def flush(self):
        """将缓冲区数据批量写入磁盘"""

    def is_phase_done(self, phase: int) -> bool:
    def mark_phase_done(self, phase: int):
    def clear_from(self, phase: int):
        """清除指定阶段及之后的所有标记和进度"""

class BatchIPWriter:
    def __init__(self, writer: IPWriter):
        self._writer = writer
        self._batch: dict[str, dict] = {}

    def __enter__(self) -> 'BatchIPWriter':
        """进入批量模式"""

    def __exit__(self, *args):
        """安全退出，自动 flush"""

    def add(self, ip: str, channel: str, data: dict):
        """缓存写入请求"""

    def flush_batch(self):
        """一次性将所有缓存数据写入 JSON 文件"""
        # 加载当前数据 -> 合并缓存 -> 写入文件
```

设计要点：
- ProgressManager 内存缓存已完成 IP，定期 flush
- 使用 `atexit` 注册安全退出钩子，异常退出时保存进度
- BatchIPWriter 支持 `with` 上下文管理器
- 一个 IP 的多个渠道数据合并后一次性写入
- Phase 1：每个 IP 查完 ipinfo + rdns 后 flush 一次
- Phase 3：每个 IP 查完 aizhan + chinaz + fofa 后 flush 一次

### reporter.py — 报告生成（可替换）

```python
class BaseTraceReporter(ABC):
    @abstractmethod
    def record_phase(self, phase_num: int, stats: dict): ...

    @abstractmethod
    def generate_summary(self, ips: list, report_data: dict): ...

    @abstractmethod
    def save_report(self): ...

class TextTraceReporter(BaseTraceReporter):
    """当前实现：终端文本 + JSON 文件"""
```

Pipeline 通过构造函数接收 Reporter，默认使用 `TextTraceReporter`：
```python
pipeline = TraceIPPipeline(ip_file, config, reporter=None)
# reporter 为 None 时自动创建 TextTraceReporter
```

未来添加 HTML/Word 报告只需实现新的 `BaseTraceReporter` 子类。

### pipeline.py — 流水线编排

```python
class TraceIPPipeline:
    def __init__(self, ip_file: str, config: dict, reporter: BaseTraceReporter = None):
        self._classifier = IPClassifier(...)
        self._progress = ProgressManager(...)
        self._reporter = reporter or TextTraceReporter(...)
        self._batch_writer = BatchIPWriter(IPWriter())
        self._ips = load_ips(ip_file)
        self._config = config

    def run(self):
        """主流程：按阶段执行"""

    def _phase1_collect_basic(self):
        """并行采集 ipinfo + rdns"""
        for ip in pending_ips:
            results = self._query_channels_parallel(ip, [
                ('ipinfo_api', fetch_ipinfo, ipinfo_settings, timeout),
                ('rdns_ptr', fetch_rdns_ptr, rdns_settings, timeout),
            ])
            ...

    def _phase3_deep_query(self):
        """并行采集 aizhan + chinaz + fofa"""
        for ip in pending_ips:
            results = self._query_channels_parallel(ip, [
                ('aizhan', fetch_aizhan, aizhan_settings, timeout),
                ('chinaz', fetch_chinaz, chinaz_settings, timeout),
                ('fofa', fetch_fofa_host_detail, fofa_settings, timeout),
            ])
            ...

    def _query_channels_parallel(self, ip, channel_specs) -> dict:
        """并行查询多个渠道，返回 {channel_name: data}"""
        # 使用 concurrent.futures.ThreadPoolExecutor
        # 超时的渠道返回错误标记而非阻塞
```

### 并行查询策略

**仅跨渠道并行，IP 之间顺序执行：**

```
处理 IP 1.2.3.4:
  Thread-1: 查 ipinfo_api (限速 1.2s)
  Thread-2: 查 rdns_ptr   (限速 0.1s)
  → 等待全部完成或超时 → flush_batch + record_progress
  → 等待最大 delay → 下一个 IP
```

- 使用 `concurrent.futures.ThreadPoolExecutor`
- 每个渠道查询函数传 `delay=0`，由 pipeline 统一控制 IP 间等待时间
- 渠道级超时：CLI `--channel-timeout` 参数控制（默认 0 = 不限时），优先级高于 `.env` 中的 `IP_CHANNEL_TIMEOUT`
- 超时的渠道返回 `{'raw_error': 'channel timeout after Ns'}`，不影响其他渠道
- 超时后对应的 future 被 `cancel()`，不会继续占用资源

### trace_ip.py — CLI 入口

```python
def main():
    parser = argparse.ArgumentParser(...)
    # 阶段控制
    parser.add_argument('--from-phase', type=int, choices=[1, 2, 3, 4])
    parser.add_argument('--only-phase', type=int, choices=[1, 2, 3, 4])
    # 分类规则
    parser.add_argument('--custom-rules', type=str)
    parser.add_argument('--no-custom-rules', action='store_true')
    # 输出控制
    parser.add_argument('--output-dir', type=str)
    parser.add_argument('--no-deep-query', action='store_true')
    # 渠道超时
    parser.add_argument('--channel-timeout', type=int, default=0,
                        help='单渠道查询超时秒数（0=不限时）')

    args = parser.parse_args()
    config = {
        'from_phase': args.from_phase,
        'only_phase': args.only_phase,
        'custom_rules': args.custom_rules,
        'no_custom_rules': args.no_custom_rules,
        'output_dir': args.output_dir,
        'output_dir_explicit': args.output_dir is not None,
        'no_deep_query': args.no_deep_query,
        'channel_timeout': args.channel_timeout,
    }
    pipeline = TraceIPPipeline(args.ip_file, config)
    pipeline.run()
```

## 日志集成

所有模块使用 `logging.getLogger('ip_info_manager.scenarios.trace_ip')`。

| 级别 | 内容 |
|------|------|
| INFO | 阶段开始/结束、进度摘要、分类统计 |
| DEBUG | 每个 IP 的查询详情、分类匹配过程 |
| WARNING | 渠道查询失败、超时、进度文件损坏 |
| ERROR | 文件读写失败、配置错误 |

终端保留关键进度信息，通过 logger 输出。

## 错误处理

**渠道查询级别：** 单个渠道失败不影响其他渠道
```python
try:
    data = fetch_ipinfo(ip, token)
except Exception as e:
    logger.warning(f"IP {ip} ipinfo 查询失败: {e}")
    data = {'raw_error': str(e)}
```

**文件操作级别：** 损坏的进度文件自动重建
```python
try:
    progress = self._progress.load_completed(phase)
except json.JSONDecodeError:
    logger.warning("进度文件损坏，将从空进度开始")
    progress = set()
```

**Pipeline 级别：** KeyboardInterrupt 优雅退出
```python
try:
    pipeline.run()
except KeyboardInterrupt:
    logger.info("用户中断，正在保存进度...")
    pipeline._progress.flush()
    pipeline._batch_writer.flush_batch()
    logger.info("进度已保存，可使用 --from-phase 续查")
```

## 迁移策略

1. 创建 `scenarios/trace_ip/` 目录
2. 逐个创建新模块：classifier.py → progress.py → reporter.py → pipeline.py → trace_ip.py
3. 将 `scenarios/classifiers/` 移入 `scenarios/trace_ip/classifiers/`
4. 删除旧的 `scenarios/trace_ip.py`
5. 更新 `scenarios/__init__.py` 导出新入口
6. 验证功能正确性

## 依赖关系

```
trace_ip.py → pipeline.py → classifier.py
                           → progress.py (ProgressManager + BatchIPWriter)
                           → reporter.py
                           → ../channel/*.py (fetch 函数)
                           → ../config.py (Settings)
                           → ../reader.py (IPReader)
                           → ../writer.py (IPWriter)
```

无循环依赖，每个叶子模块可独立测试。

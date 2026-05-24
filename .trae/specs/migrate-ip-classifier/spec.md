# 迁移 IP 自动分类模块 Spec

## Why

将遗留代码 `legacy/scenarios/trace_ip/classifier.py` 迁移到新架构，作为 `processors/classifier/` 模块，实现 BatchRunner Protocol。

## What Changes

- 新建 `src/ip_info/processors/classifier/` 目录，包含 rules.py、engine.py、runner.py
- 新建 `src/ip_info/batch/batch_classifier.py` CLI 脚本入口
- 迁移配置文件 `legacy/scenarios/trace_ip/classifiers/` → `config/classifier/`
- 新建 `tests/unit/processors/test_classifier_*.py` 测试

## Impact

- Affected specs: BatchRunner Protocol（新增一个实现者）
- Affected code: `src/ip_info/processors/classifier/`（新建）、`src/ip_info/batch/batch_classifier.py`（新建）、`config/classifier/`（迁移）

## ADDED Requirements

### Requirement: 规则加载与合并 (rules.py)

系统 SHALL 提供 `load_rules()` 函数，加载并合并 builtin + custom 规则：

#### Scenario: 正常加载
- **WHEN** 调用 `load_rules(builtin_path, custom_path=None)`
- **THEN** 返回 OrderedDict，builtin 在前，custom 在后

#### Scenario: custom 规则合并
- **WHEN** 提供 custom_path 且文件存在
- **THEN** custom 规则追加到 builtin 之后

#### Scenario: custom 文件不存在
- **WHEN** custom_path 指向不存在的文件
- **THEN** 仅返回 builtin 规则，不报错

#### Scenario: 空文件
- **WHEN** 规则文件为空
- **THEN** 返回空 OrderedDict

### Requirement: IPClassifier 匹配引擎 (engine.py)

系统 SHALL 提供 `IPClassifier` 类，基于规则对 IP 数据进行分类：

#### Scenario: suffix 匹配
- **WHEN** 规则 type="suffix" 且字段值以 match 结尾
- **THEN** 返回该分类

#### Scenario: contains 匹配
- **WHEN** 规则 type="contains" 且字段值包含 match
- **THEN** 返回该分类

#### Scenario: prefix 匹配
- **WHEN** 规则 type="prefix" 且字段值以 match 开头
- **THEN** 返回该分类

#### Scenario: exact 匹配
- **WHEN** 规则 type="exact" 且字段值等于 match
- **THEN** 返回该分类

#### Scenario: regex 匹配
- **WHEN** 规则 type="regex" 且字段值匹配正则
- **THEN** 返回该分类

#### Scenario: 无匹配
- **WHEN** 没有任何规则命中
- **THEN** 返回 category="other"

#### Scenario: first-match 策略
- **WHEN** 多个规则都能匹配
- **THEN** 返回第一个命中的分类

#### Scenario: 大小写不敏感
- **WHEN** 字段值和 match 大小写不同
- **THEN** 仍然匹配成功

#### Scenario: 嵌套字段路径
- **WHEN** field 为 "rdns_ptr.hostname"
- **THEN** 从嵌套 dict 中提取值

### Requirement: BatchClassifier 批量处理器 (runner.py)

系统 SHALL 提供 `BatchClassifier` 类，实现 `BatchRunner` Protocol：

#### Scenario: 正常批量分类
- **WHEN** 调用 `BatchClassifier(ips, writer, reader, rules_dir).run()`
- **THEN** 从 reader 读取每个 IP 的数据 → 规则匹配 → writer 写入 "classifier" 渠道 → 返回 BatchResult

#### Scenario: 跳过无数据 IP
- **WHEN** reader 中没有某 IP 的数据
- **THEN** 跳过该 IP，计入 skip_count

#### Scenario: 每次全量重处理
- **WHEN** IP 已有 classifier 数据
- **THEN** 仍然重新分类，覆盖旧结果

#### Scenario: 空输入
- **WHEN** IP 列表为空
- **THEN** 返回 BatchResult(success_count=0, skip_count=0)

### Requirement: CLI 脚本入口

系统 SHALL 提供 `python -m ip_info.batch.batch_classifier` 命令行入口：

#### Scenario: 基本用法
- **WHEN** 执行 `python -m ip_info.batch.batch_classifier ip_file --storage-file data/test.json`
- **THEN** 加载 IP 文件，运行 BatchClassifier，输出结果摘要

### Requirement: 配置文件迁移

系统 SHALL 将 `legacy/scenarios/trace_ip/classifiers/` 目录复制到 `config/classifier/`。

## REMOVED Requirements

### Requirement: ClassifyResult dataclass
**Reason**: 改用普通 dict 构建，简化实现
**Migration**: 分类结果直接构建为 dict 写入 writer

### Requirement: _builtin_count 跟踪
**Reason**: 简化规则来源标记
**Migration**: 在 load_rules 时标记每条规则来源

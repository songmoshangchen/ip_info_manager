# 测试文档

运行命令：`python -m pytest tests/ -v -p no:dash`

## 文件索引

| 文件 | 覆盖模块 | 测试数 |
|------|---------|--------|
| `test_progress.py` | `scenarios/trace_ip/progress.py` | 11 |
| `test_in_memory_writer.py` | `protocols.py` (InMemoryIPWriter) | 9 |
| `test_in_memory_reader.py` | `protocols.py` (InMemoryIPReader) | 17 |
| `test_protocol_conformance.py` | `writer.py` + `reader.py` 协议兼容性 | 8 |
| `test_channel_base.py` | `channel/base.py` + `ChannelFetcher` Protocol | 10 |
| `test_channel_protocol.py` | `ChannelProtocol` + 适配器 + InMemoryChannel | 36 |
| `test_channel_registry.py` | `ChannelRegistry` + `create_default_registry` + 7 适配器 | 46 |
| `test_batch_run.py` | `BaseBatchQuery.run()` + 9 个迁移验证 | 36 |
| `test_trace_utils.py` | `scenarios/trace_ip/trace_utils.py` | 26 |
| `test_phase_runner.py` | `scenarios/trace_ip/phase_runner.py` | 10 |
| `test_config.py` | `config.py` Pydantic V2 迁移 | 25 |
| `test_pipeline_registry.py` | ChannelRegistry + Pipeline 集成模式 | 8 |

## test_in_memory_writer.py

`InMemoryIPWriter` 是 `IPDataWriter` + `IPDataReader` Protocol 的纯内存测试替身。`get_all()` 不属于 Protocol 接口。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| 1 | `test_add_or_update_ip_creates_new_ip_record` | 新 IP + 新渠道 → 创建含 `ip` 字段的记录 |
| 2 | `test_add_or_update_ip_appends_channel_to_existing_ip` | 已有 IP + 新渠道 → 追加，不覆盖已有渠道 |
| 3 | `test_add_or_update_ip_overwrites_existing_channel` | 同名渠道 → 整体替换（非 merge），旧字段消失 |
| 4 | `test_add_or_update_ip_returns_true` | 写入返回 `True` |
| 5 | `test_delete_ip_removes_entire_record` | 删 IP → 整个记录消失，其他 IP 不受影响 |
| 6 | `test_delete_ip_returns_false_for_nonexistent` | 删不存在的 IP → 返回 `False` |
| 7 | `test_delete_channel_removes_only_specified_channel` | 删已有 IP 的已有渠道 → 只删该渠道 |
| 8 | `test_delete_channel_returns_false_for_nonexistent_ip` | IP 不存在 → 返回 `False` |
| 9 | `test_delete_channel_returns_false_for_nonexistent_channel` | 渠道不存在 → 返回 `False` |

## test_in_memory_reader.py

`InMemoryIPReader` 通过 dict 初始化，可与 `InMemoryIPWriter.get_all()` 配合。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| 1-3 | `get_ip_data` | 已有/不存在/空存储 |
| 4-6 | `get_channel_data` | 已有/不存在IP/不存在渠道 |
| 7-8 | `list_all_ips` | 返回所有/空列表 |
| 9-11 | `list_ip_channels` | 排除ip字段/不存在/无渠道 |
| 12-17 | `search_ips_by_channel` | 按渠道/key/value/不存在/不匹配 |

## test_protocol_conformance.py

验证 `IPWriter`/`IPReader` 满足 Protocol（isinstance + 行为测试）。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| 1-2 | Writer 协议 | isinstance + 方法存在 |
| 3-4 | Reader 协议 | isinstance + 方法存在 |
| 5-7 | Writer 行为 | 通过 Protocol 类型注解写/删IP/删渠道 |
| 8 | Reader 行为 | 通过 Protocol 类型注解读取全部 5 个方法 |

## test_channel_base.py

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| 1-2 | ChannelFetcher Protocol | 函数满足协议/Protocol 是 callable |
| 3-5 | apply_delay | delay=0不阻塞/delay>0等待/delay<0不阻塞 |
| 6-10 | format_output | 补充query_time/不覆盖/保留字段/空字典/错误字典 |

## test_channel_protocol.py

完整版 `ChannelProtocol`（`channel_name` + `validate()` + `fetch()`），3 个适配器 + InMemoryChannel 测试替身。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **Protocol 结构** | | |
| 1 | channel_name 注解存在 | `__annotations__` 包含 channel_name |
| 2 | validate 方法存在 | hasattr 检查 |
| 3 | fetch 方法存在 | hasattr 检查 |
| 4 | runtime_checkable | 满足协议的类通过 isinstance |
| 5 | 不满足协议的类 | isinstance 返回 False |
| **InMemoryChannel** | | |
| 6-7 | channel_name | 默认值/自定义 |
| 8-9 | validate | 默认 True/配置 False |
| 10 | fetch 返回配置结果 | dict 返回 |
| 11 | fetch 记录调用 | (ip, kwargs) 元组列表 |
| 12-13 | fetch 不可变性 | 不修改原始 dict/每次返回副本 |
| **FofaHostChannel 适配器** | | |
| 14 | 满足 ChannelProtocol | isinstance 检查 |
| 15 | channel_name | = 'fofa_host' |
| 16-18 | validate | 成功→True/exit→False/异常→False |
| 19 | fetch 委托 | 调用 fetch_channel(ip, **kwargs) |
| **AizhanChannel 适配器** | | |
| 20 | 满足 ChannelProtocol | isinstance 检查 |
| 21 | channel_name | = 'aizhan' |
| 22-24 | validate | 成功→True/exit→False/异常→False |
| 25 | fetch 委托 | 调用 fetch_channel(ip, **kwargs) |
| **PortScanChannel 适配器** | | |
| 26 | 满足 ChannelProtocol | isinstance 检查 |
| 27 | channel_name | = 'port_scan' |
| 28-30 | validate | 引擎可用→True/不可用→False/异常→False |
| 31 | fetch 委托 | 调用 fetch_channel(ip, **kwargs) |
| **集成测试** | | |
| 32 | 多渠道通过协议接口 | isinstance + fetch 返回 dict |
| 33 | validate+fetch 工作流 | 先验证再查询 |
| 34 | 验证失败渠道 | validate 返回 False |
| 35 | Protocol 类型注解使用 | 函数参数类型为 ChannelProtocol |
| 36 | 验证失败返回错误 | raw_error + error_message |

## test_trace_utils.py

9 个共享领域函数 + 2 个常量，从 reporter/excel_exporter 提取。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| 1-4 | is_china_ip | country_code=CN/country含China/非中国/无ipinfo |
| 5-8 | extract_all_domains | 含source+title/跨渠道去重/无成功数据/跳过空域名 |
| 9-11 | extract_fofa_ports | 字典列表/报错/无fofa |
| 12-13 | has_domains | True/False |
| 14-15 | has_ports | True/False |
| 16-19 | trace_priority | P1/P2/P2(端口)/P4 |
| 20-22 | cat_display | 含note/other/无note |
| 23-25 | trace_action | ICP备案/WHOIS/公开信息检索 |
| 26 | sort_key | 排序键降序 |

## test_phase_runner.py

PhaseRunner 通用循环，封装"进度-查询-写入"骨架。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| 1 | init 存储配置 | phase_num + channels 正确存储 |
| 2 | 从 store 检测已处理 IP | 所有渠道都有数据 → 标记为已处理 |
| 3 | 需要所有渠道才标记已处理 | 缺少任一渠道 → 不标记 |
| 4 | 空存储无已处理 | 空数据 → 返回空集合 |
| 5 | 排除已处理 IP | pending = all - processed |
| 6 | 全部已处理返回空 | 无待处理 IP |
| 7 | 合并进度文件 IP | progress_ips + store_processed |
| 8 | run 调用 query_fn | 每个 pending IP 都调用一次 |
| 9 | run 跳过已处理 | 已处理 IP 不调用 query_fn |
| 10 | run 写入结果到 store | 查询结果通过 store.add_or_update_ip 写入 |

## test_channel_registry.py

`ChannelRegistry`（注册/查找/列表/验证/fetch）+ `create_default_registry()` 工厂函数 + 7 个渠道适配器。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **ChannelRegistry.register** | | |
| 1 | 注册渠道 | get 返回同一实例 |
| 2 | 注册多个 | list_names 长度正确 |
| 3 | 覆盖同名 | 后注册覆盖先注册 |
| 4 | 非 Protocol 拒绝 | raise TypeError |
| 5 | None 拒绝 | raise TypeError |
| **ChannelRegistry.get** | | |
| 6 | 获取已注册 | 返回实例 |
| 7 | 未知返回 None | 不存在的渠道名 |
| 8 | 空注册表 | 返回 None |
| **ChannelRegistry.list** | | |
| 9 | list_names | 返回所有名称 |
| 10 | 空注册表 | 返回 [] |
| 11 | list_channels | 返回所有实例 |
| **ChannelRegistry.validate** | | |
| 12 | validate_all | 返回 {name: bool} |
| 13 | validate_all 空 | 返回 {} |
| 14 | validate 单个 | 返回 bool |
| 15 | validate 不存在 | 返回 False |
| **ChannelRegistry.fetch** | | |
| 16 | fetch 委托 | 返回渠道 fetch 结果 |
| 17 | fetch 未知渠道 | raise KeyError |
| 18 | fetch 传递 kwargs | kwargs 正确传递 |
| **集成测试** | | |
| 19 | 注册+使用 | 多渠道注册/查询 |
| 20 | 类型注解使用 | 通过 ChannelRegistry 类型注解 |
| **create_default_registry** | | |
| 21 | 返回类型 | isinstance ChannelRegistry |
| 22 | 包含全部 10 渠道 | expected 列表逐一检查 |
| 23 | 全部满足 Protocol | isinstance ChannelProtocol |
| 24 | 名称一致性 | get(name) is channel |
| 25 | 总数 = 10 | len(list_names) == 10 |
| **7 个适配器** | | |
| 26-32 | Protocol 满足性 | isinstance + channel_name |
| 33 | chinaz validate | exit→False |
| 34 | chinaz fetch | 委托 fetch_channel |
| 35-37 | fofa_search/zoomeye/rdns_ptr fetch | 委托 + kwargs |
| 38-40 | whois/ssl_cert/ipinfo_api fetch | 委托 + kwargs |
| 41-46 | validate 边界 | exit→False / 成功→True |

## test_base_batch.py

`BaseBatchQuery` ABC 的初始化/加载逻辑测试（14 个）。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| 1-3 | IP 去重加载 | 去重/空行/原始计数 |
| 4-5 | 进度文件 | 加载已有/不存在返回空集 |
| 6-7 | 待处理 IP | 合并去重+进度/全部已处理 |
| 8 | 渠道名属性 | 默认/自定义 |
| 9-10 | delay 获取 | 约定属性名/默认值 |
| 11-12 | _is_error | raw_error/error 字段检查 |
| 13-14 | progress_file | 基于 storage_file 生成 |

## test_batch_run.py

`BaseBatchQuery.run()` 核心循环 + 2 个示范迁移验证。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **run 基本流程** | | |
| 1 | 查询全部待处理 IP | writes 长度 = pending 数 |
| 2 | 写入正确渠道名 | channel_name 匹配 |
| 3 | 写入每个 IP 的数据 | data 内容正确 |
| 4 | 保存进度 | _load_progress 包含所有 IP |
| 5 | 处理错误响应 | raw_error 正确写入 |
| 6 | 空 pending 无操作 | 0 writes |
| **PID 管理** | | |
| 7 | 启动时写 PID | pid_written = True |
| 8 | 每个 IP 更新心跳 | heartbeats = IP 数 |
| 9 | 完成时移除 PID | removed = True |
| 10 | 中断时移除 PID | KeyboardInterrupt → removed |
| **延迟** | | |
| 11 | 查询间应用延迟 | elapsed ≥ delay * (n-1) |
| **统计** | | |
| 12 | 成功/失败计数 | success_count + fail_count |
| 13 | 总耗时记录 | total_elapsed ≥ 0 |
| **validate 钩子** | | |
| 14 | 不跳过时调用 | _do_validate 被调用 |
| 15 | 跳过时不调用 | no_validate=True |
| **迁移验证** | | |
| 16-18 | fofa_host 迁移 | 继承/channel_name/run 方法 |
| 19-20 | rdns_ptr 迁移 | 继承/channel_name |
| 21-22 | aizhan 迁移 | 继承/channel_name |
| 23-24 | chinaz 迁移 | 继承/channel_name |
| 25-26 | fofa_search 迁移 | 继承/channel_name |
| 27-28 | ipinfo_api 迁移 | 继承/channel_name |
| 29-30 | ssl_cert 迁移 | 继承/channel_name |
| 31-32 | whois 迁移 | 继承/channel_name |
| 33-34 | zoomeye 迁移 | 继承/channel_name |

## TDD 路线图

```
③ IPWriter/Reader Protocol  ✅ 完成
④ Channel Protocol          ✅ 完成（完整版：ChannelProtocol + 10 适配器 + InMemoryChannel）
⑦ Channel 公共函数提取       ✅ 完成
⑤ Reporter 领域逻辑分离      ✅ 完成（trace_utils + 迁移）
① Pipeline 拆分              ✅ PhaseRunner 已创建；#2/#3/#4 保留现状
② 批量脚本去重                ✅ 完成（BaseBatchQuery.run() + 9/10 脚本迁移，concurrent 版本除外）
⑥ 渠道注册表                  ✅ 完成（ChannelRegistry + create_default_registry + 10 适配器）
```

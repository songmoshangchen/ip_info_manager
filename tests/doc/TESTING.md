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
| `test_trace_utils.py` | `scenarios/trace_ip/trace_utils.py` (含健壮性) | 26 |
| `test_phase_runner.py` | `scenarios/trace_ip/phase_runner.py` | 10 |
| `test_config.py` | `config.py` Pydantic V2 迁移 | 25 |
| `test_pipeline_registry.py` | ChannelRegistry + Pipeline 集成模式 | 8 |
| `test_classifier.py` | `scenarios/trace_ip/classifier.py` | 28 |
| `test_pipeline_exclude.py` | `pipeline.py` exclude_ips 逻辑 | 13+1 |
| `test_fofa_host.py` | `channel/fofa_host.py` request/fetch/validate | 20 |
| `test_aizhan.py` | `channel/aizhan.py` request/parse/fetch/validate | 31 |
| `test_chinaz.py` | `channel/chinaz.py` request/parse/fetch/validate | 23 |
| `test_ipinfo_api.py` | `channel/ipinfo_api.py` SDK+HTTP 双模式 | 22 |
| `test_rdns_ptr.py` | `channel/rdns_ptr.py` PTR/herror/timeout | 14 |
| `test_whois_query.py` | `channel/whois_query.py` request/parse/fetch | 20 |
| `test_ssl_cert.py` | `channel/ssl_cert.py` cert/parse_domains/format | 18 |
| `test_port_scan.py` | `channel/port_scan.py` nmap/xml_parse/validate | 18 |
| `test_fofa_search.py` | `channel/fofa_search.py` request/fetch/validate | 16 |
| `test_zoomeye.py` | `channel/zoomeye.py` request/fetch/validate | 16 |

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

## test_classifier.py

`IPClassifier` 分类引擎 + `ClassifyResult` 数据类。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestIPClassifierMatch** | | |
| 1 | suffix match | 后缀匹配返回 category+label+need_deep_query |
| 2 | contains match | 包含匹配返回 category |
| 3 | no match | 无匹配返回 "other" |
| 4 | multi rule match | 多规则匹配取第一个 |
| 5 | priority first | 高优先级规则先匹配 |
| **TestIPClassifierFieldExtraction** | | |
| 6 | nested field | `rdns_ptr.hostname` 嵌套取值 |
| 7 | missing top key | 顶层 key 不存在跳过 |
| 8 | missing nested key | 嵌套 key 不存在跳过 |
| 9 | null value | 值为 None 跳过 |
| **TestIPClassifierPatternTypes** | | |
| 10-12 | suffix/contains/exact | 三种匹配类型 |
| 13 | case insensitive | contains 忽略大小写 |
| **TestIPClassifierCustomRules** | | |
| 14 | custom rules | 自定义规则文件 |
| 15 | empty patterns | 空规则列表 |
| 16 | invalid type | 缺少 type 字段 → KeyError (xfail) |
| **TestClassifyResult** | | |
| 17-22 | 字段默认值 | category/label/need_deep_query/matched_by |
| **TestIPClassifierWithBuiltinRules** | | |
| 23-28 | 内置规则 | 加载项目自带 rules.json |

## test_pipeline_exclude.py

`pipeline.py` 中 `_load_exclude_ips` + `_print_report_summary` + Phase 7 集成。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestLoadExcludeIps** | | |
| 1 | file not found | 返回空集合 |
| 2 | empty file | 返回空集合 |
| 3 | no matching IPs | 无匹配返回空集合 |
| 4 | partial match | 部分匹配 |
| 5 | full match | 全部匹配 |
| 6 | dedup | 去重 |
| 7-10 | 边界 | 空行/注释/空白/CIDR |
| **TestPrintReportSummary** | | |
| 11 | import error | 导入不存在模块 → skip |
| **TestPhase7Integration** | | |
| 12-14 | 集成 | exclude_ips 注入 + 过滤 + 结果验证 |

## test_fofa_host.py

`channel/fofa_host.py` — FOFA Host 聚合 API 渠道。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | normal JSON | 返回解析后的 dict，URL 含 detail=true |
| 2 | timeout | 返回 `{raw_error: True, error_message}` |
| 3 | HTTP error | 返回 error dict |
| 4 | invalid JSON | ValueError → error dict |
| 5 | connection error | DNS 解析失败 → error dict |
| 6 | API error | API 返回 error 但不包装（透传） |
| 7 | empty result | 空 detail 列表正常返回 |
| **TestFetchChannel** | | |
| 8-9 | query_time | 正常/错误流程均添加 query_time |
| 10 | delay | apply_delay 被调用 |
| 11 | kwargs 传递 | key/timeout 正确传递 |
| **TestFormatOutput** | | |
| 12-14 | query_time | 补充/保留/原地修改 |
| **TestValidateChannelKey** | | |
| 15-19 | 验证 | 空/空白/无效/网络异常/正常 |
| **TestFofaHostChannelExtra** | | |
| 20 | fetch 委托 | kwargs 透传 |

## test_aizhan.py

`channel/aizhan.py` — 爱站网爬虫渠道。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | normal HTML | 返回 response.text |
| 2 | ReadTimeout | xfail: 被误分类为"查询失败" |
| 3 | Timeout keyword | 含 "timeout" → "网络超时" |
| 4 | 403 | "爱站网禁止请求" |
| 5 | connection error | "网络中断" |
| 6 | generic error | "查询失败" |
| **TestParseResponse** | | |
| 7 | error dict | 直接透传 |
| 8-10 | 页面缺失 | dns-infos/dns-content/两者缺失 |
| 11 | 无域名 | "暂无域名解析到该IP" → 空列表 |
| 12 | 中国地域 | "北京 朝阳 联通" → "中国北京朝阳" |
| 13 | 外国地域 | 非中国 → 原样保留 |
| 14 | 域名去重 | 重复域名只保留第一个 |
| 15 | 域名上限 | 最多 20 个 |
| 16 | 短域名过滤 | len≤3 或无 "." 被过滤 |
| 17 | 无 strong 标签 | location/isp 为 None |
| 18 | 非数字 domain_count | span.red 非数字 → 0 |
| 19 | 缺少 tbody | 返回 success=False |
| 20 | 列数不足 | <5 列的行被跳过 |
| 21 | 无 anchor | 回退到 text 取域名 |
| **TestFetchChannel** | | |
| 22-24 | 流程 | 正常/错误均添加 query_time；delay 调用 |
| **TestValidateChannelKey** | | |
| 25-30 | 验证 | 空/空白/302重定向/404/网络异常/正常 |
| **TestAizhanChannelExtra** | | |
| 31 | fetch 委托 | kwargs 透传 |

## test_chinaz.py

`channel/chinaz.py` — 站长之家爬虫渠道。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | normal HTML | 返回 response.text |
| 2 | ReadTimeout | xfail: 同 aizhan |
| 3 | Timeout keyword | "网络超时" |
| 4 | 403 | "站长之家禁止请求" |
| 5 | connection error | "网络中断" |
| **TestParseResponse** | | |
| 6 | error dict | 直接透传 |
| 7-8 | 页面缺失 | info section/domain section |
| 9 | 地域+运营商 | label 解析 |
| 10 | 域名+日期 | date 拆分 start_time/end_time |
| 11 | 域名去重 | 重复只保留第一个 |
| 12 | 域名上限 | 最多 20 |
| 13 | 短域名过滤 | len≤3 被过滤 |
| 14 | 暂无结果 | 空域名列表 |
| 15 | 无 anchor | p 内无 a 标签跳过 |
| **TestFetchChannel** | | |
| 16-17 | 流程 | 正常/错误均添加 query_time |
| **TestValidateChannelKey** | | |
| 18-22 | 验证 | 空/空白/缺字段/网络异常(不退出)/正常 |
| **TestChinazChannelExtra** | | |
| 23 | fetch 委托 | kwargs 透传 |

## test_ipinfo_api.py

`channel/ipinfo_api.py` — IPInfo API 渠道，SDK (`_request_channel_api`) + HTTP (`_request_channel_noapi`) 双模式。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannelApiMode** | | |
| 1 | normal | api.ipinfo.io/lite + Bearer token |
| 2 | timeout | 返回 error dict |
| 3 | HTTP error | 401 → error dict |
| 4 | invalid JSON | → error dict |
| **TestRequestChannelNoApiMode** | | |
| 5 | normal | ipinfo.io/{ip}/json + hostname |
| 6 | timeout | → error dict |
| 7 | rate limit | 429 → error dict |
| 8 | 不同字段 | hostname/loc 等 free API 独有字段 |
| **TestRequestChannelDispatch** | | |
| 9-10 | 分发 | use_api=True/False 调用对应函数 |
| **TestFetchChannel** | | |
| 11-14 | 流程 | API/NoAPI/错误均添加 query_time；delay |
| **TestValidateChannelKey** | | |
| 15-18 | 验证 | 有效token/无效token/无token用免费API/免费API不可达 |
| **TestIpinfoApiChannelExtra** | | |
| 19 | fetch 委托 | kwargs 透传 |

## test_rdns_ptr.py

`channel/rdns_ptr.py` — DNS 反向解析渠道 (socket.gethostbyaddr)。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | 单 PTR | hostname + ptr_count=1 |
| 2 | 多 PTR | aliases + ptr_count=3 |
| 3 | herror | has_ptr=False, error_type="herror" |
| 4 | gaierror | has_ptr=False, error_type="gaierror" |
| 5 | timeout | error_type="timeout"，含超时秒数 |
| 6 | 其他异常 | raw_error=True, error_type=类名 |
| 7 | query_ip | 结果包含查询 IP |
| **TestFetchChannel** | | |
| 8-10 | 流程 | 正常/错误均添加 query_time；delay |
| **TestValidateChannelKey** | | |
| 11-13 | 验证 | 成功/herror仍通过/其他错误退出 |
| **TestRdnsPtrChannelExtra** | | |
| 14 | fetch 委托 | kwargs 透传 |

## test_whois_query.py

`channel/whois_query.py` — WHOIS 查询渠道 (python-whois)。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | normal | 返回 whois 结果对象 |
| 2 | None 结果 | → "未找到 Whois 信息" |
| 3 | timeout | → "查询超时" |
| 4 | exception | → error dict |
| 5 | 未安装 | whois_query=None → "未安装" |
| **TestParseResponse** | | |
| 6 | error dict | raw_error 透传 |
| 7 | normal | domain_name/registrar/country 等字段 |
| 8 | 列表取首 | domain_name=[a,b] → a |
| 9 | 空列表 | xfail: [] truthy 检查跳过字段 |
| 10 | datetime isoformat | creation_date → ISO 格式 |
| 11 | 日期列表取首 | [date1, date2] → date1 |
| 12-13 | name_servers | 列表/字符串包裹 |
| 14 | None 字段 | 不存在的字段不包含在结果中 |
| **TestFetchChannel** | | |
| 15-16 | 流程 | 正常/错误 |
| **TestValidateChannelKey** | | |
| 17-19 | 验证 | 未安装退出/成功/超时仍通过 |
| **TestWhoisChannelExtra** | | |
| 20 | fetch 委托 | kwargs 透传 |

## test_ssl_cert.py

`channel/ssl_cert.py` — SSL 证书获取渠道 (ssl + socket)。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | normal cert | 返回 cert_text |
| 2 | no cert | → error_message="no_cert" |
| 3 | timeout | → "connection_timeout" |
| 4 | refused | → "connection_refused" |
| 5 | SSL error | → "ssl_error: ..." |
| 6 | generic | → error dict |
| **TestParseDomains** | | |
| 7 | CN+SAN | 提取所有域名 |
| 8 | CN only | 仅 CN |
| 9 | SAN only | 仅 SAN |
| 10 | 无域名 | 返回空列表 |
| 11 | 去重 | CN 与 SAN 重复去重 |
| **TestFormatOutput** | | |
| 12 | error | error + ip + port + query_time |
| 13 | issuer_cn 空格截断 | xfail: 多词 CN 被截断 |
| 14 | success basic | subject_cn + san_domains + query_time |
| **TestFetchChannel** | | |
| 15-17 | 流程 | 正常/错误/delay |
| **TestSslCertChannelExtra** | | |
| 18 | fetch 委托 | kwargs 透传 |

## test_port_scan.py

`channel/port_scan.py` — nmap 端口扫描渠道 (subprocess)。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | normal scan | XML 输出 + returncode + 命令含 -p |
| 2 | nmap not found | FileNotFoundError → error dict |
| 3 | nmap timeout | TimeoutExpired → error dict |
| 4 | nmap exception | OSError → error dict |
| 5 | empty port string | 命令不含 -p |
| **TestParseNmapXml** | | |
| 6 | normal | host_alive + open_ports + service/product |
| 7 | no host | host_alive=False |
| 8 | invalid XML | 返回默认空结果 |
| 9 | historical closed | 已验证/已关闭端口分类 |
| 10 | empty XML | 空结果 |
| 11 | no open ports | 全部 closed |
| 12 | malformed port_id | xfail: int("abc") 异常未捕获 |
| **TestFetchChannel** | | |
| 13-15 | 流程 | 正常/错误/nonzero returncode |
| **TestValidateEngine** | | |
| 16-19 | 验证 | PATH 中找到/未找到/绝对路径/超时 |
| **TestPortScanChannelExtra** | | |
| 20 | fetch 委托 | kwargs 透传 |

## test_fofa_search.py

`channel/fofa_search.py` — FOFA 搜索 API 渠道 (base64 编码查询)。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | normal | results + size |
| 2 | timeout | → error dict |
| 3 | HTTP error | → error dict |
| 4 | invalid JSON | → error dict |
| 5 | query_suffix | base64 编码含后缀 |
| 6 | empty results | size=0 正常返回 |
| **TestFetchChannel** | | |
| 7-9 | 流程 | 正常/错误/query_time；delay |
| **TestFormatOutput** | | |
| 10-11 | query_time+fields | 补充/保留 |
| **TestValidateChannelKey** | | |
| 12-14 | 验证 | 空/无效/正常 |
| **TestFofaSearchChannelExtra** | | |
| 15 | fetch 委托 | kwargs 透传 |

## test_zoomeye.py

`channel/zoomeye.py` — ZoomEye API 渠道 (POST 请求)。

| # | 测试名 | 验证的行为 |
|---|--------|-----------|
| **TestRequestChannel** | | |
| 1 | normal | total + data + API-KEY header |
| 2 | API error | message != "success" → error dict |
| 3 | timeout | → error dict |
| 4 | HTTP error | → error dict |
| 5 | connection error | → error dict |
| 6 | query encoded | base64 编码在 body 中 |
| 7 | sub_type | sub_type 传递到 POST body |
| 8 | empty results | total=0 正常返回 |
| **TestFetchChannel** | | |
| 9-11 | 流程 | 正常/错误/delay |
| **TestFormatOutput** | | |
| 12-13 | query_time | 补充/保留 |
| **TestValidateChannelKey** | | |
| 14-16 | 验证 | 空/有效/空白 |
| **TestZoomeyeChannelExtra** | | |
| 17 | fetch 委托 | kwargs 透传 |

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

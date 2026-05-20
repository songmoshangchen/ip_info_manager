# PRD: IP 信息管理器 — 系统行为规格

## Problem Statement

IP 信息管理器需要从多个第三方渠道（FOFA、爱站网、站长之家、IPInfo、ZoomEye 等）批量采集 IP 的关联信息（域名、端口、地理位置、WHOIS、SSL 证书等），经过分类和优先级排序后，生成可操作的追踪报告。

当前系统存在以下问题：
1. **渠道行为未标准化** — 10 个渠道的错误处理、返回格式、验证逻辑各不相同，缺乏统一规格
2. **协议层不完整** — 数据读写接口、渠道接口、分类引擎等核心抽象缺少行为规格
3. **健壮性不足** — 存在多个 None 处理、异常分类、正则匹配等 bug，缺少测试覆盖
4. **可测试性差** — 渠道直接依赖网络和外部 API，无法在不触发真实请求的情况下验证行为

## Solution

通过 TDD 方式建立完整的行为测试套件（505 个测试），从测试中逆向提取每个模块的行为规格。测试是规格的唯一真实来源，所有生产代码必须适配测试描述的行为。

系统分为 5 层：
1. **协议层** — 定义数据读写和渠道的接口契约
2. **存储层** — 基于文件系统的 JSON 数据读写
3. **渠道层** — 10 个独立渠道，统一遵循 ChannelProtocol
4. **编排层** — 阶段执行器、断点续传、分类引擎、管线编排
5. **配置层** — Pydantic V2 环境变量配置

## User Stories

> 标记说明：
> - 🟢 **正常流程** — 正常输入下的期望行为
> - 🔴 **异常处理** — 错误/边界情况的处理
> - 📥 **输入要求** — 接口参数和格式约束
> - 📤 **输出要求** — 返回值结构和格式
> - 🔧 **开发者/调试** — 测试替身、可观测性等开发需求
> - ⚙️ **系统运行** — 运行时行为（启动、配置、管线）

---

### 协议与接口

#### 🔧 开发者/调试

1. 作为开发者，我希望所有渠道实现统一的 ChannelProtocol 接口（channel_name + validate + fetch），以便渠道可以互换使用
2. 作为开发者，我希望通过 isinstance() 在运行时检查一个对象是否满足 ChannelProtocol，以便做类型安全验证
3. 作为开发者，我希望有 IPDataWriter 和 IPDataReader 协议定义，以便存储层可以替换为不同实现（文件系统、数据库、内存等）
4. 作为开发者，我希望有满足上述协议的测试替身实现，以便在不依赖文件系统和网络的情况下编写测试

#### 🟢 正常流程

5. 作为系统，我希望 IPDataWriter 通过 add_or_update_ip 写入的数据，能通过 IPDataReader 的 get_ip_data 读回，以便端到端流程正确

#### 📤 输出要求 — IPDataWriter 契约

6. 作为系统，我希望 add_or_update_ip 对同一 IP+渠道的多次写入以最后一次为准（更新语义）
7. 作为系统，我希望 add_or_update_ip 对同一 IP 不同渠道的写入互不影响（渠道隔离）

#### 📤 输出要求 — IPDataReader 契约

8. 作为系统，我希望 get_ip_data(ip) 返回该 IP 所有渠道数据的 dict，包含 ip 字段
9. 作为系统，我希望 get_channel_data(ip, channel) 返回该 IP 指定渠道的数据 dict
10. 作为系统，我希望 list_all_ips() 返回所有已存储的 IP 列表
11. 作为系统，我希望 list_ip_channels(ip) 返回该 IP 已有数据的渠道列表

#### 🔴 异常处理

12. 作为系统，我希望不满足 ChannelProtocol 的类在 isinstance() 检查时返回 False，以便防止非法对象混入
13. 作为系统，我希望适配器的 validate() 在底层函数抛出 SystemExit 或任何异常时返回 False（不崩溃）
14. 作为系统，我希望 delete_ip 对不存在的 IP 返回 False（不报错）
15. 作为系统，我希望 delete_channel 对不存在的 IP 或渠道返回 False（不报错）
16. 作为系统，我希望 get_ip_data / get_channel_data 在数据不存在时返回 None（不报错）
17. 作为系统，我希望 list_ip_channels / search_ips_by_channel 在无匹配时返回空列表（不报错）

---

### 渠道注册与发现

#### 🔧 开发者/调试

18. 作为开发者，我希望通过 ChannelRegistry 按 channel_name 注册渠道，以便集中管理
19. 作为开发者，我希望 create_default_registry() 自动注册所有预期渠道，以便开箱即用且能发现遗漏或意外新增的渠道
20. 作为开发者，我希望所有注册的渠道都满足 ChannelProtocol，以便保证接口一致性

#### 🟢 正常流程

21. 作为系统，我希望注册表支持按名称查找渠道（get）、列出所有渠道名（list_names）、列出所有渠道实例（list_channels）
22. 作为系统，我希望注册表支持批量验证所有渠道（validate_all），返回每个渠道的验证结果 dict
23. 作为系统，我希望注册表支持通过名称委托 fetch（registry.fetch(channel_name, ip)），以便统一调用入口

#### 🔴 异常处理

24. 作为系统，我希望注册不满足协议接口的对象时抛出 TypeError，以便及早发现类型错误
25. 作为开发者，我希望重复注册同一名称时覆盖旧渠道，以便支持渠道替换
26. 作为系统，我希望查找未注册名称时返回 None（不抛异常），以便安全处理缺失渠道
27. 作为系统，我希望 fetch 不存在的渠道名时抛出 KeyError，以便区分"渠道无数据"和"渠道未注册"
28. 作为系统，我希望 validate 不存在的渠道名时返回 False（不抛异常）

---

### 通用渠道行为 — 连续失败保护

#### 🔴 异常处理 — 批次级熔断

29. 作为系统，我希望所有渠道在连续 5 次查询因网络问题（超时、连接失败）失败后，跳过当前批次剩余的 IP，不继续查询（避免浪费时间等待必然失败的请求）
30. 作为系统，我希望连续失败保护仅在当前批次生效，下次运行时计数器重置，渠道正常工作（不禁用渠道，因为网络问题是临时性的）

#### 🔴 异常处理 — 依赖检查

31. 作为系统，我希望每个渠道在首次使用前检查自身依赖（Python 库、外部命令行工具等）是否可用，不可用时记录警告并跳过该渠道的所有查询
32. 作为系统，我希望依赖检查失败不禁用渠道，下次运行时重新检查（因为依赖可能被中途安装）

---

### FOFA Host 聚合渠道

#### � 正常流程

29. 作为系统，我希望 fofa_host 接收 IP 作为输入，从配置中获取 API Key，请求 FOFA Host API 并携带 key 和 detail=true 参数
30. 作为系统，我希望 fofa_host 在 HTTP 成功且 API 返回成功时（JSON 中 error=false），返回解析后的完整数据 dict

#### 📤 输出要求

31. 作为系统，我希望 fofa_host 在查询成功时，返回包含 API 数据和 query_time（查询时间戳）的结果

#### 🔴 异常处理 — 临时性错误（可重试）

33. 作为系统，我希望 fofa_host 在遇到超时、连接失败、查询限流等临时性错误时，不写入错误数据到存储（因为重试可能成功）
34. 作为系统，我希望 fofa_host 在遇到临时性错误时记录日志，以便排查网络问题

#### � 异常处理 — 永久性错误（不可重试）

35. 作为系统，我希望 fofa_host 在 API Key 为空或无效时，发出警告并将该渠道标记为禁用，后续 IP 直接跳过该渠道查询
36. 作为系统，我希望 fofa_host 在 API 返回业务错误时（JSON 中 error=true），原样透传错误信息，以便上层判断错误类型

---

### 爱站网渠道

#### � 正常流程

32. 作为系统，我希望 aizhan 接收 IP 作为输入，从配置中获取登录凭证（Cookie），请求爱站网 DNS 反查页面
33. 作为系统，我希望 aizhan 从页面中提取地域信息（省份+城市+运营商），中国地域格式化为"中国省份城市"，非中国地域原样保留
34. 作为系统，我希望 aizhan 从页面中提取关联域名列表

#### 📤 输出要求

35. 作为系统，我希望 aizhan 查询成功时返回包含地域（location）、运营商（isp）、域名列表（domains）、域名数量（domain_count）和 query_time 的结果
36. 作为系统，我希望域名列表去重（保留首次出现）、上限 20 个、过滤无点号的无效域名
37. 作为系统，我希望无关联域名时返回空列表而非报错

#### 🔴 异常处理 — 临时性错误（可重试）

38. 作为系统，我希望 aizhan 在遇到超时或连接失败等网络错误时，不写入错误数据到存储
39. 作为系统，我希望 aizhan 在页面结构不符合预期（缺少必需的数据区域）时，不写入错误数据到存储，记录日志以便排查
40. 作为系统，我希望 aizhan 在遇到临时性错误时记录日志，以便排查网络或页面变更问题

#### 🔴 异常处理 — 永久性错误（不可重试）

41. 作为系统，我希望 aizhan 在登录凭证（Cookie）为空或已失效（如页面重定向到登录页、返回 403）时，发出警告并将该渠道标记为禁用，后续 IP 直接跳过该渠道查询

---

### 站长之家渠道

#### � 正常流程

42. 作为系统，我希望 chinaz 接收 IP 作为输入，从配置中获取登录凭证（Cookie），请求站长之家 IP 反查页面
43. 作为系统，我希望 chinaz 从页面中提取归属地（省份+城市）和运营商信息
44. 作为系统，我希望 chinaz 从页面中提取关联域名及每个域名的备案起止日期

#### 📤 输出要求

45. 作为系统，我希望 chinaz 查询成功时返回包含归属地（location）、运营商（isp）、域名列表（domains，含起止日期）和 query_time 的结果
46. 作为系统，我希望域名列表去重（保留首次出现）、上限 20 个、过滤无点号的无效域名
47. 作为系统，我希望无关联域名时返回空列表而非报错

#### � 异常处理 — 临时性错误（可重试）

48. 作为系统，我希望 chinaz 在遇到超时或连接失败等网络错误时，不写入错误数据到存储
49. 作为系统，我希望 chinaz 在页面结构不符合预期（缺少必需的数据区域）时，不写入错误数据到存储，记录日志以便排查
50. 作为系统，我希望 chinaz 在遇到临时性错误时记录日志，以便排查网络或页面变更问题

#### � 异常处理 — 永久性错误（不可重试）

51. 作为系统，我希望 chinaz 在登录凭证（Cookie）为空或缺少必需字段时，发出警告并将该渠道标记为禁用，后续 IP 直接跳过该渠道查询

---

### IPInfo 认证渠道（ipinfo_api）

#### 🟢 正常流程

52. 作为系统，我希望 ipinfo_api 接收 IP 作为输入，从配置中获取 API Token，使用 Token 认证请求 IPInfo API，获取 IP 的地理位置、运营商等信息
53. 作为系统，我希望验证阶段验证 Token 的有效性

#### 📤 输出要求

54. 作为系统，我希望 ipinfo_api 查询成功时返回包含 IP 地理信息（国家/省份/城市/运营商）和 query_time 的结果

#### 🔴 异常处理 — 临时性错误（可重试）

55. 作为系统，我希望 ipinfo_api 在遇到超时或连接失败等网络错误时，不写入错误数据到存储
56. 作为系统，我希望 ipinfo_api 在遇到临时性错误时记录日志，以便排查网络问题

#### 🔴 异常处理 — 永久性错误（不可重试）

57. 作为系统，我希望 ipinfo_api 在 Token 为空或无效时，发出警告并将该渠道标记为禁用，后续 IP 直接跳过

---

### IPInfo 免费渠道（ipinfo_free）

#### 🟢 正常流程

58. 作为系统，我希望 ipinfo_free 接收 IP 作为输入，无认证请求 IPInfo 公开接口，获取 IP 的地理位置、主机名等信息

#### 📤 输出要求

60. 作为系统，我希望 ipinfo_free 查询成功时返回包含 IP 地理信息（国家/省份/城市）和 query_time 的结果
61. 作为系统，我希望 ipinfo_free 额外返回主机名（hostname）和坐标（loc）等公开接口独有字段

#### 🔴 异常处理 — 临时性错误（可重试）

62. 作为系统，我希望 ipinfo_free 在遇到超时或连接失败等网络错误时，不写入错误数据到存储
63. 作为系统，我希望 ipinfo_free 在到达请求限额时，不写入错误数据到存储，记录日志以便调整查询频率
64. 作为系统，我希望 ipinfo_free 在遇到临时性错误时记录日志，以便排查网络问题

---

### DNS 反向解析渠道（rdns_ptr）

#### � 正常流程

65. 作为系统，我希望 rdns_ptr 接收 IP 作为输入，通过 DNS 反向解析查询该 IP 的主机名
66. 作为系统，我希望 rdns_ptr 在 IP 无 PTR 记录时正常返回（表示无反向解析记录，不是错误）

#### 📤 输出要求

68. 作为系统，我希望 rdns_ptr 查询成功时返回包含主机名（hostname）、别名列表（aliases）、PTR 记录数量（ptr_count）和 query_time 的结果
69. 作为系统，我希望 rdns_ptr 无 PTR 记录时返回 has_ptr=False 及查询 IP，而非报错

#### 🔴 异常处理 — 临时性错误

70. 作为系统，我希望 rdns_ptr 在 DNS 查询超时时正常记录结果（has_ptr=False，含超时信息），因为 DNS 超时是常见现象，不代表网络异常
71. 作为系统，我希望 rdns_ptr 在遇到临时性错误时记录日志，以便排查网络问题

#### 🔴 异常处理 — 网络异常（计入熔断）

72. 作为系统，我希望 rdns_ptr 在遇到网络不可用（非 DNS 超时，而是真正的连接失败）时，不写入数据到存储，计入通用熔断计数器

---

### WHOIS 查询渠道

#### � 正常流程

73. 作为系统，我希望 whois_query 接收 IP 或域名作为输入，通过 WHOIS 协议查询注册信息

#### 📤 输出要求

75. 作为系统，我希望 whois_query 查询成功时返回包含域名注册信息（注册商、注册人、国家、有效期等）和 query_time 的结果
76. 作为系统，我希望 whois_query 对同一字段有多个值的情况取第一个有效值
77. 作为系统，我希望 whois_query 对日期类型字段统一转换为字符串格式输出
78. 作为系统，我希望 whois_query 无 WHOIS 记录时正常返回（表示无注册信息，不是错误）

#### 🔴 异常处理 — 临时性错误（可重试）

79. 作为系统，我希望 whois_query 在遇到超时或连接失败等网络错误时，不写入错误数据到存储
80. 作为系统，我希望 whois_query 在遇到临时性错误时记录日志，以便排查问题

---

### SSL 证书渠道

#### 🟢 正常流程

74. 作为系统，我希望 ssl_cert 接收 IP 或域名作为目标，以及端口列表作为输入，通过 SSL 连接获取目标服务在每个端口上的证书信息
75. 作为系统，我希望 ssl_cert 从每份证书中提取主题域名（CN）和所有备用域名（SAN），合并去重后返回
76. 作为系统，我希望 ssl_cert 支持域名作为输入（如 example.com:443），因为域名的 SSL 证书查询比 IP 更常见

#### 📤 输出要求

77. 作为系统，我希望 ssl_cert 查询成功时返回包含主题域名（subject_cn）、颁发者（issuer_cn）、备用域名列表（san_domains）、有效期、查询的端口列表和 query_time 的结果
78. 作为系统，我希望 ssl_cert 对多个端口的证书结果合并返回，包含每个端口的证书信息
79. 作为系统，我希望 ssl_cert 在目标服务无 SSL 证书或未开放指定端口时正常返回失败信息，而非报错

#### 🔴 异常处理 — 临时性错误（可重试）

80. 作为系统，我希望 ssl_cert 在遇到超时或连接失败等网络错误时，不写入错误数据到存储
81. 作为系统，我希望 ssl_cert 在遇到临时性错误时记录日志，以便排查问题

---

### nmap 端口扫描渠道

#### � 正常流程

64. 作为系统，我希望 nmap_port_scan 接收 IP 和可选端口列表作为输入，对目标 IP 执行端口扫描
65. 作为系统，我希望 nmap_port_scan 从扫描结果中提取每个开放端口的服务名称、产品信息和版本信息
66. 作为系统，我希望 nmap_port_scan 在端口列表非空时仅扫描指定端口，为空时扫描常用端口

#### 📤 输出要求

67. 作为系统，我希望 nmap_port_scan 查询成功时返回包含主机存活状态、开放端口列表、扫描端口总数、开放端口数量和查询时间的结果
69. 作为系统，我希望 nmap_port_scan 每个开放端口结果包含端口号、协议、状态、服务名称、产品信息和版本信息
70. 作为系统，我希望 nmap_port_scan 在目标主机无响应或无开放端口时正常返回（host_alive=False 或 open_count=0），而非报错
71. 作为系统，我希望 nmap_port_scan 在扫描输出无法正确解析时，返回空结果而非抛出异常

#### � 异常处理 — 依赖检查

72. 作为系统，我希望 nmap_port_scan 在首次使用前检查端口扫描工具是否可用，不可用时跳过该渠道并记录警告日志
73. 作为系统，我希望 nmap_port_scan 支持在系统路径中自动检测扫描工具，也支持通过配置指定工具路径

#### 🔴 异常处理 — 临时性错误（可重试）

74. 作为系统，我希望 nmap_port_scan 在扫描超时或执行异常时，不写入错误数据到存储，计入熔断计数器
75. 作为系统，我希望 nmap_port_scan 在遇到临时性错误时记录日志，以便排查问题

#### 🔧 开发者/调试

76. 作为开发者，我希望 nmap_port_scan 的结果包含扫描引擎标识，用于区分不同扫描工具的实现
77. 作为开发者，我希望 nmap_port_scan 在扫描工具返回非零退出码时，在结果中保留退出码信息供排查

---

### FOFA 搜索渠道

#### � 正常流程

78. 作为系统，我希望 fofa_search 接收 IP 作为输入，通过 FOFA 搜索 API 查询该 IP 的关联资产信息
79. 作为系统，我希望 fofa_search 支持追加额外查询条件，用于缩小搜索范围
80. 作为系统，我希望 fofa_search 在搜索无结果时正常返回空结果，而非报错

#### 📤 输出要求

81. 作为系统，我希望 fofa_search 查询成功时返回包含结果列表、结果总数、查询字段定义和 query_time 的结果
82. 作为系统，我希望 fofa_search 在结果为空时仍返回完整的元数据结构（fields、query_time 等）

#### 🔴 异常处理 — 永久性错误（不可重试）

83. 作为系统，我希望 fofa_search 在 API Key 为空时，发警告日志并禁用该渠道，跳过所有未查询的 IP
84. 作为系统，我希望 fofa_search 在 API Key 无效（API 返回凭证错误）时，发警告日志并禁用该渠道，跳过所有未查询的 IP

#### � 异常处理 — 临时性错误（可重试）

85. 作为系统，我希望 fofa_search 在遇到超时、连接失败等网络错误时，不写入错误数据到存储，计入熔断计数器
86. 作为系统，我希望 fofa_search 在遇到临时性错误时记录日志，以便排查问题
87. 作为系统，我希望 fofa_search 在 API 返回非 JSON 格式响应时，视为临时性错误处理

---

### ZoomEye 渠道

#### � 正常流程

88. 作为系统，我希望 zoomeye 接收 IP 作为输入，通过 ZoomEye 搜索 API 查询该 IP 的关联资产信息
89. 作为系统，我希望 zoomeye 支持指定搜索子类型参数，用于区分不同资产维度的搜索
90. 作为系统，我希望 zoomeye 在搜索无结果时正常返回空结果，而非报错

#### 📤 输出要求

91. 作为系统，我希望 zoomeye 查询成功时返回包含结果列表、结果总数和 query_time 的结果
92. 作为系统，我希望 zoomeye 在 API 返回错误消息时，将错误信息包含在返回结果中

#### 🔴 异常处理 — 永久性错误（不可重试）

93. 作为系统，我希望 zoomeye 在 API Key 为空或仅含空白字符时，发警告日志并禁用该渠道，跳过所有未查询的 IP

#### 🔴 异常处理 — 临时性错误（可重试）

94. 作为系统，我希望 zoomeye 在遇到超时、连接失败等网络错误时，不写入错误数据到存储，计入熔断计数器
95. 作为系统，我希望 zoomeye 在遇到临时性错误时记录日志，以便排查问题

#### 🔧 开发者/调试

96. 作为开发者，我希望 zoomeye 的 Key 验证仅检查是否已配置，不进行在线验证，以避免消耗 API 额度

---

### 批量查询框架

#### 🟢 正常流程

97. 作为系统，我希望批量查询框架提供 IP 列表加载能力，自动去重、跳过空行，并记录原始数量、去重数量和重复数量
98. 作为系统，我希望批量查询框架支持三种批次模式：单渠道查询（1:1）、跨渠道查询（1:N）、独立处理脚本（不对应渠道）
99. 作为系统，我希望批量查询框架提供延迟控制接口，具体批次脚本按需调用
100. 作为系统，我希望批量查询框架提供查询统计接口（成功数、失败数、总耗时），具体批次脚本在完成时调用

#### 📤 必选接口（批次脚本必须使用）

101. 作为系统，我希望批量查询框架提供数据写入接口，接收 IP、渠道名称和查询结果；批次脚本必须使用加载的 IP 列表数据作为输入，并将查询结果通过此接口写入存储
102. 作为系统，我希望批量查询框架提供进度保存接口，批次脚本在处理完 IP 后必须调用以持久化进度
103. 作为系统，我希望批量查询框架提供进度加载接口，在启动时自动检测已处理的 IP，仅返回剩余待处理的 IP；待处理列表为空时跳过执行
104. 作为系统，我希望批量查询框架在并发场景下提供线程安全的数据写入接口，避免并发写入导致数据损坏

#### 📤 可选接口（批次脚本按需使用）

105. 作为系统，我希望批量查询框架提供进程标识写入和清理接口，批次脚本在启动和完成时按需调用
106. 作为系统，我希望批量查询框架提供进程心跳更新接口，批次脚本在处理 IP 时按需调用
107. 作为开发者，我希望批量查询框架提供 ETA 估算工具，批次脚本可自行决定是否使用及计算策略
108. 作为开发者，我希望批量查询框架在启动前提供凭证验证钩子，且支持跳过验证（用于调试）
109. 作为系统，我希望批量查询框架提供错误检测接口，批次脚本可据此判断查询结果是否为错误

#### 📤 执行模式（由具体批次脚本决定）

110. 作为开发者，我希望具体批次脚本自行决定执行模式（串行或并发），因为不同渠道有不同的并发限制
111. 作为开发者，我希望具体批次脚本自行决定数据写入时机（逐条、批量、并发完成后刷入），以适配不同的执行模式

---

### 分类引擎

#### 📥 输入要求

82. 作为系统，我希望 IPClassifier 从 JSON 规则文件加载分类规则
83. 作为系统，我希望 IPClassifier 支持 suffix / contains / exact / prefix / regex 五种匹配类型
84. 作为系统，我希望 IPClassifier 支持嵌套字段路径（如 rdns_ptr.hostname）
85. 作为系统，我希望 IPClassifier 支持自定义规则文件与内置规则合并

#### 📤 输出要求

86. 作为系统，我希望 IPClassifier 缺少匹配时返回 category="other"
87. 作为系统，我希望 ClassifyResult 包含 category / label / description / matched_by / need_deep_query / classify_time

---

### 阶段执行与断点续传

#### ⚙️ 系统运行

88. 作为系统，我希望 PhaseRunner 接受 IP 列表、阶段号、渠道列表、数据存储
89. 作为系统，我希望 PhaseRunner 从数据存储检测已处理的 IP（需要所有指定渠道都有数据）
90. 作为系统，我希望 PhaseRunner 只对 pending IP 调用 query_fn
91. 作为系统，我希望 PhaseRunner 将查询结果写入数据存储

#### 🔴 异常处理

92. 作为系统，我希望 PhaseRunner 安全处理 query_fn 返回 None 或空 dict 的情况

#### ⚙️ 系统运行（断点续传）

93. 作为系统，我希望 ProgressManager 支持渠道级进度文件（{prefix}.trace_phase{N}.{channel}.progress）
94. 作为系统，我希望 ProgressManager 在无渠道级文件时退化为阶段级进度
95. 作为系统，我希望 ProgressManager 的 load_completed 取所有渠道的交集
96. 作为系统，我希望 ProgressManager 的 clear_from 同时清理阶段级和渠道级文件

---

### 工具函数

#### 🟢 正常流程

97. 作为系统，我希望 is_china_ip 根据 country_code=="CN" 或 country 含 "China" 判断
99. 作为系统，我希望 extract_all_domains 从 aizhan 和 chinaz 合并域名，去重
101. 作为系统，我希望 trace_priority 根据中国 IP + 有域名 + 有端口计算 1-4 优先级

#### 🔴 异常处理

98. 作为系统，我希望 is_china_ip 在 country=None 或 country_code=None 时安全返回 False（当前 bug：TypeError）
100. 作为系统，我希望 extract_all_domains 安全跳过 domains 列表中的 None 元素（当前 bug：AttributeError）

---

### 配置

#### ⚙️ 系统运行

102. 作为系统，我希望 Settings 通过 Pydantic V2 从 .env 文件加载所有渠道配置（API Key、超时、延迟等）
104. 作为系统，我希望未配置的渠道参数有合理默认值，以便不配置 .env 也不崩溃

#### 🔧 开发者/调试

103. 作为开发者，我希望在测试时可以隔离 .env 文件，通过环境变量注入配置，以便测试不同配置组合

---

### 管线集成 — 排除 IP

#### 📥 输入要求

105. 作为系统，我希望 pipeline 从指定文件加载排除 IP 列表（exclude_ips_file）

#### 🔴 异常处理

106. 作为系统，我希望 exclude 文件不存在、为空、或文件中的 IP 均不在 JSON 数据中时，返回 None（优雅降级，不报错）

#### ⚙️ 系统运行

107. 作为系统，我希望 exclude 文件中的 IP 先与 JSON 数据中的 IP 取交集，确定哪些 IP 实际需要被排除（仅在两者中都存在的 IP 才被排除）
109. 作为系统，我希望 exclude 文件中的重复 IP 在与 JSON 数据取交集之前先去重

#### 📤 输出要求

108. 作为系统，我希望 exclude 结果包含 exclude_ips（有效排除列表）、effective_count（有效数）、total_in_file（文件总数）、not_in_data_count（不在数据中数）、not_in_data_ips（不在数据中的 IP 列表）
110. 作为系统，我希望 exclude 结果中不包含不在 JSON 数据中的 IP（只排除实际存在的）

---

### 管线集成 — Phase 7 报告生成

#### ⚙️ 系统运行

111. 作为系统，我希望 Phase 7 无 exclude 文件时，报告生成函数收到 exclude_info=None
112. 作为系统，我希望 Phase 7 有 exclude 文件且匹配成功时，报告生成函数收到 exclude_info dict
114. 作为系统，我希望 Phase 7 调用 generate_trace_excel 和 generate_docx_report 生成报告

#### 🔴 异常处理

113. 作为系统，我希望 Phase 7 的 exclude 文件不存在时，报告生成函数收到 exclude_info=None（优雅降级）

## Implementation Decisions

### 模块架构

系统分为以下模块，每个模块都是可通过公共接口独立测试的深模块：

1. **protocols** — 定义 IPDataWriter、IPDataReader、ChannelProtocol、InMemoryChannel、InMemoryIPWriter、InMemoryIPReader 六个核心抽象
2. **writer / reader** — 基于文件系统的 JSON 存储，实现 IPDataWriter 和 IPDataReader
3. **channel/base** — ChannelFetcher Protocol 和 BaseBatchQuery 批量查询基类
4. **channel/registry** — ChannelRegistry 渠道注册表 + create_default_registry 工厂函数
5. **channel/* (10个)** — 每个渠道独立模块，暴露 XxxChannel 适配器类
6. **scenarios/trace_ip/classifier** — IPClassifier 分类引擎 + ClassifyResult 数据类
7. **scenarios/trace_ip/phase_runner** — PhaseRunner 阶段执行器
8. **scenarios/trace_ip/progress** — ProgressManager 断点续传
9. **scenarios/trace_ip/trace_utils** — 工具函数（is_china_ip / extract_all_domains / trace_priority 等）
10. **pipeline** — 管线编排（exclude_ips / 报告摘要 / Phase 集成）
11. **config** — Pydantic V2 Settings 配置

### 接口契约

**ChannelProtocol：**
- `channel_name: str` — 渠道唯一标识
- `validate() -> bool` — 验证渠道可用性（成功 True，任何异常 False）
- `fetch(ip: str, **kwargs) -> dict` — 获取 IP 信息，kwargs 全透传

**IPDataWriter：**
- `add_or_update_ip(ip, channel, data)` — 添加或更新 IP 的渠道数据
- `delete_ip(ip) -> bool` — 删除 IP 的所有数据
- `delete_channel(ip, channel) -> bool` — 删除 IP 的指定渠道数据

**IPDataReader：**
- `get_ip_data(ip) -> dict | None` — 获取 IP 的全部渠道数据
- `get_channel_data(ip, channel) -> dict | None` — 获取 IP 的指定渠道数据
- `list_all_ips() -> list` — 列出所有 IP
- `list_ip_channels(ip) -> list` — 列出 IP 的所有渠道
- `search_ips_by_channel(channel, key, value) -> list` — 按渠道字段搜索 IP

### 渠道错误返回格式

所有渠道的错误返回统一为：
```json
{"raw_error": true, "error_message": "具体描述"}
```

### 渠道 validate 行为矩阵

| 渠道 | 空 key/cookie | 网络异常 | API 报错 |
|------|-------------|---------|---------|
| fofa_host | exit(1) | exit(1) | exit(1) |
| fofa_search | exit(1) | exit(1) | exit(1) |
| aizhan | exit(1) | exit(1) | exit(1) |
| chinaz | exit(1) | **静默通过** | exit(1) |
| ipinfo_api | 用免费API | exit(1) | exit(1) |
| rdns_ptr | 不需要key | herror通过 | - |
| whois_query | 不需要key | 超时通过 | - |
| ssl_cert | 不需要key | 不验证 | - |
| port_scan | 不需要key | 返回None | - |
| zoomeye | exit(1) | **不在线验证** | - |

### 超时分类逻辑（aizhan / chinaz 共用）

错误消息中按优先级匹配：
1. 含 `"timeout"` 或 `"timed out"` → "网络超时"
2. 含 `403` / `429` / `forbidden` → "禁止请求"
3. 含 `"网络"` 或 `"连接"` → "网络中断"
4. 其他 → "查询失败"

## Testing Decisions

### 测试原则

1. **测试验证外部行为，不验证实现细节** — 通过公共接口（fetch / validate / parse_response）测试，不直接测试内部私有函数
2. **测试描述期望行为** — 测试断言的是代码应该做什么，不是代码现在做了什么
3. **bug 标记 xfail** — 已知 bug 的测试用 `@pytest.mark.xfail(reason="...")` 标记，不降低测试期望
4. **一个测试验证一件事** — 每个测试方法只验证一个行为
5. **垂直切片** — 一个测试 → 一个修复 → 一个验证，不批量写测试后批量修复

### Mock 策略

| 测试目标 | Mock 方式 | 原因 |
|---------|----------|------|
| 渠道 HTTP 请求 | `patch('channel.xxx.requests.get/post')` | 避免真实网络请求 |
| 渠道 Session | `patch('channel.xxx.requests.Session')` | chinaz 使用 Session |
| DNS 解析 | `patch('channel.rdns_ptr.socket.gethostbyaddr')` | 避免 DNS 查询 |
| WHOIS 库 | `patch('channel.whois_query.whois_query')` | 避免真实 WHOIS 查询 |
| SSL 连接 | `patch('channel.ssl_cert._get_ssl_cert_text')` | 避免 SSL 握手 |
| nmap 执行 | `patch('channel.port_scan.subprocess.run')` | 避免 nmap 依赖 |
| 配置 | `patch('channel.xxx.Settings')` | 隔离环境变量 |
| 延迟 | `patch('channel.xxx.apply_delay')` | 加速测试 |

**不 Mock 的部分：**
- BeautifulSoup HTML 解析 — 纯文本处理，无副作用
- parse_response / parse_nmap_xml / _parse_domains — 纯函数，直接测试
- format_output — 纯函数，直接测试
- InMemoryChannel / InMemoryIPWriter / InMemoryIPReader — 专为测试设计的替身

### 测试覆盖

| 模块 | 测试文件 | 测试数 |
|------|---------|--------|
| protocols (ChannelProtocol + InMemory) | test_channel_protocol.py | 36 |
| protocols (InMemoryIPWriter) | test_in_memory_writer.py | 9 |
| protocols (InMemoryIPReader) | test_in_memory_reader.py | 17 |
| writer + reader 协议兼容性 | test_protocol_conformance.py | 8 |
| channel/base (ChannelFetcher + BaseBatchQuery) | test_channel_base.py | 10 |
| channel/registry | test_channel_registry.py | 46 |
| channel/batch_run | test_batch_run.py | 36 |
| channel/fofa_host | test_fofa_host.py | 20 |
| channel/aizhan | test_aizhan.py | 31 |
| channel/chinaz | test_chinaz.py | 23 |
| channel/ipinfo_api | test_ipinfo_api.py | 22 |
| channel/rdns_ptr | test_rdns_ptr.py | 14 |
| channel/whois_query | test_whois_query.py | 20 |
| channel/ssl_cert | test_ssl_cert.py | 18 |
| channel/port_scan | test_port_scan.py | 18 |
| channel/fofa_search | test_fofa_search.py | 16 |
| channel/zoomeye | test_zoomeye.py | 16 |
| classifier | test_classifier.py | 28 |
| trace_utils | test_trace_utils.py | 26 |
| phase_runner | test_phase_runner.py | 10 |
| progress | test_progress.py | 11 |
| config | test_config.py | 25 |
| pipeline_registry | test_pipeline_registry.py | 8 |
| pipeline_exclude | test_pipeline_exclude.py | 14 |
| **合计** | **25 个文件** | **505** |

## Out of Scope

1. **渠道并行查询** — 当前按顺序执行，并行化是未来优化
2. **缓存层** — 查询结果不缓存，每次 fetch 都是实时请求
3. **重试机制** — 渠道失败后不自动重试（delay 仅控制请求间隔）
4. **Web UI** — 当前只有 CLI 和脚本接口
5. **数据库存储** — 当前使用文件系统 JSON 存储
6. **API 限流管理** — 各渠道的 rate limiting 由调用方自行管理
7. **修复已有 bug** — 6 个 xfail 测试对应的 bug 修复是独立任务

## Further Notes

### 已知待修复 Bug (6 个 xfail)

| # | 模块 | 期望行为 | 当前行为 | 严重度 |
|---|------|---------|---------|--------|
| 1 | trace_utils | is_china_ip country=None → False | TypeError | 高 |
| 2 | trace_utils | is_china_ip 双 None → False | TypeError | 高 |
| 3 | trace_utils | extract_all_domains domains 含 None → 跳过 | AttributeError | 中 |
| 4 | whois_query | parse_response 空列表字段 → None | 跳过字段 | 低 |
| 5 | ssl_cert | format_output issuer_cn 多词完整 | 空格截断 | 中 |
| 6 | port_scan | parse_nmap_xml 非法 portid → raw_error | int() 异常 | 低 |

### 已修复 Bug (2 个)

| # | 模块 | 修复内容 |
|---|------|---------|
| 1 | aizhan | 超时分类增加 "timed out" 匹配，ReadTimeout 不再被误分类 |
| 2 | chinaz | 同上 |

### 测试运行命令

```bash
cd ip_info_manager
python -m pytest tests/ -v -p no:dash
```

当前结果：**505 passed, 1 skipped, 6 xfailed, 1 warning**

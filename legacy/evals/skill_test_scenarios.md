# SKILL.md 重构测试场景

## 用户提供的测试场景

### 场景 1：溯源 IP 全流程

**用户输入：** "我给了你一批 ip 要溯源处理"

**AI 应该自动做的关键动作：**
- 询问/确认项目名称，引导使用 config_tool.py 修改 IP_TRACE_IP_PROJECT_NAME
- 确认运行阶段（完整流水线 / 从某阶段开始 / 只跑某阶段）
- 确认启用的渠道，引导配置渠道开关环境变量
- 生成正确的 `python -m scenarios.trace_ip` 运行命令
- 遇到 key/cookie 失效时，读取 config.md 了解如何用 config_tool.py 更新凭证
- 遇到频率限制/异常时，引导调整查询间隔时间
- 引导查看日志定位异常原因
- 引导 ai_analysis.py 的研判流程：batch 读取 → 分析 → writer.py add 写入结果

---

### 场景 2：IP 域名反查全流程

**用户输入：** "我给你一批 ip 要反查域名"

**AI 应该自动做的关键动作：**
- 询问/确认项目名称，引导修改 IP_IP_DOMAIN_LOOKUP_PROJECT_NAME
- 确认运行阶段和启用的渠道（6个渠道可选）
- 生成正确的 `python -m scenarios.ip_domain_lookup` 运行命令
- 遇到凭证/频率问题时，转跳 config.md 更新凭证和间隔
- 引导查看日志定位异常

---

### 场景 3：批量渠道查询

**用户输入：** "我给你一批 ip 要用 fofa 批量查询"（或其他渠道名）

**AI 应该自动做的关键动作：**
- 确认目标渠道，检查该渠道是否需要凭证
- 确认是否需要切换存储目录/项目名（IP_STORAGE_DIR / IP_STORAGE_NAME）
- 用 merge_ip_files.py 先验证 IP 文件
- 对于 ipinfo_api 特殊处理：确认是否使用 API 模式（有 Key）还是免 API 模式（--no-api）
- 生成正确的 `python scripts/batch_<channel>.py` 命令
- 遇到凭证问题时引导更新

---

### 场景 4：补充溯源 IP

**用户输入：** "我需要补充溯源一些 ip"

**AI 应该自动做的关键动作：**
- 确认当前项目名称（IP_TRACE_IP_PROJECT_NAME）
- 用 merge_ip_files.py 验证新 IP 文件
- 判断：是重新跑完整流水线，还是只补充采集新 IP（可能需要先查看已有数据判断哪些 IP 是新的）
- 生成运行命令，可能使用 --from-phase 参数跳过已完成阶段
- 或者引导将新 IP 追加到原 IP 文件后重新运行

---

### 场景 5：Fofa 导出的混合数据反查域名

**用户输入：** "我提供了 ip:端口 和 域名:端口的文件，这些文件是 fofa 查询的，我要反查他们域名"

**AI 应该自动做的关键动作：**
- 识别数据中 IP 和域名的混合格式，解析提取
- 从文件中分离出纯 IP 列表和纯域名列表
- 对域名列表做 DNS 解析，获取域名映射的 IP
- 将映射得到的 IP 从原 IP 列表中去除（避免重复查询）
- 对剩余 IP 列表执行 ip_domain_lookup 流水线做域名反查
- 最终输出报告 = 剩余 IP 的反查结果 + 原有域名部分

> 注意：此场景需要的代码还未完成，仅作为 AI 行为参考。

---

## AI 补充的测试场景

### 场景 6：单条 IP 快速查询

**用户输入：** "帮我查一下 1.2.3.4 这个 IP 的信息"

**AI 应该做的关键动作：**
- 先用 `reader.py get "1.2.3.4"` 查看是否已有数据
- 如果没有数据或数据不完整，询问用户需要哪些渠道
- 使用对应的 `channel/<channel>.py "1.2.3.4"` 查询
- 展示查询结果

---

### 场景 7：查看已有数据并导出

**用户输入：** "帮我把目前所有 IP 的 fofa_host 和 ipinfo_api 数据整理出来"

**AI 应该做的关键动作：**
- 使用 `reader.py list --include-channel fofa_host ipinfo_api --export-excel output.xlsx`
- 不需要查询新数据，只用 reader + exporter

---

### 场景 8：凭证过期更新

**用户输入：** "爱站的 cookie 过期了，帮我更新一下"

**AI 应该做的关键动作：**
- 读取 config.md 了解 config_tool.py 用法
- 引导用户提供新 cookie
- 使用 `python tools/config_tool.py set IP_AIZHAN_COOKIE "新cookie值"`
- 不直接编辑 .env 文件

---

### 场景 9：断点续查 / 查看进度

**用户输入：** "之前跑的 fofa 批量查询中断了，帮我继续"

**AI 应该做的关键动作：**
- 确认之前使用的数据目录和文件
- 检查 .progress 文件是否存在
- 直接重新运行相同的批量命令（会自动跳过已处理的 IP）
- 如需查看进度，引导使用 progress_tool.py

---

### 场景 10：溯源流水线自定义分类规则

**用户输入：** "我想在溯源流水线里加一条规则，把所有 .cloud.tencent.com 的 RDNS 归类为腾讯云"

**AI 应该做的关键动作：**
- 读取 trace-ip-pipeline.md 中的分类规则部分
- 引导修改 custom_rules.json（不是 builtin_rules.json）
- 说明规则格式：field / match / type
- 生成正确的 JSON 片段

---

### 场景 11：多个项目切换

**用户输入：** "我之前处理了一批叫 0424攻击IP 的溯源数据，现在要处理新的一批叫 0515攻击IP，怎么切换？"

**AI 应该做的关键动作：**
- 使用 config_tool.py set IP_TRACE_IP_PROJECT_NAME "0515攻击IP"
- 确认新的输出目录 data/trace_ip/0515攻击IP/ 会自动创建
- 说明不同项目互不干扰

---

### 场景 12：IP 文件合并与去重

**用户输入：** "我有 3 个 IP 文件，帮我合并成一个去重的"

**AI 应该做的关键动作：**
- 使用 `python tools/merge_ip_files.py file1.txt file2.txt file3.txt -o merged.txt`
- 如果有无效 IP 加 --show-invalid 展示

---

### 场景 13：查看某 IP 已有的所有渠道数据

**用户输入：** "帮我看看 192.168.1.1 目前有哪些渠道的数据"

**AI 应该做的关键动作：**
- `python reader.py list-channels "192.168.1.1"`
- 或 `python reader.py get "192.168.1.1"` 查看完整数据

---

### 场景 14：溯源报告生成后追加 AI 研判

**用户输入：** "溯源报告跑完了，现在需要对分类为 other 的 IP 进行 AI 研判"

**AI 应该做的关键动作：**
- 使用 `python tools/ai_analysis.py count --categories other` 查看待研判数量
- 使用 `python tools/ai_analysis.py batch --categories other` 获取待研判数据
- AI 分析后用 `python writer.py add "<IP>" ai_analysis key=value ...` 写入研判结果
- 可重新生成 Word 报告包含研判结果

---

### 场景 15：删除错误数据

**用户输入：** "之前 5.6.7.8 这个 IP 的 whois 数据查错了，帮我删掉"

**AI 应该做的关键动作：**
- `python writer.py delete-channel "5.6.7.8" whois`
- 询问是否需要重新查询：`python channel/whois_query.py "5.6.7.8"`

---

### 场景 16：批量查询前的环境检查

**用户输入：** "我要用 fofa 和爱站批量查一批 IP，先帮我检查下环境"

**AI 应该做的关键动作：**
- 检查 IP_FOFA_API_KEY 和 IP_AIZHAN_COOKIE 是否配置
- 可用 `python tools/config_tool.py check` 检查配置完整性
- 检查 IP 文件格式是否正确（merge_ip_files.py 验证）
- 提醒查询间隔设置

---

### 场景 17：域名验证（独立使用 verify_ip_domain.py）

**用户输入：** "帮我验证一下数据里爱站反查到的域名现在还有没有效"

**AI 应该做的关键动作：**
- `python tools/verify_ip_domain.py <json文件> --channel aizhan`
- 先 --dry-run 看结果，确认后再正式写入

---

### 场景 18：查询间隔调整

**用户输入：** "fofa 查询太快被限频了，帮我调慢一点"

**AI 应该做的关键动作：**
- 使用 config_tool.py set IP_FOFA_QUERY_DELAY 5.0（加大间隔）
- 不直接改 .env 文件
- 不改代码

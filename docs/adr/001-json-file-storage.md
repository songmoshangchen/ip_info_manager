# ADR-001: 使用 JSON 文件作为数据存储

## 状态

已采纳

## 上下文

项目需要存储 IP 情报数据，每个 IP 包含多个渠道的采集结果。需要选择一种数据存储方案。

可选方案：
1. 关系型数据库（SQLite / PostgreSQL）
2. NoSQL 数据库（MongoDB / Redis）
3. JSON 文件

## 决策

选择 **JSON 文件** 作为数据存储。

数据组织方式：以 JSON 文件为存储单元，IP 地址作为顶层 key，渠道名作为二级 key：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "fofa_host": { ... },
    "rdns_ptr": { ... }
  }
}
```

存储路径规则：
- 通用数据：`data/{IP_STORAGE_DIR}/{IP_STORAGE_NAME}.json`
- 溯源场景：`data/trace_ip/{project_name}/{project_name}.json`
- 域名反查：`data/ip_domain_lookup/{project_name}/{project_name}.json`

## 理由

1. **零依赖** — 无需安装数据库服务
2. **可移植性** — 单文件复制即可迁移数据
3. **人类可读** — 可直接用文本编辑器查看和调试
4. **场景隔离** — 不同任务使用不同 JSON 文件，天然隔离
5. **简单性** — 项目规模有限（单次任务通常几十到几百个 IP），JSON 性能足够

## 后果

**优势：**
- 部署简单，`pip install` 后即可使用
- 数据文件可直接版本管理或分享
- 调试直观

**劣势：**
- 大数据量时（>10000 IP）读写性能下降（全量读写）
- 无并发写入保护（通过 BatchIPWriter 上下文管理器缓解）
- 不支持复杂查询（通过 reader.py 的 search 方法做简单过滤）
- 文件损坏风险（无事务保护）

**缓解措施：**
- `BatchIPWriter` 批量写入减少 IO 次数
- `ProgressManager` 断点续查避免重复工作
- 每个场景独立 JSON 文件，控制单文件大小

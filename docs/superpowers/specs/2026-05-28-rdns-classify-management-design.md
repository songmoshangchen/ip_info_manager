# RDNS 分类闭环管理设计

## 目标

将分类为"其他"的 RDNS hostname 逐步消化，通过 Export → 人工审查 → Import 闭环，持续完善 `builtin_rules.json`（通用规则）和 `custom_rules.json`（异常规则），消除未分类 RDNS，防止爬虫/扫描器漏网。

## 架构

```
Phase 2 分类完成
  → 自动调用 export_unclassified_rdns()
  → 读取 IP 数据 (via IPDataReader)
  → 筛选 category="other" 且有 RDNS hostname 的 IP
  → 按 hostname 去重
  → 生成 Excel 报表
  → 日志: "还有 X 个未处理 RDNS，报表位于 xxx，请处理"

人工审查 Excel
  → 填写 category / match_type / match_value / note

scripts/import_rdns_rules.py
  → 读取标注后的 Excel
  → 验证 + 合并到 custom_rules.json
  → 写回
```

## Excel 报表格式

文件名: `{prefix}.unclassified_rdns.xlsx`

### Sheet 1: 未分类RDNS

| is\_sample | hostname | field  | category | match\_type | match\_value | note   | new\_label | new\_description | new\_need\_deep\_query |
| ---------- | -------- | ------ | -------- | ----------- | ------------ | ------ | ---------- | ---------------- | ---------------------- |
| <br />     | <br />   | <br /> | <br />   | <br />      | <br />       | <br /> | <br />     | <br />           | <br />                 |

**列说明**:

| 列                      | 预填充                  | 用户操作   | 说明                                                                                            |
| ---------------------- | -------------------- | ------ | --------------------------------------------------------------------------------------------- |
| is\_sample             | 说明/样例/空              | 不修改    | `说明`=字段说明行, `样例`=参考样例, 空=待处理数据                                                                |
| hostname               | ✅                    | 不修改    | RDNS 反解域名                                                                                     |
| field                  | ✅ rdns\_ptr.hostname | 不修改    | 匹配字段                                                                                          |
| category               | 空                    | **填写** | 分类 key，如 cloud\_provider/cdn/crawler\_scanner/residential/invalid\_rdns/excluded\_domain 或新分类 |
| match\_type            | 空                    | **填写** | suffix/contains/prefix/exact/regex                                                            |
| match\_value           | 空                    | **填写** | 匹配值，如 .amazonaws.com                                                                          |
| note                   | 空                    | **填写** | 备注说明                                                                                          |
| new\_label             | 空                    | 新分类时填写 | 新分类的显示名称                                                                                      |
| new\_description       | 空                    | 新分类时填写 | 新分类的描述                                                                                        |
| new\_need\_deep\_query | 空                    | 新分类时填写 | 是/否，新分类是否需要深度查询                                                                               |

**预填行**:

1. **说明行** (is\_sample="说明"): 每列写该列的含义和约束
2. **样例行** (is\_sample="样例"): 每种 category 一个样例 + 一个新分类样例，共 7-8 行
3. **数据行** (is\_sample=空): 未分类的 RDNS hostname，等待用户填写

### Sheet 2: 参考样例

从 `builtin_rules.json` 提取，每个 category 展示 2-3 条代表性规则:

| category | label  | match\_type | match\_value | note   | example\_hostname |
| -------- | ------ | ----------- | ------------ | ------ | ----------------- |
| <br />   | <br /> | <br />      | <br />       | <br /> | <br />            |

此 Sheet 仅供人工参考，import 脚本不读取。

## 新增文件

| 文件                                          | 说明                                     |
| ------------------------------------------- | -------------------------------------- |
| `src/ip_info/export/rdns_classify_excel.py` | 导出: 从存储层读数据 → 生成 Excel                 |
| `scripts/import_rdns_rules.py`              | 导入: 读取标注 Excel → 更新 custom\_rules.json |

## 导出逻辑 (`rdns_classify_excel.py`)

### 入口函数

```python
def export_unclassified_rdns(
    reader: IPDataReader,
    output_dir: str,
    prefix: str,
    rules_dir: str,
) -> int:
    """导出未分类 RDNS Excel，返回未分类 RDNS 数量。"""
```

### 流程

1. `reader.list_all_ips_data()` 获取全部 IP 数据
2. 过滤: `classifier.category == "other"` AND `rdns_ptr.has_ptr == True`
3. 提取 `rdns_ptr.hostname`，按 hostname 去重（set）
4. 加载 `builtin_rules.json` 提取参考样例
5. 生成 Excel:

   * Sheet 1: 说明行 + 样例行 + 数据行

   * Sheet 2: 参考样例
6. 日志输出未分类数量和文件路径
7. 返回未分类 RDNS 数量

### Excel 生成方式

复用 `generate_grouped_excel()` 生成 Sheet 2（按 category 分组）。
Sheet 1 因为有说明行/样例行/数据行混合结构，直接使用 openpyxl 生成（与 `excel_grouped.py` 相同的样式模式）。

## 导入逻辑 (`import_rdns_rules.py`)

### 命令行

```
python scripts/import_rdns_rules.py <excel_file> [--rules-dir config/classifier] [--dry-run]
```

### 流程

1. 读取 Excel Sheet 1
2. 跳过 is\_sample 列非空的行（说明行 + 样例行）
3. 逐行验证:

   * category 不能为空

   * match\_type 必须是 suffix/contains/prefix/exact/regex 之一

   * match\_value 不能为空

   * 如果 category 不在已有分类中，new\_label/new\_description/new\_need\_deep\_query 必须填写
4. 读取 `custom_rules.json`
5. 合并:

   * 已有 category: 追加 pattern 到 patterns 列表

   * 新 category: 创建新条目
6. 写回 `custom_rules.json`
7. `--dry-run` 模式只验证不写入

### 验证规则

| 规则                        | 说明                                                                       |
| ------------------------- | ------------------------------------------------------------------------ |
| category 必填               | 不能为空                                                                     |
| match\_type 枚举            | suffix/contains/prefix/exact/regex                                       |
| match\_value 必填           | 不能为空                                                                     |
| 重复检查                      | 同一 category + match\_value 不重复添加（大小写不敏感，与分类引擎一致）                         |
| 新分类完整性                    | 新 category 必须同时提供 new\_label + new\_description + new\_need\_deep\_query |
| new\_need\_deep\_query 枚举 | 是/否                                                                      |

### 合并策略

* 所有新规则统一写入 `custom_rules.json`（builtin\_rules.json 不可修改）

* "已有分类"判断: 同时检查 `builtin_rules.json` 和 `custom_rules.json` 的 key

* 如果 category 在 builtin 中已存在（如 cloud\_provider），仍在 custom 中创建同名 category 并追加 pattern，`load_rules()` 合并时 custom 会覆盖 builtin 同名 key

* 如果 category 仅在 custom 中已存在，追加 pattern 到其 patterns 列表

* 如果 category 全新，创建新条目

## 集成点

### Phase 2 自动导出

`ClassifyTagPhase` 构造函数增加 `output_dir` 和 `prefix` 参数。分类完成后自动调用:

```python
from ip_info.export.rdns_classify_excel import export_unclassified_rdns

unclassified_count = export_unclassified_rdns(
    reader=self._reader,
    output_dir=self._output_dir,
    prefix=self._prefix,
    rules_dir=self._rules_dir,
)
if unclassified_count > 0:
    logger.info("还有 %d 个未处理 RDNS，报表位于 %s，请处理", unclassified_count, excel_path)
```

`run_pipeline.py` 中创建 `ClassifyTagPhase` 时传入 `output_dir` 和 `prefix`。不修改 `PipelineContext`。

## 未来扩展 (方案 C)

* 智能推断 match\_type 和 match\_value（基于 hostname 模式分析）

* 自动建议 category（基于 ipinfo\_api.as\_name 关联分析）

* 交互式 CLI 逐个确认

## 测试策略

| 层级   | 测试内容                                       |
| ---- | ------------------------------------------ |
| 单元测试 | `rdns_classify_excel.py` 的数据提取、去重、Excel 生成 |
| 单元测试 | import 逻辑的验证、合并、写回                         |
| 集成测试 | 完整 export → import 闭环                      |
| Fake | FakeReader 提供测试数据                          |


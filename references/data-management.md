# 数据读写操作

当用户需要查看、添加、删除、搜索 IP 数据时读取此文件。

## 决策树

```
用户想查看某个 IP 的数据 → reader.py get
用户想查看某个 IP 的某渠道数据 → reader.py get-channel
用户想查看所有/筛选 IP 列表 → reader.py list
用户想搜索含特定渠道/字段的 IP → reader.py search
用户想导出数据到 Excel → reader.py list --export-excel
用户想添加/更新 IP 的渠道数据 → writer.py add
用户想删除某个 IP → writer.py delete-ip
用户想删除某个 IP 的某渠道 → writer.py delete-channel
```

## 写入数据（writer.py）

所有命令在项目根目录 `ip_info_manager/` 下执行。

### 添加/更新 IP 渠道数据

```bash
python writer.py add "<IP>" "<渠道名>" <key1>=<value1> <key2>=<value2> ...
```

值类型自动推断：`true/false` → 布尔，纯数字 → 整数，含小数点 → 浮点，其余 → 字符串。

示例：

```bash
python writer.py add "192.168.1.1" "analysis" severity="高" action="保留" note="疑似攻击者VPS"
```

### 删除数据

```bash
python writer.py delete-ip "192.168.1.1"
python writer.py delete-channel "192.168.1.1" "analysis"
```

## 查询数据（reader.py）

### 获取单个 IP 数据

```bash
python reader.py get "1.2.3.4"
python reader.py get-channel "1.2.3.4" fofa_host
python reader.py list-channels "1.2.3.4"
```

### 列出 IP 列表

```bash
python reader.py list
python reader.py list --detail
python reader.py list --start 10 --end 50
python reader.py list --include-channel fofa_host
python reader.py list --exclude-channel kimi
python reader.py list --detail --include-channel fofa_host --output result.txt
```

### 导出 Excel

```bash
python reader.py list --export-excel output.xlsx
python reader.py list --include-channel fofa_host ipinfo_api --export-excel output.xlsx
python reader.py list --exclude-channel kimi --export-excel output.xlsx
```

导出的 Excel 包含蓝色表头、自动列宽、按渠道分组的字段展示。

### 搜索 IP

```bash
python reader.py search fofa_host
python reader.py search fofa_host --key country_name --value "China"
```

## 数据格式

所有 IP 数据存储在 JSON 文件中，结构为 `{ "IP地址": { "ip": "...", "渠道名": {...}, ... } }`。

具体存储路径由配置决定：
- channel/batch 通用数据：`data/{IP_STORAGE_DIR}/{IP_STORAGE_NAME}.json`
- 场景数据：`data/{场景名}/{项目名}/{项目名}.json`

不确定参数时可用 `python writer.py --help` 或 `python reader.py --help` 查看。

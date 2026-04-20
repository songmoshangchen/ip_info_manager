# IP Info Manager — IP 信息管理工具

一个用于批量采集、存储、查询和导出 IP 地址多维度情报信息的命令行工具。

## 功能概述

- **多渠道情报采集**：通过 Fofa、IPInfo、RDNS PTR、Whois、爱站、站长之家等渠道批量查询 IP 信息
- **JSON 数据存储**：所有 IP 数据以 JSON 格式统一存储，按 IP + 渠道组织
- **命令行查询**：支持按 IP、渠道、字段等条件检索数据
- **Excel 导出**：将 IP 数据导出为格式化的 Excel 文件
- **断点续查**：批量查询支持进度保存，中断后可继续
- **并发查询**：RDNS 查询提供多线程并发版本
- **IP 反查域名**：通过爱站网和站长之家查询 IP 绑定的域名信息

## 目录结构

```
ip_info_manager/
├── .env                    # 环境变量配置（API Key 等）
├── .env.example            # 环境变量配置模板
├── requirements.txt        # Python 依赖
├── writer.py               # IP 数据写入器
├── reader.py               # IP 数据读取器
├── exporter.py             # Excel 导出器
├── writer_example.py       # 写入器使用示例
├── channel/                # 数据采集渠道
│   ├── fofa.py             # Fofa API 查询
│   ├── ipinfo_api.py       # IPInfo API 查询（需 Token）
│   ├── ipinfo_noapi.py     # IPInfo 免 API 查询
│   ├── rdns_ptr.py         # RDNS PTR 反向解析
│   ├── whois_query.py      # Whois 查询
│   ├── aizhan.py           # 爱站网 IP 反查域名
│   ├── chinaz.py           # 站长之家 IP 反查域名
│   └── data/               # 渠道级数据
│       └── ip_data.json
├── scripts/                # 批量查询脚本
│   ├── batch_fofa.py       # 批量 Fofa 查询
│   ├── batch_ipinfo_api.py # 批量 IPInfo 查询
│   ├── batch_rdns_ptr.py   # 批量 RDNS 查询（单线程）
│   ├── batch_rdns_ptr_concurrent.py  # 批量 RDNS 查询（多线程）
│   ├── batch_whois.py      # 批量 Whois 查询
│   ├── batch_aizhan.py     # 批量爱站网查询
│   └── batch_chinaz.py     # 批量站长之家查询
├── tools/                  # 辅助工具
│   ├── compare_ip_files.py # IP 文件比较
│   └── process_ip_list.py  # IP 列表处理（验证/去重）
└── data/                   # 数据存储目录
    ├── ip_data.json        # 主数据文件
    ├── *.progress          # 批量查询进度文件
    └── *.xlsx              # 导出的 Excel 文件
```

## 环境配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

当前依赖：
- `pydantic-settings>=2.0.0` — 配置管理
- `ipinfo>=5.0.0` — IPInfo SDK
- `beautifulsoup4>=4.12.0` — HTML 解析（爱站/站长之家）
- `requests>=2.28.0` — HTTP 请求
- `openpyxl` — Excel 导出
- `python-whois` — Whois 查询（可选）

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入实际值：

```bash
IP_STORAGE_DIR=data
IP_STORAGE_FILENAME=ip_data.json
IP_FOFA_API_KEY=your_fofa_api_key_here
IP_IPINFO_ACCESS_TOKEN=your_ipinfo_access_token_here
IP_FOFA_QUERY_DELAY=1.1
IP_IPINFO_QUERY_DELAY=1.1
IP_AIZHAN_COOKIE=your_aizhan_cookie_here
IP_AIZHAN_QUERY_DELAY=2
IP_CHINAZ_COOKIE=your_chinaz_cookie_here
IP_CHINAZ_QUERY_DELAY=2
```

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `IP_STORAGE_DIR` | 否 | `data` | 数据存储目录 |
| `IP_STORAGE_FILENAME` | 否 | `ip_data.json` | 数据文件名 |
| `IP_FOFA_API_KEY` | 使用 Fofa 时必填 | — | Fofa API Key |
| `IP_IPINFO_ACCESS_TOKEN` | 使用 IPInfo API 时必填 | — | IPInfo Access Token |
| `IP_AIZHAN_COOKIE` | 使用爱站时必填 | — | 爱站网 Cookie（浏览器登录后获取） |
| `IP_CHINAZ_COOKIE` | 否 | 空 | 站长之家 Cookie（可选，有 Cookie 可查更多信息） |
| `IP_FOFA_QUERY_DELAY` | 否 | `1.1` | Fofa 查询间隔（秒） |
| `IP_IPINFO_QUERY_DELAY` | 否 | `1.1` | IPInfo 查询间隔（秒） |
| `IP_AIZHAN_QUERY_DELAY` | 否 | `2` | 爱站查询间隔（秒） |
| `IP_CHINAZ_QUERY_DELAY` | 否 | `2` | 站长之家查询间隔（秒） |

## 数据存储格式

所有 IP 数据存储在 `data/ip_data.json`，结构如下：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "fofa": { ... },
    "ipinfo_api": { ... },
    "rdns_ptr": { ... },
    "whois": { ... },
    "aizhan": {
      "success": true,
      "location": "中国广东广州",
      "isp": "电信",
      "domain_count": 5,
      "domains": [{"domain": "example.com", "title": "示例网站"}]
    },
    "chinaz": {
      "success": true,
      "location": "广东省广州市",
      "isp": "电信",
      "domains": [{"domain": "example.com", "start_time": "2024-01-01", "end_time": "2026-01-01"}]
    }
  }
}
```

每个 IP 下包含 `ip` 字段和若干渠道数据，渠道名作为 key。不同渠道的数据结构由对应采集脚本决定。

## 核心模块

### writer.py — IP 数据写入器

用于添加、更新和删除 IP 数据。

```bash
# 添加/更新 IP 渠道数据
python writer.py add <IP> <渠道名> <key1=value1> <key2=value2> ...

# 删除整个 IP
python writer.py delete-ip <IP>

# 删除 IP 的某个渠道
python writer.py delete-channel <IP> <渠道名>
```

**示例：**

```bash
python writer.py add "1.2.3.4" "kimi" net_type="阿里云ECS" trace_value="高" action="保留" note="测试"
```

### reader.py — IP 数据读取器

用于查询和检索已存储的 IP 数据。

```bash
# 获取 IP 全部数据
python reader.py get <IP>

# 获取 IP 指定渠道数据
python reader.py get-channel <IP> <渠道名>

# 列出所有 IP
python reader.py list
python reader.py list --detail                    # 显示详细信息
python reader.py list --start 10 --end 20         # 分页
python reader.py list --include-channel fofa       # 仅显示含 fofa 渠道的 IP
python reader.py list --exclude-channel kimi       # 排除含 kimi 渠道的 IP
python reader.py list --export-excel output.xlsx   # 导出到 Excel
python reader.py list --output result.txt          # 输出到文件

# 列出 IP 的所有渠道
python reader.py list-channels <IP>

# 按渠道搜索 IP
python reader.py search <渠道名>
python reader.py search <渠道名> --key <字段> --value <值>
```

### exporter.py — Excel 导出器

一般通过 `reader.py` 的 `--export-excel` 参数调用，也可单独使用。导出的 Excel 包含：
- 蓝色表头、白色加粗字体
- 自动列宽适配
- 按渠道分组的字段展示

## 数据采集渠道

### channel/fofa.py — Fofa 查询

调用 Fofa API 获取 IP 的主机详情（端口、服务、操作系统等）。

```bash
python channel/fofa.py <IP地址>
```

需要配置 `IP_FOFA_API_KEY`。

### channel/ipinfo_api.py — IPInfo API 查询

通过 IPInfo 官方 SDK 获取 IP 地理位置和 ASN 信息。

```bash
python channel/ipinfo_api.py <IP地址>
```

需要配置 `IP_IPINFO_ACCESS_TOKEN`。

### channel/ipinfo_noapi.py — IPInfo 免 API 查询

通过 `ipinfo.io` 公开接口获取 IP 信息，无需 Token。

```bash
python channel/ipinfo_noapi.py <IP地址>
```

### channel/rdns_ptr.py — RDNS PTR 反向解析

通过 DNS PTR 记录查询 IP 的反向域名。

```bash
python channel/rdns_ptr.py <IP地址>
```

### channel/whois_query.py — Whois 查询

查询 IP 或域名的注册信息。

```bash
python channel/whois_query.py <IP地址或域名>
```

需要安装 `python-whois`：`pip install python-whois`

### channel/aizhan.py — 爱站网 IP 反查域名

通过爱站网（dns.aizhan.com）查询 IP 绑定的域名信息，包括域名、网站标题、归属地、运营商。

```bash
python channel/aizhan.py <IP地址>
```

需要配置 `IP_AIZHAN_COOKIE`（浏览器登录爱站网后获取 Cookie）。

返回数据格式：
```json
{
  "success": true,
  "location": "中国广东广州",
  "isp": "电信",
  "domain_count": 5,
  "domains": [{"domain": "example.com", "title": "示例网站"}],
  "query_time": "2026-04-20T10:00:00"
}
```

### channel/chinaz.py — 站长之家 IP 反查域名

通过站长之家（ipchaxun.com）查询 IP 绑定的域名信息，包括域名、绑定时间段、归属地、运营商。

```bash
python channel/chinaz.py <IP地址>
```

Cookie 可选配置（`IP_CHINAZ_COOKIE`），有 Cookie 可查询更多信息。

返回数据格式：
```json
{
  "success": true,
  "location": "广东省广州市",
  "isp": "电信",
  "domains": [{"domain": "example.com", "start_time": "2024-01-01", "end_time": "2026-01-01"}],
  "query_time": "2026-04-20T10:00:00"
}
```

## 批量查询脚本

所有批量脚本的使用方式一致：

```bash
python scripts/<脚本名> <IP文件路径>
```

IP 文件为纯文本，每行一个 IP 地址。

| 脚本 | 渠道 | 说明 |
|------|------|------|
| `batch_fofa.py` | fofa | 批量 Fofa 查询 |
| `batch_ipinfo_api.py` | ipinfo_api | 批量 IPInfo 查询 |
| `batch_rdns_ptr.py` | rdns_ptr | 批量 RDNS 查询（单线程） |
| `batch_rdns_ptr_concurrent.py` | rdns_ptr | 批量 RDNS 查询（多线程） |
| `batch_whois.py` | whois | 批量 Whois 查询 |
| `batch_aizhan.py` | aizhan | 批量爱站网 IP 反查域名 |
| `batch_chinaz.py` | chinaz | 批量站长之家 IP 反查域名 |

**并发 RDNS 查询**支持指定线程数：

```bash
python scripts/batch_rdns_ptr_concurrent.py ips.txt 20
```

### 断点续查机制

每个批量脚本会自动生成 `文件名.渠道名.progress` 进度文件，记录已处理的 IP。中断后重新运行会自动跳过已处理的 IP。如需重新查询，删除对应的 `.progress` 文件即可。

## 辅助工具

### tools/compare_ip_files.py — IP 文件比较

比较两个 IP 文件，找出重复 IP 和差异 IP。

```bash
python tools/compare_ip_files.py <文件A> <文件B>
```

输出：
- 同时在 A 和 B 中的 IP（重复）
- 只在 B 中的 IP（新增）

### tools/process_ip_list.py — IP 列表处理

对 IP 列表进行验证和去重。

```bash
python tools/process_ip_list.py <文件路径>
python tools/process_ip_list.py <文件路径> --show-valid    # 显示有效 IP
python tools/process_ip_list.py <文件路径> --show-invalid   # 显示无效 IP
python tools/process_ip_list.py <文件路径> --show-all       # 显示全部
```

支持 IPv4 和 IPv6 格式验证。

# 凭证管理与环境配置

当用户需要更新 API Key/Cookie、查看或修改环境变量配置时读取此文件。

**重要原则：所有配置变更必须通过 `tools/config_tool.py` 执行，不要直接编辑 `.env` 文件，不要修改源代码。**

## 凭证更新（最常用）

### 查看当前凭证状态

```bash
python tools/config_tool.py status
python tools/config_tool.py check
```

### 更新 Fofa API Key

```bash
python tools/config_tool.py set IP_FOFA_API_KEY "新的key值"
```

### 更新爱站 Cookie

```bash
python tools/config_tool.py set IP_AIZHAN_COOKIE "新的cookie值"
```

### 更新站长之家 Cookie

```bash
python tools/config_tool.py set IP_CHINAZ_COOKIE "新的cookie值"
```

### 更新 ZoomEye API Key

```bash
python tools/config_tool.py set IP_ZOOMEYE_API_KEY "新的key值"
```

### 更新 IPInfo Token

```bash
python tools/config_tool.py set IP_IPINFO_ACCESS_TOKEN "新的token值"
```

## config_tool.py 完整用法

```bash
python tools/config_tool.py list                                       # 列出所有配置项
python tools/config_tool.py list --group credentials                   # 按分组列出
python tools/config_tool.py groups                                     # 查看所有分组
python tools/config_tool.py status                                     # 配置状态总览
python tools/config_tool.py check                                      # 检查配置完整性
python tools/config_tool.py info IP_FOFA_API_KEY                       # 查看配置项详情
python tools/config_tool.py get IP_STORAGE_DIR                         # 获取配置值
python tools/config_tool.py set IP_STORAGE_DIR data/202604             # 设置配置值
python tools/config_tool.py delete IP_STORAGE_DIR                      # 删除配置项
python tools/config_tool.py bulk-set IP_STORAGE_DIR=data IP_STORAGE_NAME=ip_data  # 批量设置
```

所有配置项必须以 `IP_` 为前缀。

不确定用法时用 `python tools/config_tool.py --help`。

## 查询间隔与超时配置

遇到限频或超时时调整：

```bash
python tools/config_tool.py set IP_FOFA_QUERY_DELAY 5.0          # Fofa 间隔改为 5 秒
python tools/config_tool.py set IP_AIZHAN_QUERY_DELAY 3.0        # 爱站间隔改为 3 秒
python tools/config_tool.py set IP_RDNS_QUERY_TIMEOUT 3.0        # RDNS 超时改为 3 秒
```

### 默认值参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| IP_FOFA_QUERY_DELAY | 2.0 | Fofa 查询间隔（秒） |
| IP_FOFA_QUERY_TIMEOUT | 30.0 | Fofa 查询超时（秒） |
| IP_FOFA_VALIDATE_TIMEOUT | 10.0 | Fofa 凭证验证超时（秒） |
| IP_IPINFO_QUERY_DELAY | 1.2 | IPInfo 查询间隔（秒） |
| IP_IPINFO_QUERY_TIMEOUT | 30.0 | IPInfo 查询超时（秒） |
| IP_IPINFO_VALIDATE_TIMEOUT | 30.0 | IPInfo 凭证验证超时（秒） |
| IP_RDNS_QUERY_TIMEOUT | 1.5 | RDNS 查询超时（秒） |
| IP_RDNS_QUERY_DELAY | 0.1 | RDNS 批量查询间隔（秒） |
| IP_WHOIS_QUERY_TIMEOUT | 2.0 | Whois 查询超时（秒） |
| IP_WHOIS_QUERY_DELAY | 0.5 | Whois 批量查询间隔（秒） |
| IP_AIZHAN_QUERY_DELAY | 2.0 | 爱站查询间隔（秒） |
| IP_AIZHAN_QUERY_TIMEOUT | 15.0 | 爱站查询超时（秒） |
| IP_AIZHAN_VALIDATE_TIMEOUT | 10.0 | 爱站凭证验证超时（秒） |
| IP_CHINAZ_QUERY_DELAY | 2.0 | 站长之家查询间隔（秒） |
| IP_CHINAZ_QUERY_TIMEOUT | 15.0 | 站长之家查询超时（秒） |
| IP_CHINAZ_VALIDATE_TIMEOUT | 10.0 | 站长之家凭证验证超时（秒） |
| IP_ZOOMEYE_QUERY_DELAY | 2.0 | ZoomEye 查询间隔（秒） |
| IP_ZOOMEYE_QUERY_TIMEOUT | 30.0 | ZoomEye 查询超时（秒） |
| IP_SSL_CERT_PORT | 443 | SSL 证书获取端口 |
| IP_SSL_CERT_TIMEOUT | 5 | SSL 连接超时（秒） |
| IP_SSL_CERT_OPENSSL_TIMEOUT | 10.0 | SSL 证书 OpenSSL 超时（秒） |
| IP_SSL_CERT_QUERY_DELAY | 0.5 | SSL 证书查询间隔（秒） |

## 溯源IP流水线渠道配置

控制溯源流水线各阶段渠道的启用/禁用（默认全部启用）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| IP_TRACE_IP_PHASE1_IPINFO_ENABLED | true | Phase 1：启用 IPInfo 查询 |
| IP_TRACE_IP_PHASE1_RDNS_PTR_ENABLED | true | Phase 1：启用 RDNS PTR 反向解析 |
| IP_TRACE_IP_PHASE3_AIZHAN_ENABLED | true | Phase 3：启用爱站网 IP 反查域名 |
| IP_TRACE_IP_PHASE3_CHINAZ_ENABLED | true | Phase 3：启用站长之家 IP 反查域名 |
| IP_TRACE_IP_PHASE3_FOFA_HOST_ENABLED | true | Phase 3：启用 Fofa Host 聚合查询 |
| IP_TRACE_IP_PHASE4_DNS_VERIFY_ENABLED | true | Phase 4：DNS 域名正向验证 |
| IP_TRACE_IP_DNS_VERIFY_TIMEOUT | 3.0 | DNS 域名验证超时（秒） |
| IP_TRACE_IP_DNS_VERIFY_CONCURRENCY | 10 | DNS 域名验证并发线程数 |

### 端口扫描配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| IP_TRACE_IP_PHASE5_PORT_SCAN_ENABLED | false | Phase 5：启用端口扫描（默认关闭） |
| IP_TRACE_IP_PORT_SCAN_ENGINE | nmap | 端口扫描引擎 |
| IP_TRACE_IP_PORT_SCAN_NMAP_PATH | nmap | nmap 可执行文件路径 |
| IP_TRACE_IP_PORT_SCAN_TIMEOUT | 90 | 单 IP 扫描超时（秒） |
| IP_TRACE_IP_PORT_SCAN_PORT_LIST | config/port_scan/top1000.txt | 端口列表文件路径 |
| IP_TRACE_IP_PORT_SCAN_CONCURRENCY | 1 | 端口扫描并发数 |

## IP域名反查流水线渠道配置

控制 IP 域名反查流水线各采集渠道的启用/禁用（默认全部启用）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| IP_IP_DOMAIN_LOOKUP_RDNS_PTR_ENABLED | true | 启用 RDNS PTR 反向解析 |
| IP_IP_DOMAIN_LOOKUP_AIZHAN_ENABLED | true | 启用爱站网 IP 反查域名 |
| IP_IP_DOMAIN_LOOKUP_CHINAZ_ENABLED | true | 启用站长之家 IP 反查域名 |
| IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED | true | 启用 ZoomEye 网络空间测绘 |
| IP_IP_DOMAIN_LOOKUP_FOFA_SEARCH_ENABLED | true | 启用 Fofa 搜索查询 |
| IP_IP_DOMAIN_LOOKUP_SSL_CERT_ENABLED | true | 启用 SSL 证书域名提取 |

## 输出文件配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| IP_STORAGE_DIR | 空 | channel/batch 数据存储子目录（相对于 data/） |
| IP_STORAGE_NAME | ip_data | 存储名称（文件命名前缀） |
| IP_IP_DOMAIN_LOOKUP_PROJECT_NAME | temp | ip_domain_lookup 场景项目名 |
| IP_TRACE_IP_PROJECT_NAME | temp | trace_ip 场景项目名 |

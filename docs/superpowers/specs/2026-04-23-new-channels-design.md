# 新增渠道设计（Plan 2：Fofa IP 查询 / ZoomEye / SSL 证书）

> 本文档为 Plan 2，记录三个新渠道的设计方案。
> 各渠道独立实现后，逐一集成到 `ip_domain_lookup` 场景的 Phase 1 域名收集阶段。
> 当前状态：**待实现**

## 渠道总览

| 渠道 | 文件 | 配置项 | 域名提取方式 | 优先级 |
|------|------|--------|------------|--------|
| Fofa IP 查询 | `channel/fofa_ip.py` | `IP_FOFA_API_KEY`（复用） | 查询 `ip="x.x.x.x"` 提取 host 字段 | 高（已有 Key） |
| ZoomEye | `channel/zoomeye.py` | `IP_ZOOMEYE_API_KEY` | 查询 `ip:x.x.x.x` 提取域名/证书 | 中（有额度限制） |
| SSL 证书 | `channel/ssl_cert.py` | 无 | 连接 443 端口提取证书 SAN 域名 | 中 |

---

## 1. Fofa IP 查询渠道

### 背景

现有 `channel/fofa.py` 仅实现 Host 聚合查询（返回某个 host 的关联 IP 列表），缺少按 IP 查询关联域名/服务的接口。

### 实现方案

新建 `channel/fofa_ip.py`，遵循 `channel/_template.py` 的统一接口规范。

**查询语句**：`ip="x.x.x.x"`

**API 调用**：
```
GET https://fofa.info/api/v1/search/all
    ?email={email}&key={key}&qbase64={base64(query)}&fields=host,protocol,port,title&size=100
```

**响应解析**：
- `results` 数组中每条记录的 `host` 字段提取域名（去除协议和端口）
- 去重后返回域名列表

**输出格式**（写入 JSON 的 `fofa_ip` 字段）：
```json
{
  "fofa_ip": {
    "success": true,
    "ip": "1.2.3.4",
    "query": "ip=\"1.2.3.4\"",
    "total_results": 15,
    "domains": [
      {"domain": "example.com", "port": 443, "protocol": "https"},
      {"domain": "api.example.com", "port": 8080, "protocol": "http"}
    ],
    "domain_count": 2,
    "query_time": "2026-04-23T10:00:00"
  }
}
```

**配置**：复用 `FofaSettings`（`IP_FOFA_API_KEY`、`IP_FOFA_QUERY_DELAY`），无需新增配置项。

**批量脚本**：新建 `scripts/batch_fofa_ip.py`，遵循 `scripts/_template.py` 规范。

---

## 2. ZoomEye 渠道

### 背景

ZoomEye 是另一个网络空间测绘平台，可通过 API 按 IP 查询关联的域名、服务、证书信息。用户已有 API Key，但有额度限制，因此作为可选渠道。

### 实现方案

新建 `channel/zoomeye.py`，遵循 `channel/_template.py` 的统一接口规范。

**查询语句**：`ip:x.x.x.x`

**API 调用**：
```
GET https://api.zoomeye.org/host/search
    ?query=ip:x.x.x.x&facet=app,os&count=20
Authorization: JWT {api_key}
```

**响应解析**：
- `matches` 数组中每条记录提取：
  - `domain` 字段（如果有）
  - `websight.ssl.cert.subject.cn`（证书中的域名）
  - `websight.ssl.cert.extensions.subjectAltName`（SAN 中的域名）
- 去重后返回域名列表

**输出格式**（写入 JSON 的 `zoomeye` 字段）：
```json
{
  "zoomeye": {
    "success": true,
    "ip": "1.2.3.4",
    "query": "ip:1.2.3.4",
    "total_results": 8,
    "domains": [
      {"domain": "example.com", "source": "domain_field"},
      {"domain": "ssl.example.com", "source": "ssl_cert_cn"},
      {"domain": "wildcard.example.com", "source": "ssl_cert_san"}
    ],
    "domain_count": 3,
    "query_time": "2026-04-23T10:00:00"
  }
}
```

**配置**（新增到 `config.py`）：
```python
class ZoomeyeSettings(BaseSettings):
    zoomeye_api_key: str = Field(default='')
    zoomeye_query_delay: float = Field(default=1.0)

    class Config:
        env_prefix = 'IP_'
        env_file = ENV_FILE
```

环境变量：`IP_ZOOMEYE_API_KEY`、`IP_ZOOMEYE_QUERY_DELAY`

**批量脚本**：新建 `scripts/batch_zoomeye.py`。

**额度注意事项**：
- ZoomEye 免费账号有每日/每月查询额度限制
- CLI 入口增加 `--skip-zoomeye` 选项，允许跳过该渠道
- 查询前检查 Key 是否为空，空则自动跳过并记录日志

---

## 3. SSL 证书域名提取渠道

### 背景

许多 HTTPS 服务的 SSL/TLS 证书中包含域名信息（Subject CN 和 SAN），可以直接提取而无需依赖第三方平台。适合作为补充域名来源。

### 实现方案

新建 `channel/ssl_cert.py`，遵循 `channel/_template.py` 的统一接口规范。

**提取逻辑**：
1. 尝试连接 IP 的 443 端口，获取 SSL 证书
2. 解析证书的 `subject` 字段提取 Common Name (CN)
3. 解析证书的 `subjectAltName` 扩展提取所有 DNS 名称
4. 过滤掉通配符域名（`*.example.com`）和 IP 地址类型的值

**实现细节**：
```python
import ssl
import socket

def _get_ssl_cert(ip, port=443, timeout=5):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((ip, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=ip) as ssock:
            return ssock.getpeercert(binary_form=False)
```

**输出格式**（写入 JSON 的 `ssl_cert` 字段）：
```json
{
  "ssl_cert": {
    "success": true,
    "ip": "1.2.3.4",
    "port": 443,
    "subject_cn": "example.com",
    "san_domains": ["example.com", "www.example.com", "api.example.com"],
    "domains": [
      {"domain": "example.com", "source": "subject_cn"},
      {"domain": "www.example.com", "source": "san"},
      {"domain": "api.example.com", "source": "san"}
    ],
    "domain_count": 3,
    "query_time": "2026-04-23T10:00:00"
  }
}
```

**错误场景**：
- 连接超时 / 拒绝连接：`success: false`，标记 `error: "connection_failed"`
- 无 SSL 证书：`success: false`，标记 `error: "no_cert"`
- 证书解析失败：`success: false`，标记 `error: "cert_parse_failed"`

**配置**（新增到 `config.py`）：
```python
class SslCertSettings(BaseSettings):
    ssl_cert_timeout: float = Field(default=5.0)
    ssl_cert_port: int = Field(default=443)

    class Config:
        env_prefix = 'IP_'
        env_file = ENV_FILE
```

**批量脚本**：新建 `scripts/batch_ssl_cert.py`。

---

## 集成到 ip_domain_lookup 场景

各渠道实现并测试通过后，在 `scenarios/ip_domain_lookup/pipeline.py` 的 Phase 1 中加入：

```python
# Phase 1 域名收集渠道列表（逐步扩展）
channel_specs = [
    ('rdns_ptr', fetch_rdns_ptr, {...}),
    ('aizhan', fetch_aizhan, {...}),
    ('chinaz', fetch_chinaz, {...}),
    # 以下渠道实现后取消注释
    # ('fofa_ip', fetch_fofa_ip, {...}),
    # ('zoomeye', fetch_zoomeye, {...}),
    # ('ssl_cert', fetch_ssl_cert, {...}),
]
```

每个渠道独立开发、独立测试，实现一个验证一个，确认无误后取消注释加入流水线。

## 实施顺序建议

1. **Fofa IP 查询** — 优先级最高，已有 Key 和现有 Fofa 渠道可参考
2. **SSL 证书** — 无需外部 API，纯本地实现，风险最低
3. **ZoomEye** — 需注意额度限制，最后实现

每个渠道的开发流程：
1. 实现 `channel/xxx.py`（遵循 `_template.py`）
2. 实现 `scripts/batch_xxx.py`（遵循 `_template.py`）
3. 单渠道测试验证
4. 集成到 `ip_domain_lookup` Phase 1
5. 全流程测试

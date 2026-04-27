# 初始化与快速上手指南

当用户首次使用本项目、在新环境部署、或需要从头搭建工作环境时，按此文档执行初始化。

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | >= 3.10 |
| 操作系统 | Windows / Linux / macOS |
| 网络 | 需要访问外部 API（Fofa、IPInfo、ZoomEye 等） |

## 第一步：获取项目代码

```bash
git clone https://github.com/songmoshangchen/ip_info_manager.git
cd ip_info_manager
```

## 第二步：安装依赖

### 核心依赖（必装）

```bash
pip install -r requirements.txt
```

核心依赖包含：

| 包名 | 用途 |
|------|------|
| pydantic-settings>=2.0.0 | 配置管理（.env 读取） |
| ipinfo>=5.0.0 | IPInfo SDK |
| beautifulsoup4>=4.12.0 | HTML 解析（爱站/站长之家） |
| requests>=2.28.0 | HTTP 请求 |

### 可选依赖（按需安装）

| 包名 | 安装命令 | 用途 |
|------|---------|------|
| openpyxl | `pip install openpyxl` | Excel 导出功能 |
| python-docx>=1.0.0 | `pip install python-docx` | Word 报告自动生成（未安装时流水线跳过报告阶段） |
| python-whois | `pip install python-whois` | Whois 查询渠道 |

一次性全部安装可选依赖：

```bash
pip install openpyxl python-docx python-whois
```

## 第三步：创建配置文件

```bash
cp .env.example .env
```

## 第四步：配置 API 凭证

**所有配置变更必须通过 `tools/config_tool.py` 执行，不要直接编辑 `.env` 文件。**

### 查看当前配置状态

```bash
python tools/config_tool.py status
python tools/config_tool.py check
```

### 凭证配置

根据实际使用的渠道，配置对应的 API Key / Cookie：

| 渠道 | 配置变量 | 必填 | 获取方式 |
|------|---------|------|---------|
| Fofa | `IP_FOFA_API_KEY` | 使用 Fofa 时必填 | 登录 [fofa.info](https://fofa.info) → 个人中心 → API Key |
| IPInfo | `IP_IPINFO_ACCESS_TOKEN` | API 模式时必填 | 登录 [ipinfo.io](https://ipinfo.io) → Token 管理 |
| 爱站 | `IP_AIZHAN_COOKIE` | 使用爱站时必填 | 浏览器登录 [dns.aizhan.com](https://dns.aizhan.com) → F12 → 复制 Cookie |
| 站长之家 | `IP_CHINAZ_COOKIE` | 否（有 Cookie 可查更多信息） | 浏览器登录 [ipchaxun.com](https://ipchaxun.com) → F12 → 复制 Cookie |
| ZoomEye | `IP_ZOOMEYE_API_KEY` | 使用 ZoomEye 时必填 | 登录 [zoomeye.org](https://zoomeye.org) → 个人中心 → API Key |

**配置示例：**

```bash
python tools/config_tool.py set IP_FOFA_API_KEY "你的Fofa Key"
python tools/config_tool.py set IP_IPINFO_ACCESS_TOKEN "你的IPInfo Token"
python tools/config_tool.py set IP_AIZHAN_COOKIE "你的爱站Cookie"
python tools/config_tool.py set IP_ZOOMEYE_API_KEY "你的ZoomEye Key"
```

### 无需凭证即可使用的渠道

以下渠道无需任何 API Key，开箱即用：

| 渠道 | 说明 |
|------|------|
| RDNS PTR | DNS 反向解析，使用系统本地查询 |
| SSL 证书 | 直连目标 IP 提取证书，无需外部 API |
| IPInfo（免 API 模式） | 返回基础地理信息，无需 Token |

## 第五步：配置数据存储路径

默认即可使用。如需自定义：

```bash
python tools/config_tool.py set IP_STORAGE_DIR "202604"
python tools/config_tool.py set IP_STORAGE_NAME "ip_data"
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `IP_STORAGE_DIR` | 空 | channel/batch 数据存储子目录（相对于 data/） |
| `IP_STORAGE_NAME` | `ip_data` | 存储名称（文件命名前缀） |
| `IP_TRACE_IP_PROJECT_NAME` | `temp` | 溯源IP流水线项目名 |
| `IP_IP_DOMAIN_LOOKUP_PROJECT_NAME` | `temp` | IP域名反查流水线项目名 |

## 第六步：验证安装

### 1. 验证配置加载

```bash
python tools/config_tool.py list
```

应输出所有配置项及当前值。

### 2. 单 IP 查询测试

```bash
python channel/rdns_ptr.py 8.8.8.8
python channel/ipinfo_api.py 8.8.8.8
python channel/ssl_cert.py 1.1.1.1
```

以上三个渠道无需任何凭证即可测试。

### 3. 读取数据验证

```bash
python reader.py get 8.8.8.8
python reader.py list
```

### 4. 查看数据文件

数据默认存储在 `data/` 目录下：

```
data/
├── ip_data.json          # 主数据文件
└── logs/                 # 日志目录
```

## 快速上手流程

安装完成后，可按以下路径逐步使用：

1. **单 IP 查询** → 读取 [references/channel-query.md](channel-query.md)
2. **批量查询** → 读取 [references/batch-query.md](batch-query.md)
3. **数据管理（查看/导出）** → 读取 [references/data-management.md](data-management.md)
4. **溯源IP流水线** → 读取 [references/trace-ip-pipeline.md](trace-ip-pipeline.md)
5. **IP域名反查流水线** → 读取 [references/ip-domain-lookup-pipeline.md](ip-domain-lookup-pipeline.md)

## 常见问题

### pip install 报错

确认 Python 版本 >= 3.10：

```bash
python --version
```

### 配置不生效

确认 `.env` 文件存在于项目根目录，且配置项以 `IP_` 为前缀：

```bash
python tools/config_tool.py check
```

### API Key 校验失败

- Fofa：确认 Key 有效且未过期，登录 [fofa.info](https://fofa.info) 检查
- IPInfo：确认 Token 有效，登录 [ipinfo.io](https://ipinfo.io) 检查
- 爱站/站长之家：Cookie 有效期较短，需定期更新

更多问题排查请参阅 [references/troubleshooting.md](troubleshooting.md)。

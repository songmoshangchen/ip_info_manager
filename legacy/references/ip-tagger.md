# IP 标签打标工具

当用户需要为 IP 批量打标签（威胁情报匹配）时读取此文件。基于本地 `.ipset`/`.netset` 配置文件进行匹配，纯本地计算，无网络请求。

## 决策树

```
用户需要给一批 IP 打威胁情报标签 → ip_tagger.py
用户需要查看/编辑标签配置清单 → 编辑 config/ip_tagger/manifest.json
用户需要更新标签源文件 → python tools/ip_tagger_updater.py --from-git
用户需要从离线包导入 → python tools/ip_tagger_updater.py --from-archive ./blocklist-ipsets-master.zip
用户需要新增自定义标签源 → 添加文件到 config/ip_tagger/ + 更新 manifest.json
```

## 核心用法（ip_tagger.py）

### 基本用法

```bash
python tools/ip_tagger.py data/ips.txt
```

输入为 IP 文本文件（每行一个 IP），输出只写入命中标签的 IP 到 JSON 数据文件。

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `ip_file` | 是 | — | IP 文件路径（每行一个 IP） |
| `--mode` | 否 | `accumulate` | 写入模式：`accumulate`（累加）或 `overwrite`（覆盖） |
| `--level` | 否 | 全部 | 标签级别：`1`（快速21源）、`2`（正常31源）、`3`（全量35源） |
| `--output` | 否 | Settings 定位 | 输出 JSON 文件路径 |
| `--config-dir` | 否 | `config/ip_tagger` | 标签配置文件目录 |
| `--manifest` | 否 | `{config-dir}/manifest.json` | 清单文件路径 |

### 标签级别

| 级别 | 标签源数 | 耗时参考 | 说明 |
|---|---|---|---|
| `--level 1`（快速） | 21 | ~1s | 核心威胁：银狐、C&C、Tor、SSH、Bot、高危/中危/低危威胁、各类攻击 |
| `--level 2`（正常） | 31 | ~2s | + Spamhaus、ET Spamhaus、GreenSnow、PHP系列、乌克兰Blocklist、Spam30天、Artillery威胁 |
| `--level 3`（全量） | 35 | ~15s | + AbuseIPDB（74万+16万条）、垃圾Spam日报、匿名IP全量（190万条） |
| 不指定 | 35 | ~15s | 使用全部标签源 |

### 使用示例

```bash
# 默认累加模式（使用 Settings 定位 JSON 文件）
python tools/ip_tagger.py data/ips.txt

# 快速模式（21 个标签源，~1s）
python tools/ip_tagger.py data/ips.txt --level 1

# 正常模式（31 个标签源，~2s）
python tools/ip_tagger.py data/ips.txt --level 2

# 全量模式（35 个标签源，最全面）
python tools/ip_tagger.py data/ips.txt --level 3

# 覆盖模式（清空已有标签重写）
python tools/ip_tagger.py data/ips.txt --mode overwrite

# 指定输出 JSON 文件
python tools/ip_tagger.py data/ips.txt --output data/202604/202604_ip_data.json
```

### 写入模式

- **accumulate**（累加，默认）：将新标签合并到已有 `tags` 字段，按标签名去重
- **overwrite**（覆盖）：清空已有 `tags` 字段后重新写入

### 写入的 JSON 数据格式（tags 渠道）

只写入命中标签的 IP，未命中的不写入。格式为标签名列表：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "tags": ["银狐", "高危威胁", "SSH暴力破解"]
  }
}
```

### 月度更新提醒

ip_tagger 运行时会检查 `config/ip_tagger/.last_update` 标记文件。如果当前月份与标记不一致，会提醒用户更新标签源。updater 成功更新后自动写入标记。

### 场景集成（公共接口）

可在流水线或其他脚本中直接调用：

```python
from tools.ip_tagger import run_tagger
run_tagger('data/ips.txt', mode='accumulate')
run_tagger('data/ips.txt', mode='accumulate', output='data/202604/202604_ip_data.json')
run_tagger('data/ips.txt', level=1)
```

## 标签源更新（ip_tagger_updater.py）

从 [FireHOL blocklist-ipsets](https://github.com/firehol/blocklist-ipsets) 更新标签源文件，支持三种导入方式。

### 基本用法

```bash
# 方式1：git clone 整个仓库（推荐，稳定）
python tools/ip_tagger_updater.py --from-git

# 方式2：从本地 ZIP 压缩包导入（离线环境）
python tools/ip_tagger_updater.py --from-archive ./blocklist-ipsets-master.zip

# 方式3：从 GitHub 逐文件下载
python tools/ip_tagger_updater.py

# 仅检查更新，不实际下载
python tools/ip_tagger_updater.py --dry-run

# 强制更新所有文件（跳过缓存检查）
python tools/ip_tagger_updater.py --force
```

### 更新策略

- **git clone / ZIP 导入**：从仓库中复制 manifest 指定的文件，大小相同则跳过
- **GitHub 逐文件**：HEAD 请求检查远程 `Content-Length`，大小相同则跳过
- `source_url` 为空的条目不自动更新（自定义维护）
- 内置 3 次重试机制，应对 GitHub 连接不稳定
- 更新成功后自动写入 `.last_update` 月度标记

### 建议更新频率

**每月更新一次**（建议每月1号后执行）。ip_tagger 运行时会在过月后提醒。

## 标签配置管理

### 配置目录结构

```
config/ip_tagger/
├── manifest.json                # 标签清单（文件 → 标签名映射 + 下载源 + 级别）
├── .last_update                 # 月度更新标记（自动生成）
├── yinhu.ipset                  # 银狐木马（自定义维护）
├── feodo_badips.ipset           # 僵尸网络 C&C
├── cybercrime.ipset             # 综合犯罪 IP
├── firehol_level1.netset        # 高危威胁
├── firehol_level2.netset        # 中危威胁
├── firehol_level3.netset        # 低危威胁
├── blocklist_de.ipset           # Blocklist 攻击 IP
├── blocklist_de_ssh.ipset       # SSH 暴力破解
├── blocklist_de_bruteforce.ipset # 暴力破解
├── blocklist_de_mail.ipset      # 邮件攻击
├── blocklist_de_apache.ipset    # Apache 攻击
├── blocklist_de_bots.ipset      # 恶意 Bot
├── blocklist_de_imap.ipset      # IMAP 攻击
├── blocklist_de_ftp.ipset       # FTP 攻击
├── blocklist_de_sip.ipset       # SIP 攻击
├── blocklist_de_strongips.ipset # 持续性攻击 IP
├── tor_exits.ipset              # Tor 出口节点
├── botscout_1d.ipset            # 僵尸网络 Bot
├── ciarmy.ipset                 # CIArmy 恶意 IP
├── vxvault.ipset                # VXVault 恶意 URL
├── spamhaus_drop.netset         # Spamhaus DROP（Level 2）
├── spamhaus_edrop.netset        # Spamhaus EDROP（Level 2）
├── greensnow.ipset              # GreenSnow 攻击（Level 2）
├── php_*.ipset                  # PHP 系列攻击（Level 2）
├── blocklist_net_ua.ipset       # 乌克兰 Blocklist（Level 2）
├── stopforumspam_7d.ipset       # 垃圾 Spam 7天（Level 1）
├── stopforumspam_30d.ipset      # 垃圾 Spam 30天（Level 2）
├── bds_atif.ipset               # Artillery 威胁（Level 2）
├── abuseipdb_1d.ipset           # AbuseIPDB 日报（Level 3）
├── abuseipdb_30d.ipset          # AbuseIPDB 月报（Level 3）
└── firehol_anonymous.netset     # 匿名 IP 全量（Level 3）
```

### manifest.json 格式

```json
[
  {"file": "yinhu.ipset", "label": "银狐", "level": 1, "source_url": "", "note": "自定义维护"},
  {"file": "feodo_badips.ipset", "label": "僵尸网络C&C", "level": 1, "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/feodo_badips.ipset"},
  {"file": "spamhaus_drop.netset", "label": "Spamhaus DROP", "level": 2, "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/spamhaus_drop.netset"},
  {"file": "abuseipdb_1d.ipset", "label": "AbuseIPDB日报", "level": 3, "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/abuseipdb_1d.ipset"}
]
```

- `file`：相对于 config-dir 的文件名
- `label`：标签名称（支持中文），不可重复
- `level`：级别（1/2/3），ip_tagger 通过 `--level` 过滤
- `source_url`：下载源 URL（为空则不自动更新）
- `note`：可选备注

### 新增标签源

1. 将 `.ipset`/`.netset` 文件放入 `config/ip_tagger/`
2. 在 `manifest.json` 中添加条目（含 level、如需自动更新则填写 source_url）
3. 重新运行 `ip_tagger.py`

## 核心算法

统一 IPv4/IPv6 整数排序双指针扫描，O(n+m) 复杂度：

1. 输入 IP 列表转为整数并排序
2. 流式读取配置文件（每批 256 条排序）
3. 双指针对比已排序 IP 和已排序网段范围
4. 只收集命中结果，未命中的不写入

## 环境变量配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `IP_IP_TAGGER_CONFIG_DIR` | `config/ip_tagger` | 标签配置文件目录（⚠️ 实际无效） |

> ⚠️ **注意**：虽然 `config.py` 中 `IpTaggerSettings` 定义了 `ip_tagger_config_dir` 字段（在 `env_prefix='IP_'` 下映射为环境变量 `IP_IP_TAGGER_CONFIG_DIR`），但 `ip_tagger.py` 实际并不使用 `IpTaggerSettings`，而是通过 `--config-dir` 命令行参数硬编码默认值 `config/ip_tagger`。因此该环境变量实际无效，配置目录请通过 `--config-dir` 参数指定。

无需 API Key、超时、延迟等配置。

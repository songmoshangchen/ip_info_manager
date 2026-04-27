# IP 标签打标工具

当用户需要为 IP 批量打标签（威胁情报匹配）时读取此文件。基于本地 `.ipset`/`.netset` 配置文件进行匹配，纯本地计算，无网络请求。

## 决策树

```
用户需要给一批 IP 打威胁情报标签 → ip_tagger.py
用户需要查看/编辑标签配置清单 → 编辑 config/ip_tagger/manifest.json
用户需要更新标签源文件 → python tools/ip_tagger_updater.py
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
| `--level` | 否 | 全部 | 标签级别：`1`（快速5源）、`2`（正常13源）、`3`（全量23源） |
| `--output` | 否 | Settings 定位 | 输出 JSON 文件路径 |
| `--config-dir` | 否 | `config/ip_tagger` | 标签配置文件目录 |
| `--manifest` | 否 | `{config-dir}/manifest.json` | 清单文件路径 |

### 使用示例

```bash
# 默认累加模式（使用 Settings 定位 JSON 文件）
python tools/ip_tagger.py data/ips.txt

# 快速模式（仅 5 个核心标签源，最快）
python tools/ip_tagger.py data/ips.txt --level 1

# 正常模式（13 个标签源，平衡速度与覆盖面）
python tools/ip_tagger.py data/ips.txt --level 2

# 全量模式（23 个标签源，最全面）
python tools/ip_tagger.py data/ips.txt --level 3

# 覆盖模式（清空已有标签重写）
python tools/ip_tagger.py data/ips.txt --mode overwrite

# 指定输出 JSON 文件
python tools/ip_tagger.py data/ips.txt --output data/202604/202604_ip_data.json

# 指定配置目录
python tools/ip_tagger.py data/ips.txt --config-dir config/ip_tagger
```

### 写入模式

- **accumulate**（累加，默认）：将新标签合并到已有 `tags` 字段，按标签名去重
- **overwrite**（覆盖）：清空已有 `tags` 字段后重新写入

### 写入的 JSON 数据格式（tags 渠道）

只写入命中标签的 IP，未命中的不写入：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "tags": {
      "labels": ["银狐", "高危威胁"],
      "details": [
        {"label": "银狐", "source": "yinhu.ipset"},
        {"label": "高危威胁", "source": "firehol_level1.netset"}
      ],
      "query_time": "2026-04-27T10:00:00"
    }
  }
}
```

### 场景集成（公共接口）

可在流水线或其他脚本中直接调用：

```python
from tools.ip_tagger import run_tagger
run_tagger('data/ips.txt', mode='accumulate')
run_tagger('data/ips.txt', mode='accumulate', output='data/202604/202604_ip_data.json')
```

## 标签源更新（ip_tagger_updater.py）

从 [FireHOL blocklist-ipsets](https://github.com/firehol/blocklist-ipsets) 自动下载更新标签源文件。

### 基本用法

```bash
# 方式1：从 GitHub 逐文件下载（默认）
python tools/ip_tagger_updater.py

# 方式2：git clone 整个仓库（推荐，稳定）
python tools/ip_tagger_updater.py --from-git

# 方式3：从本地 ZIP 压缩包导入（离线环境）
python tools/ip_tagger_updater.py --from-archive ./blocklist-ipsets-main.zip

# 仅检查更新，不实际下载
python tools/ip_tagger_updater.py --dry-run

# 强制更新所有文件（跳过缓存检查）
python tools/ip_tagger_updater.py --force
```

### 更新策略

- 通过 HEAD 请求检查远程文件 `Content-Length`，与本地文件大小对比
- 大小相同则跳过（已是最新）
- 大小不同则下载覆盖
- `source_url` 为空的条目不自动更新（自定义维护）
- 内置 3 次重试机制，应对 GitHub 连接不稳定

### 建议更新频率

| 标签源 | 建议更新频率 | 说明 |
|---|---|---|
| blocklist_de 系列 | 每天或每周 | 48小时攻击数据，变化快 |
| firehol_level1 | 每周 | 聚合列表，相对稳定 |
| feodo/cybercrime | 每周 | 恶意软件 C&C，变化中等 |
| tor_exits | 每周 | Tor 出口节点列表 |
| stopforumspam_7d | 每周 | 7天 spam 数据 |

## 标签配置管理

### 配置目录结构

```
config/ip_tagger/
├── manifest.json                # 标签清单（文件 → 标签名映射 + 下载源）
├── yinhu.ipset                  # 银狐木马（自定义维护）
├── feodo_badips.ipset           # 僵尸网络 C&C（FireHOL）
├── cybercrime.ipset             # 综合犯罪 IP（FireHOL）
├── firehol_level1.netset        # 高危威胁（FireHOL）
├── blocklist_de.ipset           # Blocklist 攻击 IP（FireHOL）
├── blocklist_de_ssh.ipset       # SSH 暴力破解（FireHOL）
├── tor_exits.ipset              # Tor 出口节点（FireHOL）
└── stopforumspam_7d.ipset       # 垃圾论坛 Spam（FireHOL）
```

### manifest.json 格式

```json
[
  {"file": "yinhu.ipset", "label": "银狐", "source_url": "", "note": "自定义维护"},
  {"file": "feodo_badips.ipset", "label": "僵尸网络C&C", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/feodo_badips.ipset"},
  {"file": "cybercrime.ipset", "label": "综合犯罪IP", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/cybercrime.ipset"},
  {"file": "firehol_level1.netset", "label": "高危威胁", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"},
  {"file": "blocklist_de.ipset", "label": "Blocklist攻击IP", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/blocklist_de.ipset"},
  {"file": "blocklist_de_ssh.ipset", "label": "SSH暴力破解", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/blocklist_de_ssh.ipset"},
  {"file": "tor_exits.ipset", "label": "Tor出口节点", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/tor_exits.ipset"},
  {"file": "stopforumspam_7d.ipset", "label": "垃圾论坛Spam", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/stopforumspam_7d.ipset"}
]
```

- `file`：相对于 config-dir 的文件名
- `label`：标签名称（支持中文），不可重复
- `source_url`：下载源 URL（为空则不自动更新）
- `note`：可选备注

### 配置文件格式（.ipset / .netset）

- 每行一个 IP 地址或 CIDR 网段
- `#` 开头的行为注释（跳过）
- 空行跳过
- 支持 IPv4 和 IPv6

```
# 这是注释
1.2.3.4
10.0.0.0/8
2001:db8::/32
```

### 新增标签源

1. 将 `.ipset`/`.netset` 文件放入 `config/ip_tagger/`
2. 在 `manifest.json` 中添加条目（如需自动更新则填写 `source_url`）
3. 重新运行 `ip_tagger.py`

### 新增 FireHOL 标签源

如需从 FireHOL 仓库新增标签源：

1. 在 [FireHOL blocklist-ipsets](https://github.com/firehol/blocklist-ipsets/tree/master) 找到目标文件
2. 在 `manifest.json` 中添加：`{"file": "文件名.ipset", "label": "标签名", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/文件名.ipset"}`
3. 运行 `python tools/ip_tagger_updater.py` 下载

## 核心算法

统一 IPv4/IPv6 整数排序双指针扫描，O(n+m) 复杂度：

1. 输入 IP 列表转为整数并排序
2. 流式读取配置文件（每批 256 条排序）
3. 双指针对比已排序 IP 和已排序网段范围
4. 只收集命中结果，未命中的不写入

## 环境变量配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `IP_TAGGER_CONFIG_DIR` | `config/ip_tagger` | 标签配置文件目录 |

无需 API Key、超时、延迟等配置。

# IP 标签源自动更新脚本 — 实现计划

## 背景

当前 `config/ip_tagger/` 下的标签源文件需要手动从 GitHub 更新。需要编写自动更新脚本，从 [firehol/blocklist-ipsets](https://github.com/firehol/blocklist-ipsets/tree/master) 下载最新的 `.ipset`/`.netset` 文件。

## FireHOL 仓库分析

### 下载 URL 格式

Raw 文件下载地址：
```
https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/{filename}
```

例如：
- `https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/feodo_badips.ipset`
- `https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_anonymous.netset`

### 当前使用的文件（7 个）

| 文件名 | 标签 | 类别 | 状态 |
|---|---|---|---|
| `yinhu.ipset` | 银狐 | 自定义 | ❗ **不在 FireHOL 仓库**，从微步获取的部分数据，需单独维护 |
| `feodo_badips.ipset` | 僵尸网络C&C | malware | ✅ 可从 FireHOL 更新 |
| `iblocklist_abuse_zeus.netset` | Zeus银行木马 | malware | ⚠️ 已停止更新（2018年） |
| `iblocklist_abuse_spyeye.netset` | SpyEye银行木马 | malware | ⚠️ 已停止更新 |
| `iblocklist_abuse_palevo.netset` | Palevo蠕虫 | malware | ⚠️ 已停止更新 |
| `cybercrime.ipset` | 综合犯罪IP | malware | ✅ 可从 FireHOL 更新 |
| `firehol_anonymous.netset` | 匿名IP | anonymizers | ✅ 可从 FireHOL 更新（26MB/190万条） |

### 建议新增的高价值标签源

从 FireHOL 仓库中筛选，按实用性排序：

| 文件名 | 建议标签 | 类别 | 条目数 | 理由 |
|---|---|---|---|---|
| `firehol_level1.netset` | 高危威胁 | attacks | ~6000 | FireHOL 精选一级威胁（含多个子列表聚合） |
| `blocklist_de.ipset` | Blocklist攻击IP | attacks | ~21000 | 48小时内被 fail2ban 检测的攻击 IP |
| `blocklist_de_ssh.ipset` | SSH暴力破解 | attacks | ~4700 | SSH 攻击 IP |
| `blocklist_de_bruteforce.ipset` | 暴力破解 | attacks | ~1200 | WordPress/Joomla 等暴力破解 |
| `stopforumspam_7d.ipset` | 垃圾论坛spam | abuse | ~30000 | 7天内垃圾发帖 IP |
| `tor_exits.ipset` | Tor出口节点 | anonymizers | ~1000 | Tor 网络出口节点 |
| `botscout_1d.ipset` | 僵尸网络 | abuse | ~350 | 近1天捕获的 bot |

**不建议新增**：
- `firehol_anonymous.netset` — 已有，但 190万条太重，考虑替换为 `tor_exits.ipset`（更精准）
- `abuseipdb_*` — 需要付费 API
- `bogons` — RFC1918 私有地址，无实际价值

### 建议移除的过时文件

- `iblocklist_abuse_zeus.netset` — 最后更新 2018年，已过时
- `iblocklist_abuse_spyeye.netset` — 已过时
- `iblocklist_abuse_palevo.netset` — 已过时

## 实现计划

### 步骤 1：扩展 manifest.json 格式

为每个条目新增可选字段 `source_url` 和 `update_freq`：

```json
[
  {"file": "yinhu.ipset", "label": "银狐", "source_url": "", "note": "自定义维护"},
  {"file": "feodo_badips.ipset", "label": "僵尸网络C&C", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/feodo_badips.ipset"},
  {"file": "firehol_level1.netset", "label": "高危威胁", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"},
  ...
]
```

- `source_url` 为空 → 不自动更新（自定义文件）
- `source_url` 有值 → 脚本下载更新

### 步骤 2：编写 `tools/ip_tagger_updater.py`

**脚本定位**：`tools/` 下的独立工具，职责是更新配置文件。

**CLI 接口**：
```bash
python tools/ip_tagger_updater.py                    # 更新所有有 source_url 的文件
python tools/ip_tagger_updater.py --dry-run          # 仅检查，不下载
python tools/ip_tagger_updater.py --force            # 强制更新（跳过缓存检查）
python tools/ip_tagger_updater.py --config-dir config/ip_tagger  # 指定配置目录
```

**核心流程**：
1. 读取 `manifest.json`
2. 遍历每个有 `source_url` 的条目
3. HEAD 请求检查 `Content-Length` / `Last-Modified`，与本地文件对比
4. 如有更新 → 下载覆盖本地文件
5. 输出更新摘要（哪些更新了、哪些跳过、哪些失败）

**缓存策略**：
- 比较远程 `Content-Length` 与本地文件大小
- 如果相同则跳过下载
- `--force` 时忽略缓存强制下载

**超时与限速**：
- 单个文件下载超时 60 秒
- 文件间间隔 1 秒（避免触发 GitHub 限流）

### 步骤 3：更新 manifest.json

移除过时的 iblocklist 条目，新增高价值标签源：

最终建议清单：

| 文件 | 标签 | 来源 |
|---|---|---|
| `yinhu.ipset` | 银狐 | 自定义（不自动更新） |
| `feodo_badips.ipset` | 僵尸网络C&C | FireHOL |
| `cybercrime.ipset` | 综合犯罪IP | FireHOL |
| `firehol_level1.netset` | 高危威胁 | FireHOL（新增） |
| `blocklist_de.ipset` | Blocklist攻击IP | FireHOL（新增） |
| `blocklist_de_ssh.ipset` | SSH暴力破解 | FireHOL（新增） |
| `tor_exits.ipset` | Tor出口节点 | FireHOL（新增） |
| `stopforumspam_7d.ipset` | 垃圾论坛Spam | FireHOL（新增） |

移除：
- `iblocklist_abuse_zeus.netset` — 过时
- `iblocklist_abuse_spyeye.netset` — 过时
- `iblocklist_abuse_palevo.netset` — 过时
- `firehol_anonymous.netset` — 太重（190万条），用 `tor_exits` 替代

### 步骤 4：更新 references/ip-tagger.md

补充更新脚本的说明。

### 步骤 5：更新 README.md

在工具章节补充更新脚本的说明。

## 涉及的文件

| 操作 | 文件 |
|---|---|
| 新增 | `tools/ip_tagger_updater.py` |
| 修改 | `config/ip_tagger/manifest.json` |
| 新增 | `config/ip_tagger/firehol_level1.netset` 等新标签源文件 |
| 删除 | `config/ip_tagger/iblocklist_abuse_*.netset`（3个过时文件） |
| 删除 | `config/ip_tagger/firehol_anonymous.netset`（替换为 tor_exits） |
| 修改 | `references/ip-tagger.md` |
| 修改 | `README.md` |

## 注意事项

1. `yinhu.ipset` 是自定义文件，不在 FireHOL 仓库，不能自动更新
2. `firehol_anonymous.netset` 有 190万条（26MB），下载和处理都很慢，建议移除
3. GitHub raw 下载有频率限制，脚本需要合理间隔
4. 脚本不依赖 `ip_tagger.py` 的算法，仅负责下载更新配置文件

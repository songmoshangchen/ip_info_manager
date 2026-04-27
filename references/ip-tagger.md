# IP 标签打标工具

当用户需要为 IP 批量打标签（威胁情报匹配）时读取此文件。基于本地 `.ipset`/`.netset` 配置文件进行匹配，纯本地计算，无网络请求。

## 决策树

```
用户需要给一批 IP 打威胁情报标签 → ip_tagger.py
用户需要查看/编辑标签配置清单 → 编辑 config/ip_tagger/manifest.json
用户需要更新标签源文件 → 手动下载替换（后续将提供自动更新脚本）
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
| `--output` | 否 | Settings 定位 | 输出 JSON 文件路径 |
| `--config-dir` | 否 | `config/ip_tagger` | 标签配置文件目录 |
| `--manifest` | 否 | `{config-dir}/manifest.json` | 清单文件路径 |

### 使用示例

```bash
# 默认累加模式（使用 Settings 定位 JSON 文件）
python tools/ip_tagger.py data/ips.txt

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
      "labels": ["银狐", "僵尸网络C&C"],
      "details": [
        {"label": "银狐", "source": "yinhu.ipset"},
        {"label": "僵尸网络C&C", "source": "feodo_badips.ipset"}
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

## 标签配置管理

### 配置目录结构

```
config/ip_tagger/
├── manifest.json                # 标签清单（文件 → 标签名映射）
├── yinhu.ipset                  # 银狐木马 IP 列表
├── feodo_badips.ipset           # Feodo 僵尸网络 C&C
├── iblocklist_abuse_zeus.netset # Zeus 银行木马
├── iblocklist_abuse_spyeye.netset # SpyEye 银行木马
├── iblocklist_abuse_palevo.netset # Palevo 蠕虫
├── cybercrime.ipset             # 综合犯罪 IP
└── firehol_anonymous.netset     # 匿名 IP（Tor/VPN）
```

### manifest.json 格式

```json
[
  {"file": "yinhu.ipset", "label": "银狐"},
  {"file": "feodo_badips.ipset", "label": "僵尸网络C&C"},
  {"file": "iblocklist_abuse_zeus.netset", "label": "Zeus银行木马"},
  {"file": "iblocklist_abuse_spyeye.netset", "label": "SpyEye银行木马"},
  {"file": "iblocklist_abuse_palevo.netset", "label": "Palevo蠕虫"},
  {"file": "cybercrime.ipset", "label": "综合犯罪IP"},
  {"file": "firehol_anonymous.netset", "label": "匿名IP"}
]
```

- `file`：相对于 config-dir 的文件名
- `label`：标签名称（支持中文），不可重复

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
2. 在 `manifest.json` 中添加一行：`{"file": "新文件.ipset", "label": "标签名"}`
3. 重新运行 `ip_tagger.py`

### 标签源更新

标签源文件来自外部威胁情报项目（如 [FireHOL blocklist-ipsets](https://github.com/firehol/blocklist-ipsets)），需要定期更新。

**当前方式**：手动下载替换配置文件。

**计划中**：后续将提供自动更新脚本，从 GitHub 下载最新的标签源文件，并预处理为流式查询友好的格式。

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

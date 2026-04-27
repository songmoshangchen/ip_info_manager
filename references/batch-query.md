# 批量查询

当用户有一批 IP 文件需要批量查询某个渠道时读取此文件。

## 决策树

```
用户说"用 fofa 批量查一批 IP"
  → 确认存储目录/项目名是否需要切换
  → 确认凭证是否有效
  → 用 merge_ip_files.py 验证 IP 文件
  → 生成 batch 命令并执行

用户说"用 ipinfo 批量查一批 IP"
  → 额外确认：是否使用 API 模式（有 Key）还是免 API 模式（--no-api）
  → 其余同上
```

## 前置步骤

### 1. 确认存储配置

如果用户需要切换存储目录或项目名：

```bash
python tools/config_tool.py set IP_STORAGE_DIR "data/202604"
python tools/config_tool.py set IP_STORAGE_NAME "ip_data"
```

不确定当前配置时：

```bash
python tools/config_tool.py list
```

### 2. 验证 IP 文件

批量查询前务必先验证 IP 文件格式和去重：

```bash
python tools/merge_ip_files.py ips.txt
python tools/merge_ip_files.py ips.txt --show-invalid
```

多文件合并：

```bash
python tools/merge_ip_files.py file1.txt file2.txt file3.txt -o merged.txt
```

## 批量查询命令

所有命令在项目根目录 `ip_info_manager/` 下执行，`ips.txt` 为 IP 文件路径（每行一个 IP）。

| 渠道 | 命令 | 独有参数 |
|------|------|---------|
| Fofa Host 聚合 | `python scripts/batch_fofa_host.py ips.txt` | — |
| Fofa 搜索 | `python scripts/batch_fofa_search.py ips.txt` | — |
| IPInfo（API 模式） | `python scripts/batch_ipinfo_api.py ips.txt` | — |
| IPInfo（免 API 模式） | `python scripts/batch_ipinfo_api.py ips.txt --no-api` | `--no-api` |
| RDNS（单线程） | `python scripts/batch_rdns_ptr.py ips.txt` | — |
| RDNS（多线程） | `python scripts/batch_rdns_ptr_concurrent.py ips.txt --workers 20` | `--workers N` |
| Whois | `python scripts/batch_whois.py ips.txt` | — |
| 爱站 | `python scripts/batch_aizhan.py ips.txt` | — |
| 站长之家 | `python scripts/batch_chinaz.py ips.txt` | — |
| ZoomEye | `python scripts/batch_zoomeye.py ips.txt` | — |
| SSL 证书 | `python scripts/batch_ssl_cert.py ips.txt` | — |

所有批量脚本通用参数：
- `ip_file` — IP 文件路径（必填）
- `--no-validate` — 跳过凭证校验

## IPInfo 特殊处理

ipinfo_api 有两种模式，使用前需确认：

- **API 模式**（默认）：需要 `IP_IPINFO_ACCESS_TOKEN`，返回 ASN 等详细信息
- **免 API 模式**（`--no-api`）：无需 Token，返回基础地理信息

判断依据：用户是否有 Token、需要多详细的信息。

## 断点续查

批量脚本自动在数据文件同目录生成 `{storage_file}.{channel_name}.progress` 进度文件。

- 中断后重新运行同一命令，会自动跳过已处理的 IP
- 如需**全部**重新查询，删除对应的 `.progress` 文件
- 如需重新查询**特定** IP，用 `tools/progress_tool.py` 从进度文件中移除目标 IP
- 以上操作仅解除已处理标记（允许重新查询），不会直接触发查询，需重新运行批量命令才会生效

### 进度文件管理

```bash
python tools/progress_tool.py generate data/ip_data.json --channel fofa_host
python tools/progress_tool.py remove data/ip_data.fofa_host.progress 1.2.3.4 5.6.7.8
python tools/progress_tool.py remove data/ip_data.fofa_host.progress --from-file ips.txt
```

## 查询后导出

查询完成后可导出结果：

```bash
python reader.py list --include-channel fofa_host --export-excel output.xlsx
```

## 注意事项

- 批量查询前务必先验证 IP 文件（merge_ip_files.py）
- 爱站/站长之家查询间隔建议不低于 2 秒
- 日志存储在 `data/logs/{channel_name}.log`，遇到异常时查看日志
- 不确定参数时用 `python scripts/batch_<channel>.py --help`
- 遇到凭证失效、限频等异常时，读取 references/troubleshooting.md

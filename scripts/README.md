# 批量查询脚本

## 功能说明

本目录包含用于批量查询 IP 信息的脚本。

## batch_ipinfo_api.py

批量使用 ipinfo.io API 查询 IP 信息。

### 特性

- ✅ 每 1.1 秒查询一个 IP（可自定义间隔）
- ✅ 实时显示查询进度：当前序号/总数量 + IP 地址
- ✅ 显示查询结果：国家 - 组织
- ✅ 支持 Ctrl+C 中断，自动保存进度
- ✅ 下次运行自动从中断处继续
- ✅ 自动保存到数据库

### 使用方法

1. **准备 IP 文件**（一行一个 IP）：
```bash
# 创建 ips.txt 文件
8.8.8.8
8.8.4.4
1.1.1.1
```

2. **运行批量查询**：
```bash
# 默认间隔 1.1 秒
python batch_ipinfo_api.py ips.txt

# 自定义查询间隔（例如 2 秒）
python batch_ipinfo_api.py ips.txt 2.0
```

3. **中断和恢复**：
```bash
# 按 Ctrl+C 中断查询
# 查询已中断！
# 已处理: 3 个 IP
# 进度文件: ips.txt.progress
# 下次运行将从第 4 个 IP 开始

# 重新运行，自动跳过已处理的 IP
python batch_ipinfo_api.py ips.txt
```

### 输出示例

```
开始批量查询 IP 信息
IP 文件: test_ips.txt
总 IP 数: 5
已处理: 0
待处理: 5
------------------------------------------------------------
[1/5] 正在查询: 8.8.8.8 ✅ United States - Google LLC
[2/5] 正在查询: 8.8.4.4 ✅ United States - Google LLC
[3/5] 正在查询: 1.1.1.1 ✅ Australia - Cloudflare, Inc.
[4/5] 正在查询: 1.0.0.1 ✅ Australia - Cloudflare, Inc.
[5/5] 正在查询: 208.67.222.222 ✅ United States - Cisco OpenDNS, LLC

============================================================
批量查询完成！
总共处理: 5 个 IP
============================================================
```

### 进度文件

查询过程中会自动创建 `文件名.progress` 文件，记录已处理的 IP。

### 配置要求

确保 `.env` 文件包含必要的配置：
```bash
IP_STORAGE_DIR=你的存储目录
IP_STORAGE_FILENAME=你的存储文件名
IP_IPINFO_ACCESS_TOKEN=你的ipinfo_token
```

### 查询结果

所有查询结果自动保存到数据库，使用 `reader.py` 查看：
```bash
# 查看所有 IP
python ../reader.py list

# 查看指定 IP 的 ipinfo_api 渠道数据
python ../reader.py get-channel 8.8.8.8 ipinfo_api
```

## 注意事项

1. 查询间隔不要设置太短，避免触发 API 限制
2. IP 文件必须存在且格式正确（一行一个 IP）
3. 进度文件会自动创建和更新，无需手动管理
4. 如需重新查询所有 IP，删除 `.progress` 文件即可

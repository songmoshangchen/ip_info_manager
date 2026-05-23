# Tasks

- [x] Task 1: 安装 python-nmap 依赖
  - [x] SubTask 1.1: `pip install python-nmap` 并更新依赖文件

- [x] Task 2: 实现 PortScanChannel 类
  - [x] SubTask 2.1: 创建 `src/ip_info/channel/port_scan.py`
    - `channel_name = "port_scan"`
    - `__init__(self, nmap_path="nmap", timeout=30.0)`
    - `_validate_key()`: 通过 `nmap.PortScanner()` 初始化检查可用性
    - `_request(ip, **kwargs)`: 使用 `nm.scan()` 执行扫描，返回 PortScanner 对象
    - `_parse(raw, ip)`: 从 PortScanner 对象提取端口信息

- [x] Task 3: 编写单元测试 `tests/unit/channel/test_port_scan.py`（面向结果原则）
  - [x] SubTask 3.1: TestPortScanFetch — fetch 完整流程（面向结果，8 个测试）
  - [x] SubTask 3.2: TestPortScanProtocol — 协议合规（4 个测试）

# Task Dependencies

- Task 2 depends on Task 1
- Task 3 depends on Task 2

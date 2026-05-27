# Tasks

- [x] Task 1: 实现 SslCertChannel 类
  - [x] SubTask 1.1: 创建 `src/ip_info/channel/ssl_cert.py`，实现 `SslCertChannel` 类
    - `channel_name = "ssl_cert"`
    - `__init__(self, port=443, timeout=5.0, openssl_timeout=10.0)`
    - `_request(ip, **kwargs)`: SSL 直连获取证书文本，处理各类异常
    - `_parse(raw, ip)`: 解析证书文本提取 CN/SAN/Issuer/有效期
  - [x] SubTask 1.2: 实现辅助函数
    - `_get_ssl_cert_text(ip, port, timeout, openssl_timeout)`: SSL 连接 + 证书获取
    - `_cert_to_text(pem_text, openssl_timeout)`: openssl 解析 + 回退
    - `_parse_domains(cert_text)`: CN + SAN 域名提取去重
  - [x] SubTask 1.3: 端口传递机制
    - `_request` 从 kwargs 获取 port，存入实例属性供 `_parse` 使用

- [x] Task 2: 编写单元测试 `tests/unit/channel/test_ssl_cert.py`
  - [x] SubTask 2.1: TestSslCertRequest — _request 各种网络场景（7 个测试）
  - [x] SubTask 2.2: TestSslCertFetch — fetch 完整流程（7 个测试）
  - [x] SubTask 2.3: TestSslCertProtocol — 协议合规（4 个测试）

# Task Dependencies

- Task 2 depends on Task 1

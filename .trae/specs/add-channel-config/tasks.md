# Tasks

- [ ] Task 1: 创建渠道配置基类 + 各渠道配置类
  - [ ] SubTask 1.1: 创建 `src/ip_info/channel/config.py`，定义 `ChannelConfig` 基类（pydantic-settings）和 10 个渠道配置类
  - [ ] SubTask 1.2: 写测试 — .env 读取、环境变量覆盖、默认值、必填字段缺失抛 ValidationError
  - [ ] 验证: 配置类测试通过

- [ ] Task 2: BaseChannelAdapter 添加 default_delay 属性
  - [ ] SubTask 2.1: 在 `BaseChannelAdapter` 中添加 `default_delay: float = 0` 类属性
  - [ ] SubTask 2.2: 写测试 — 默认值为 0、子类覆盖
  - [ ] 验证: default_delay 测试通过

- [ ] Task 3: 修改各 ChannelAdapter 构造函数支持配置类
  - [ ] SubTask 3.1: 逐个修改 10 个 ChannelAdapter，添加 `config` 参数 + 显式参数覆盖逻辑
  - [ ] SubTask 3.2: 写测试 — 显式参数覆盖配置类、无显式参数从配置类读取、无配置类从 .env 读取
  - [ ] 验证: 各适配器配置测试通过

- [ ] Task 4: 集成验证
  - [ ] SubTask 4.1: 运行 `python -m pytest tests/unit/ -v` 确认全部测试通过
  - [ ] SubTask 4.2: 运行 `ruff check src/ tests/unit/` 确认无 lint 错误
  - [ ] 验证: 全量测试通过 + lint 通过

# Task Dependencies

- [Task 1] → [Task 3]（配置类先于适配器修改）
- [Task 2] → [Task 3]（default_delay 先于适配器修改）
- [Task 3] → [Task 4]（集成验证在所有修改完成后）

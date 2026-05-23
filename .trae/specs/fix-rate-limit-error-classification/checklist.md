# Checklist — 修复限流错误分类

## ipinfo_free
- [x] HTTP 429 抛出 ChannelError（非 ChannelPermanentError）
- [x] 对应测试验证 ChannelError + disabled 不变
- [x] 清理不再使用的 ChannelPermanentError import

## ipinfo_api
- [x] HTTP 429 抛出 ChannelError（非 ChannelPermanentError）
- [x] HTTP 401/403 仍为 ChannelPermanentError（不变）
- [x] 对应测试验证 ChannelError

## 代码质量
- [x] ruff format 通过
- [x] ruff check 通过
- [x] 全量 pytest 通过

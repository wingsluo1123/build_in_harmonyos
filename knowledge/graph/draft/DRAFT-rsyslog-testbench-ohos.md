# rsyslog testbench OHOS 迁移模式

**草稿编号**：DRAFT-rsyslog-testbench-ohos
**PR 参考**：!4708
**状态**：draft

## 适用场景

autotools 构建的服务类测试框架在 OHOS/musl/HMDFS 环境下的迁移。

## 核心方案

1. **E011 HMDFS umask 077**：configure mktemp 使用 `$TMPDIR` 绝对路径修复
2. **pthread_cancel 不可用**：25 处 `HAVE_PTHREAD_CANCEL` 条件编译
3. **musl stub**：`omusrmsg.c` 补 `endutxent`，`omfwd.c` 补 `__res_state`
4. **OHOS 无 /bin/bash**：测试脚本 shebang 需替换为 `/data/service/hnp/bin/bash`
5. **RSYSLOG_DYNNAME 环境冲突**：测试框架初始化前须 `unset RSYSLOG_DYNNAME`

## 跨库复用价值

rsyslog 测试框架结构（diag.sh + 1426 RainerScript/shell 用例）的 OHOS 适配诊断模式，可推广至同类 autotools 服务测试框架。

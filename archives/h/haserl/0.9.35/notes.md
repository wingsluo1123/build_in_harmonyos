# haserl 0.9.35 适配说明

## 适配概要
- 构建系统：autotools（上游 release tarball，自带 configure）
- 依赖：无（--without-lua 关闭可选的 Lua 嵌入支持，避免引入 lua 依赖）
- OHOS 适配处理（沿用仓库既有经验）：
  1. 老 config.guess/sub 不认识 HarmonyOS → configure 显式 --build/--host=aarch64-unknown-linux-gnu
  2. 鸿蒙 PC 拒绝执行未签名 ELF，configure try-run 探测 exec 失败 → 按原生构建语义 patch 为通过
  3. config.status umask 077 临时目录在 HMDFS 写入 EACCES → 放宽为 022
  4. in-source 构建：configure 与 make 均在源码目录执行；裸 make 避免 jobserver mkfifo 被 HMDFS 拒绝
- 产物：bin/haserl（已 OHOS 签名）

## 验证
- 本地 conan create（ci/conan/profiles/ohos-aarch64）：编译、安装、签名全部通过
- 上游无测试套件（tarball 无 tests 目录），消费者测试执行嵌入脚本验证功能

# libunibreak 8.0 适配笔记

任务 contrib-15048，用户账号 2501_91199785，功能分支 feat/libunibreak-8.0。已读取任务 API 的 assigned 所有权；远端提交前仍须回读活动与任务分支。

发布源码携带 2016 年 GNU config.guess/config.sub，不认识 HarmonyOS。配方只在 OHOS 下按其 echo/exit 格式加入 aarch64-unknown-linux-ohos，并同时修复 config.sub 的 KERNEL-OS 拆分及最终 OS 校验；不伪装 Linux、不使用 native --host/--build。

平行 make check 的同一测试对象竞争 .Tpo。保留库构建 -j2，测试完整运行 -j1。三组 Unicode 17.0 官方测试无删减、无源码修改。

正式 Conan create 和消费者已在原生 HarmonyOS 目标机通过。框架 conan-verify/finish、知识系统查重和 Pre-PR 合同尚未完成；不得把原生构建成功当作已发布或已提交。未触发平台 Review/CI。

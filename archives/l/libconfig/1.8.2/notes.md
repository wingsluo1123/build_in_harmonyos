# libconfig 1.8.2 适配笔记

本次任务分支：feat/libconfig-1.8.2。团队：诶，云朵。日期：2026-10-13。

## 配置与依赖

C/C++ 两个共享库，分别导出 libconfig::config 与 libconfig::config++。当前受测配置没有外部包依赖；编译器/CMake/签名工具属于设备工具链，不伪装成库依赖。官方源码及 SHA-256 由 conandata.yml 固定，任务本地源码覆盖仍校验同一 SHA-256。

## 适配与恢复

初次失败是共享库无 SONAME 导致 DT_NEEDED 带相对路径；补 SONAME 后仍需为源树 tests 工作目录提供计算得到的构建树 LD_LIBRARY_PATH。签名后执行上游测试，安装后重新签名。失败捕获输出用 finally 保留。

## 检测环境问题

设备只有 llvm-readelf，没有 CI 脚本调用的 readelf。先前扫描因空输出误报 SONAME；保存原失败/误报记录，不修改平台 ci 脚本。新独立事务仅在任务 PATH 增加调用已验证 llvm-readelf 的私有 readelf 桥接器，最终 L5=pass。桥接器不作为配方提交、不写系统目录、不代表比赛 worker 环境已修复。

## 最终验证

原生 HarmonyOS PC，aarch64，clang 15.0.4，Conan 2.29.1，CMake 4.1.2；上游 16/16，安装包消费者通过。详见 reports/test-report.md。

知识草稿：knowledge/drafts/E15136-draft-A713.kv + .md。只读复用现有 SONAME/运行库/签名知识，新草稿说明本次独立实质增量。

当前阶段为本地真机适配完成。聚合 finish/Pre-PR/Issue/PR/平台 Review/比赛 worker CI 尚未完成；不得将原生 W3 PASS 写成已合并或已发布。
---

**编译结束**: 2026-10-13 15:36
**最终状态**: built

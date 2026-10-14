
## 适配实测（2026-10-11）

- 依赖：dbus/1.14.10.2 + libxml2/2.15.3.1（制品仓已发布）
- 产物：bin/oddjob_request（客户端）+ sbin/oddjobd（守护进程），OHOS aarch64 ELF
- 补丁：patches/0001-oddjobd-selinux-guard.patch（非 SELinux 构建守卫，上游 Gentoo 已知缺陷，portability）
- 探索期踩坑（均在配方中固化）：①config.guess/sub 过旧不识别 ohos → 换 autoconf 2.72 版+conan 缓存含 ohos 支持版；②dbus.pc vs dbus-1.pc 别名；③FUSE umask 077 + uid 映射致 config.status 临时目录写入被拒（E046 变体）→ 探索期 umask 000 绕过，配方不受影响（不跑 configure）；④oddjobd.c selinux 守卫缺陷
- conan-verify：G1/G2/G3 PASS（test_package 消费者测试通过）

---
**编译结束**: 2026-10-11 18:20
**最终状态**: published
---

**编译结束**: 2026-10-11 21:52
**最终状态**: published

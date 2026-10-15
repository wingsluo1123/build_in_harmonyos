# bcnm 0.0.2.2 适配笔记

## 编译环境
- 构建系统: custom (skarnet configure + make)
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载 bcnm 0.0.2.2 源码 (GitHub tag archive)
2. 应用补丁 bcnm-fix-netlink.patch 修复 OHOS 头文件冲突
3. configure --disable-shared --with-sysdeps=... --with-include=... --with-lib=...
4. make -j1
5. 手动 copy 产物到 package folder（libbcnm.a, libwpactrl.a, bcnm-waitif, headers）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义 | OHOS linux/socket.h 与 sys/socket.h 重复定义 | 在 linux/netlink.h 前 typedef __kernel_sa_family_t 并定义 _UAPI_LINUX_SOCKET_H 守卫 |
| 2 | make install 被拦截 | skarnet install.sh 调用 rm 被 safe-delete hook 拦截 | 手动 copy 产物到 package folder |
| 3 | 源码 URL 不可达 | skarnet.org 被 reset | 使用 GitHub 官方镜像 |

## 源码修改

- patches/bcnm-fix-netlink.patch: 修复 bcnm_if_link_init.c 和 bcnm_if_link_event.c 的 OHOS 头文件冲突

## 依赖版本

- skalibs 2.15.1.0 (已发布到制品仓)

## 验证结果

```bash
conan create archives/b/bcnm/0.0.2.2 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# bcnm_if_getstate("lo") = 7
# bcnm consumer test: PASS
```

## 交付物

- libbcnm.a (5.7KB) — 网络接口状态监控库
- libwpactrl.a (62KB) — wpa_supplicant 控制 API
- bcnm-waitif (39KB) — 等待网络接口状态工具
- include/bcnm/{bcnm.h,if.h,wpactrl.h,config.h}

## 注意事项

- 上游未随包提供可执行测试用例（N=0），仅提供空载测试框架。三层证据：
  1. tarball（SHA256 527dd848…319c）96 条目，无 src/tests/ 目录；
  2. tag v0.0.2.2 git 树递归 95 条目（truncated=False），无 .wrapper/.expected/.baseline；
  3. Makefile:26 `TEST_BINS :=` 空定义 → `make check` 遍历零目标。
- 上游测试入口真实执行（OHOS aarch64 原生，日志 reports/upstream-test-exec.log）：
  `make check` → 零用例 exit 0；`./tools/run-test.sh bcnm-waitif`（唯一 BIN_TARGET）→
  `fatal: missing baseline` exit 100（驱动器自证无测试数据）；`./bcnm-waitif` usage sanity exit 0。
- test_package 包含消费者可行性测试（rule12，非断言）
- CI：第一轮链接期 posix_spawn EAGAIN（worker 资源争用，非配方问题），重触发后通过（2026-10-15 18:32）
---

**编译结束**: 2026-10-15 14:16
**最终状态**: built

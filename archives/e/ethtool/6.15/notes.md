# ethtool 6.15 — 适配笔记

> 档案创建时间: 2026-08-06
> 最后更新: 2026-08-06
> 状态: built（conan-verify G2 通过）

---

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | ethtool |
| 版本 | 6.15 |
| 描述 | Utility for examining and tuning network interface parameters |
| 构建系统 | autotools |
| 语言 | C |
| 许可证 | GPL-2.0 |
| 依赖 | libmnl/1.0.5 (netlink 接口) |

---

## 二、编译阶段记录

### Phase 1: 环境准备
- ✅ ohc-run.py init-build 完成（从 kernel.org 下载 tarball）
- ✅ 源码解压到 ~/tmp/builds/ethtool-6.15.work

### Phase 2: 编译
- ✅ configure 完成（参数: `--prefix=$DEFAULT_PREFIX`）
  - 平台识别: 通过 config.guess/sub 补丁
  - 编译器: clang 15.0.4
  - libmnl: ✅ 通过 pkg-config 检测到
  - netlink: ✅ 默认启用
- ✅ make -j2 编译完成，1 个 warning (GNU variable-sized type, 非致命)
- ✅ make install DESTDIR=$TEST_PREFIX 完成（staging 验证通过）

### Phase 3: 测试验证
- ⚠️ make check: test-cmdline 3 cases fail (环境问题: 无网络设备)
- ✅ ethtool --version: version 6.15
- ✅ conan create G2: PASS (ethtool --version test passed)

---

## 三、遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS mktemp 权限 | umask 077 && mkdir 在 HMDFS 上创建 drwx--S--- 目录 | 修改 configure: 使用 $TMPDIR + chmod 755 |
| 2 | E119 sockaddr_storage | OHOS SDK linux/socket.h 与 sys/socket.h 冲突 | 通过 libmnl 依赖的 patch 0004 传递解决 |

---

## 四、源码修改清单

| 文件 | 原因 | 方式 | 补丁 |
|------|------|------|------|
| configure | HMDFS mktemp 权限修复 | 手动编辑 | 0001-configure.patch |

---

## 五、依赖说明

- libmnl/1.0.5: ethtool 的 netlink 接口默认启用，需要 libmnl
- libmnl PR: #2204 (等待 AI review 和 CI)
- 注意: ethtool CI 需要 libmnl 先发布到 ohpcd 制品仓

---

**最终状态**: built (conan-verify G2 通过, 待 libmnl 发布后 CI 可通过)

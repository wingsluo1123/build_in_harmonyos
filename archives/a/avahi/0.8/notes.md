# avahi 0.8 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-11
- 编译器: clang/clang++ (Conan 2.29.1 OHOS 适配版, profile ohos-aarch64)
- 状态: built

## 编译步骤

```bash
conan create archives/a/avahi/0.8 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

- 补丁: 0001-config.guess.patch (HarmonyOS 平台识别) / 0002-config.sub.patch / 0003-configure.patch (umask 022)
- 裁剪: 仅构建 client/core/common 库，禁用 gtk/qt/python/mono/daemon 等组件
  （guile-avahi 等下游只需要 client 库）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "cannot run C compiled programs" | conftest 运行需加载依赖动态库，LD_LIBRARY_PATH 不含依赖库目录 | 配方 build() 注入依赖库目录到 LD_LIBRARY_PATH |
| 2 | PKG_CHECK_MODULES([DBUS], [dbus-1]) 找不到 dbus | dbus 配方未声明 pkg_config_name，PkgConfigDeps 默认生成 dbus.pc | cpp_info.set_property("pkg_config_name", "dbus-1") 覆盖 |

## 源码修改

- `patches/0001-config.guess.patch` — config.guess 增加 HarmonyOS (aarch64-linux-ohos) 识别
- `patches/0002-config.sub.patch` — config.sub 增加 aarch64-linux-ohos triplet
- `patches/0003-configure.patch` — configure 中 umask 022 调整

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| dbus | 1.14.10 | 制品仓已发布 |
| libdaemon | 0.14 | 制品仓已发布 |
| expat | 2.8.2 | 制品仓已发布 |
| libcap | 2.69 | 制品仓已发布 |

## 验证结果

### test_package 消费者测试 (L1) — 1/1 通过

```bash
1/1 Test #1: test_avahi ... Passed 0.04 sec
100% tests passed, 0 tests failed out of 1
```

调用 avahi-common 真实 API: `avahi_address_parse` + `avahi_address_snprint`。

### 上游测试执行 (2026-08-12) — 通过率 100% (官方 TESTS + common 单元测试)

| 口径 | 通过 | 总数 | 通过率 |
|------|------|------|--------|
| 官方 `make check` (TESTS 3 项) | 3 | 3 | 100% |
| avahi-common 单元测试 (6 项) | 6 | 6 | 100% |
| 可正常结束的测试 (含 prioq-test) | 10 | 10 | 100% |

- avahi-common: strlst-test / domain-test / alternative-test / timeval-test / utf8-test / watch-test — 全部 exit=0
- avahi-core: dns-test / hashmap-test / prioq-test / dns-spin-test — exit=0
- 常驻测试 (timeeventq-test / querier-test / update-test): exit=124 超时属设计行为 (事件循环不退出)
- conformance-test: exit=134 崩溃，上游 latent bug (server_callback 误用全局指针 avahi 而非参数 s，
  见 reports/test-report.md)，非适配缺陷，且不在官方 TESTS 中，不阻塞发布

## 注意事项

1. avahi 静态编译 (R26)，未输出 .so 到系统路径 (G3 隔离检查通过)
2. 下游引用: `self.requires("avahi/0.8")`
3. 测试数据详见 `reports/test-report.md` (AI 元数据，不入库)

---

**编译结束**: 2026-08-11 16:55
**测试补充**: 2026-08-12
**最终状态**: published

# libbasicobjects

SSSD [ding-libs](https://github.com/SSSD/ding-libs) 集合中的基础数据对象库:
simplebuffer 可增长字节缓冲区(自动 NUL 终止,支持同步 write),是
libini_config 等库的底层依赖。

## OHOS 适配

- 源:ding-libs 0.6.2 官方发行包(最后提供独立 libbasicobjects 的上游版本,
  子版本 0.1.1;0.7.0 起源码并入 libini_config 不再独立出库)。
- 官方 autotools 构建系统;`--disable-nls` + 目标级构建
  (`make simplebuffer_ut` 连带 `libbasicobjects.la`),绕开伞形仓库中
  path_utils 的 GNU gettext 依赖(OHOS musl 无实现)。
- 上游官方单测 simplebuffer_ut 在 build() 内执行;消费者探针 16 断言。

## 依赖

无(纯 libc)。

## 测试

`conan create` 三阶段:configure/make → 上游 UT(exit 0)→ test_package
(探针 + vendored 上游 UT 复跑)。

## 参考

- 上游:https://github.com/SSSD/ding-libs
- 0.6.2 发行:https://github.com/SSSD/ding-libs/releases/tag/0.6.2

# E555 — PkgConfigDeps 生成的 .pc 名与上游 Makefile 查询名不一致

## 错误特征

```
Package dbus-1 was not found in the pkg-config search path.
No package 'libpci' found
```

或更隐蔽：pkg-config 返回空，`-I`/`-L` 缺失导致头文件找不到；
又或 Makefile 的能力探测被带偏：

```make
LIBPCI_SHARED = $(shell pkg-config libpci && echo true || echo false)
# 误判为 false → 走进引用 /usr/lib/libpci.a 并额外 -lz 的错误分支
```

## 触发条件

- 构建系统: Makefile / autotools，用 `pkg-config` 探测依赖
- 依赖来源: Conan（`PkgConfigDeps` 生成器）

## 根因分析

Conan 的 `PkgConfigDeps` 按 **Conan 引用名**生成 `.pc`：
`dbus/1.14.10` → `dbus.pc`，`pciutils/3.13.0` → `pciutils.pc`。
上游 Makefile 习惯查询发行版包名：`pkg-config dbus-1`、`pkg-config libpci`。
名字对不上 → pkg-config 返回失败/空，轻则缺编译参数，重则让
`$(shell pkg-config <name> && echo true || echo false)` 式探测**误判为 false**，
走进完全无关的回退分支。

## 解决方案

### 推荐方案

在 conanfile 的 `generate()` 里补建别名 `.pc`，并把 `PKG_CONFIG_PATH`
显式指向 generators 目录（纯配方侧适配，不改上游、不碰系统路径）：

```python
gen = self.generators_folder
for alias, source in (("dbus-1.pc", "dbus.pc"), ("libpci.pc", "pciutils.pc")):
    src, dst = os.path.join(gen, source), os.path.join(gen, alias)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copyfile(src, dst)

self.run(f'PKG_CONFIG_PATH="{gen}" make -j1 ...')
```

### 备选方案

绕开 pkg-config，在配方里显式拼出 `-I/-L/-l` 传给 make
（要手工维护依赖列表，漏一个就编不过）。

### 禁止做法

- ❌ 往系统 `${prefix}/lib/pkgconfig` 写 `.pc`——污染共享文件系统，CI 干净 worker 上不存在。
- ❌ 用发行版包管理器装 `dbus-1-dev` 之类——OHOS/CI 无包管理器，且引入与 Conan 依赖链无关的系统库。

## 验证

```bash
PKG_CONFIG_PATH=<gen> pkg-config dbus-1 --cflags    # 别名生效后应输出 -I...
ls <gen>/*.pc                                       # 应同时存在 dbus.pc 与 dbus-1.pc
```

## 关联条目

- 相关: E550（同为构建期依赖/能力判断问题）

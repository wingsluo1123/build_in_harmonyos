# 应用型 autotools 包含 -module -shared 插件时禁用 --disable-shared 冲突

## 问题

nbdkit 1.48.0 的 Conan 配方首版沿用模板静态化逻辑（`--enable-static
--disable-shared`），configure 正常，make 在构建动态插件时失败：

```
libtool: error: cannot build a shared library
See the libtool documentation for more information. Fatal configuration error.
make[3]: *** [Makefile:639: nbdkit-cc-plugin.la] Error 1
```

## 根因

autotools 项目的动态插件/过滤器由 libtool 以 `-module -avoid-version
-shared` 构建，本质是共享库。`--disable-shared` 在 libtool 层面关闭共享库
构建能力，与 `-module -shared` 直接冲突，libtool 拒绝执行链接。

「系统同名库静态化」（R26/E028/E073）针对的是**库产物与系统库同名、
动态链接会污染 /lib /lib64** 的场景；而应用型服务器（nbdkit）的插件是
本包自产自用的共享模块，不属于系统同名库范畴——不加区分地套用
`--disable-shared` 会破坏插件构建。

## 方案

1. 判断包类型：`package_type=application` 且构建系统为 autotools/libtool，
   源码含 `-module -shared` 的插件/过滤器/扩展模块 → 不得 `--disable-shared`；
2. `generate()` 中移除 `--enable-static/--disable-shared` 对，可选依赖层面
   按需 `--without-*` 禁用缺失库即可；
3. 仅库型包（无插件模块）才应用 R26 静态化；
4. `package_info`：application 型 `bindirs` 设 `["bin","sbin"]`
   （conan Autotools.install 放 `bin/`，本地 autotools 默认 `sbin/`）。

```python
# generate() 修复示例
tc = AutotoolsToolchain(self)
tc.configure_args.append("--without-gnutls")  # 可选依赖照常禁用
# 不再追加 --enable-static / --disable-shared
tc.generate()

# package_info
self.cpp_info.bindirs = ["bin", "sbin"]
self.cpp_info.libs = []
```

## 验证

- 修复前：`conan create` G2 失败，`cannot build a shared library`；
- 修复后：`conan create` 通过，`plugins/cc/.libs/nbdkit-cc-plugin.so` 等
  插件正常生成，test_package 消费者验证（dlopen 公开插件 ABI）
  `nbdkit 1.48.0 consumer validation PASSED`。

## 适用边界 / 反例

- **适用**：应用型 autotools 包，含 libtool `-module -shared` 插件/过滤器
  （服务器 + 插件架构，如 nbdkit、各类 server/plugin 组合）。
- **不适用**：纯库型包（无插件模块），仍可 `--disable-shared` 静态化；
  系统同名库场景按 R26/E028/E073 处理（方向相反）。

## 查重差异（七轴）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否（无同签名条目） |
| causal_duplicate | 否（与 E028/E073 因果相反：前者防污染系统库，本候选是应用插件必须共享） |
| trigger_overlap | 部分（E345 同为动态模块主题，面向消费者验证缺公开 API） |
| solution_overlap | 部分（E345=私有 host 验证；本候选=保留共享、不禁用） |
| combination_novelty | 是（application + 插件 -module -shared + generate() 误禁共享） |
| boundary_novelty | 是（库型可静态 / 应用型含插件不可禁共享） |
| test_migration_novelty | 是（conan create 报错可复现，可迁移其他 autotools 插件类包） |

## 关联

- 产生库：nbdkit 1.48.0（archives/n/nbdkit/1.48.0）
- 相关条目：E028、E073、E345
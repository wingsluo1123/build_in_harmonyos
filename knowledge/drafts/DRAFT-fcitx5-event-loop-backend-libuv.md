# DRAFT: OHOS 无 systemd → EVENT_LOOP_BACKEND 须 libuv

## 现象

1. Step2 编译通过后核心测试运行时抛：
   ```
   F2026-... testinputcontext.cpp:362] Received exception: No available event loop implementation.
   ```
   （testevent / testeventdispatcher / testinputcontext / testinstance /
   testunicode / testquickphrase 等 7 个测试失败）
2. 配方切 libuv 后端后 CMake 报：
   ```
   CMake Error at CMakeLists.txt:109 (message):
     Failed to find a valid event loop backend.  Backends checked: libuv
   ```

## 根因

OHOS 无 systemd。`EVENT_LOOP_BACKEND=none` 时 `event_none.cpp` 的
`createDefaultEventLoop()` 返回 `nullptr`，`EventLoop` 构造抛
`"No available event loop implementation"` —— 不是测试缺陷，是后端缺失。
切 `libuv` 后端后，libuv conan 包自带 `libuv.pc` 的 `prefix=/usr/local`
（conan 包未 relocated），pkg-config 解析出错误 `-L/usr/local/lib`；且
`CMakeToolchain.cache_variables["PKG_CONFIG_PATH"]` 不会作为环境变量传给
pkg-config，导致 `pkg_check_modules(LibUV)` 找不到 libuv。

## 解决方案

```python
self.requires("libuv/1.52.1")
# build(): cmake.configure(cli_args=[..., "-DEVENT_LOOP_BACKEND=libuv", ...])

# generate()：写修正 prefix 的 libuv.pc 并注入 PKG_CONFIG_PATH
pc_dir = os.path.join(self.generators_folder, "pkgconfig")
os.makedirs(pc_dir, exist_ok=True)
with open(os.path.join(pc_dir, "libuv.pc"), "w") as f:
    f.write("prefix=%s\n...Libs: -L${libdir} -luv ..." % libuv_pkg.package_folder)
self.buildenv.append("PKG_CONFIG_PATH", pc_dir)
```

## 验证

- Step2 上游测试 38/38 全部通过（libuv 后端，LD_LIBRARY_PATH=build bin）；
- conan create 消费者与鸿蒙专项测试 PASSED（fcitx5/5.1.14 实测）。

## 适用边界

OHOS（HarmonyOS PC, aarch64）上构建含事件循环（EventLoop）的库/应用；
systemd 缺失时 libuv 是可得的最小真实后端。libuv.pc prefix 重定位处理
同样适用于其他 pkg-config 探测依赖。

## 相关条目

- DRAFT-cmake-harmonyos-system-name-soname
# interception-dual-function

[interception-tools](https://gitlab.com/interception/linux/tools) 的双功能键插件：
拦截键盘事件流，把同一个键的「轻按（tap）」与「长按（hold）」映射到不同按键。
典型用法是把修饰键变成「hold = Ctrl，tap = Delete」，减少小指负担。

- 上游：https://gitlab.com/interception/linux/plugins/dual-function-keys
- **命名说明**：本仓库归档名取比赛清单条目名 `interception-dual-function`（1.5.0）；
  上游项目名为 `dual-function-keys`，产物为 `bin/dual-function-keys`，两者指同一软件。
- 许可：MIT
- 构建系统：裸 Makefile（无 configure）
- 交付物：`bin/dual-function-keys`（单个命令行可执行文件）+ man page
- 依赖：`yaml-cpp/0.8.0`（静态）、`libevdev/1.13.7`（动态）

## 工作原理

作为 interception-tools 的过滤插件运行：从 stdin 读取 `struct input_event`
二进制流，按 `-c <cfg.yaml>` 指定的映射改写事件，再写回 stdout。
运行时由 udevmon 负责把键盘设备接入该管道。

```yaml
TIMING:
  TAP_MILLISEC: 200
  DOUBLE_TAP_MILLISEC: 150

MAPPINGS:
  - KEY: KEY_LEFTSHIFT
    TAP: KEY_DELETE
    HOLD: KEY_LEFTSHIFT
```

## 鸿蒙 PC 适配

- 内核 UAPI 头 `linux/input.h` 由 OHOS clang 15 sysroot 自带，无需头文件注入。
- 随包补丁 1 枚（`0001-cfg.cpp.patch`）：上游
  `build_tap()`/`build_hold()` 的标量分支用 `YAML::Node::size()` 做分配尺寸
  （yaml-cpp 对标量节点返回 0），`calloc(0, sizeof(Mapping))` 只得到 1 字节
  可用堆块，随后写 `->code` 越界。glibc 的 `calloc(0)` 返回块足够大掩盖了该
  缺陷，OHOS musl 下必崩（实测 SIGSEGV，rc=139）；改为 `calloc(1, ...)`。
- 上游 Makefile 硬编码 `CC/CXX/INCS/CFLAGS/CXXFLAGS/LDFLAGS`，构建时以 make
  命令行变量覆盖（R33：编译器取自 Conan profile）。驱动 `-Werror` 在 clang 15
  上会因上游 K&R 风格函数定义的 `-Wstrict-prototypes` 告警而失败，故覆盖
  CFLAGS/CXXFLAGS 时移除。
- 交付 ELF 已 selfSign 签名（E077/E135）。

## 测试

上游无自动化测试（清点证据见 `test_package/MANIFEST.yml`）。消费者侧验证：
`test_dfk.py`（上游接口功能 6 断言）+ `test_ohos.sh`（鸿蒙平台 5 断言，
含 `calloc(0)` 回归探针）。

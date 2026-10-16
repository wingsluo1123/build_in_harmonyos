- **三方库名称**：libsigrokcxx
- **上游版本**：0.5.2
- **上游仓库地址**：https://sigrok.org/（`libsigrokcxx` 为 libsigrok 源码树中的 `bindings/cxx/`，无独立 tarball）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E538（统一 C++17/libc++ profile 后发布依赖图选项不一致）、DRAFT-24650（conan 2 override 改 package_id → binary 失配 → 源码重建）、DRAFT-13572（GNOME C++ 绑定家族 ABI 线识别）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | `bindings/cxx/` 无 `Makefile.am`、无测试源，上游无测试套件 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | libsigrok 树的 `tests/*.c`（Check 框架）属 C 库 `libsigrok/0.5.2`，在其 W3 日志中计数（断言行 `Checks: 76`），已在那边统计 |
| **合计** | **0** | |

#### 上游测试入口核验证据（双源一致）

上游无独立 `libsigrokcxx` 仓库（GitHub `sigrokproject/libsigrokcxx` 返回 404；C++ 绑定随 C 库发布）。权威 tag `sigrokproject/libsigrok @ libsigrok-0.5.2` 的 `bindings/cxx/` 目录（GitHub API 实测）与本包 conandata 所载 sha256 校验通过的官方 tarball 解压树**逐条一致**，共 10 个条目：

```
ConfigKey_methods.cpp  ConfigKey_methods.hpp  ConfigKey_methods.i
QuantityFlag_methods.cpp  QuantityFlag_methods.hpp
classes.cpp  enums.py  Doxyfile  libsigrokcxx.pc.in  include/
```

- `find bindings/cxx -iname '*test*'` → **0 命中**；`find bindings/cxx -name 'Makefile*'` → **0 命中**（无构建系统测试目标）。
- **防歧义说明**：上游 `bindings/` 目录下有 **5 个子目录**（`cxx`、`java`、`python`、`ruby`、`swig`），它们是五种语言绑定的**实现目录**，不是测试用例，任何语言绑定目录下均无测试源。

#### 显式披露：上游 0.5.2 无随包测试用例，上游测试执行数为 0

**事实**：上游 libsigrokcxx 0.5.2（随 `sigrokproject/libsigrok` tag `libsigrok-0.5.2` 发布）**不含任何随包测试用例**，本 PR 对上游测试的执行数为 **0**（非跳过、非失败）。

**0 执行的具体技术原因**：
1. 上游 `bindings/cxx/` 无构建系统测试目标——目录内没有 `Makefile.am`/`Makefile.in`，上游的 autotools 测试入口（`make check`）不存在于该目录；
2. 上游 `bindings/cxx/` 无任何测试源文件（`*_test*` 0 命中），不存在可执行的测试二进制或测试脚本；
3. C++ 绑定的行为验证由 C 库的 Check 套件间接覆盖（`libsigrok.h` 语义层），该套件归属 `libsigrok/0.5.2` 包，由其配方自身强制校验并在其归档登记；
4. 因此本包补全了 3 个适配后用例（1 消费者 + 2 项鸿蒙特有非断言）作为行为验证，3/3 通过。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无套件 |
| 集成测试 | 1 | +1 | `test_package/consumer.cpp`：枚举 API 解析/链接 + `Quantity::values()` 从共享库读出注册表（W3 日志实测 `enum: Quantity::values() -> 33 entries`） |
| 鸿蒙特有测试 | 2 | 新增 | ① 共享库 closure 加载 `dlopen(RTLD_NOW)`；② 发行 ELF 的 `.codesign` 段校验 |
| **合计** | **3** | **+3** | 3/3 通过（本机为 OHOS aarch64，探针真实执行而非仅编译） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（上游本就没有测试用例）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试

> - **补全的测试范围**：已安装包的消费可行性 —— 头文件可解析、C++ 绑定可链接、共享库 `DT_NEEDED` 闭包可加载、发行 ELF 带 OHOS 签名。
> - **补全原因**：`bindings/cxx/` 没有构建系统测试目标，也没有任何测试源；上游把 `Doxyfile` 与 `*.py` 放在该目录仅用于生成 `enums.hpp`。
> - **新增测试文件清单**：
>   1. `test_package/consumer.cpp` — 消费者探针：枚举 API + `Quantity::values()` + OHOS closure 加载
>   2. `test_package/conanfile.py` — 编译/链接/签名/执行驱动（`build()` + `test()`）
>
> 其中两个鸿蒙特有用例为**非断言**测试：closure 加载只观测 `dlopen` 返回结果，签名检查只观测 `.codesign` 段是否存在，均不断言具体值。

## 验证结果

- 编译状态：通过（`libsigrokcxx built successfully`，`libsigrokcxx.so.0.5.2 signed (.codesign verified)`）
- 上游测试用例通过率：N/A（上游 `bindings/cxx/` 无套件；libsigrok 的 Check 套件（其 W3 日志断言行 `Checks: 76, Failures: 0, Errors: 0`）归属 `libsigrok/0.5.2`，由该包配方自身强制校验并在其归档登记，不计入本包）
- 新增测试用例通过率：3/3（100%）

## 补充说明

### 与上游构建链的差异

1. **doxygen → `patches/gen_enums.py`**：上游用 doxygen 由 `libsigrok.h` 生成 `enums.hpp`，CI 无 doxygen；枚举生成本质是机械解析 C 头文件，改为直接解析已安装的 `libsigrok.h`（11 个枚举全量生成）。
2. **autotools + libtool → 直接调用 clang++**：直接编译 `classes.cpp`（其通过 `#include <enums.cpp>` 内联枚举实现）并链接为 `libsigrokcxx.so.0.5.2`，显式 `-Wl,-soname,libsigrokcxx.so.0`。
3. **OHOS 签名做成强制步骤**（对齐 `libsigrok/0.5.2`）：`binary-sign-tool`/`readelf` 缺失直接报配置错误，签名后复核 `.codesign`。

### GLib 版本冲突的处置（关键决策）

| 依赖 | 钉住的 GLib | 形态 |
|------|-------------|------|
| `libsigrok/0.5.2` | `glib/2.88.0` | static |
| `glibmm/2.66.7.1` | `glib/2.84.0.1` | shared |

同一图容不下两个 glib 版本，必须 `override` 归一。**归一到 `glib/2.88.0`（static）会失败**：重建后的 glibmm 测试套件 31/33 当场 `SIGABRT`（`GLib:ERROR:../glib/gquark.c:63:g_quark_init: assertion failed: (quark_seq_id == 0)`）——static glib 被静态链进 `libglibmm-2.4.so.1` 与 `libgiomm-2.4.so.1`，进程内出现两份 GLib 全局状态。

因此归一到 **`glib/2.84.0.1`（shared）**：
- `glibmm/2.66.7.1` 直接复用制品仓已发布 binary（package_id `91be7014a920f4…`），无需重建；
- 仅 `libsigrok/0.5.2` 因 package_id 变化在干净环境需源码重建（其上游 Check 由该包配方自身强制校验）；
- 消费端 `DT_NEEDED` 中的 `libglib-2.0.so.0` 为共享库，不再有 GLib 双份状态问题。

### 产出物

- `lib/libsigrokcxx.so.0.5.2`（SONAME `libsigrokcxx.so.0`）+ 符号链接 `libsigrokcxx.so.0` / `libsigrokcxx.so`
- `include/libsigrokcxx/libsigrokcxx.hpp`、`include/libsigrokcxx/enums.hpp`（生成）
- 已签名：`.codesign` 段存在

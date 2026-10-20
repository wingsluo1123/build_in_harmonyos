# 无 GPU 构建机上跑 Vulkan/D3D 上游测试套件：假绿识破 + ICD 直接当 `libvulkan.so.1`

- **来源**：vkd3d 1.19（Wine 的 Direct3D 12 → Vulkan 翻译层，287 个 `*.shader_test`）HarmonyOS PC aarch64 适配
- **草稿名**：`DRAFT-vkd3d-1.19-no-gpu-vulkan-test-substrate`
- **可推广**：任何自带 Vulkan/EGL/OpenGL/D3D 渲染测试框架、且在找不到设备时"静默早退"的包
- **查重结论**：知识库检索 `libvulkan.so.1` / `vk_swiftshader` / `shader_runner` / `VK_ICD_FILENAMES` **零命中** ⇒ 判 `create`。
  相邻条目仅覆盖构件面（`E1361`/`E2186` 依赖旗标、`E114`/`E1016` HMDFS 暂存目录），**不覆盖**"测试期图形设备底衬 + 零执行假绿"这一面。

---

## 一、问题一：整片 PASS，实际零执行（假绿）

### 症状

构建机无任何 Vulkan 时，`make check` 会**成功退出**，日志里 287 个 `shader_test` 全部 `PASS`：

```text
PASS: tests/hlsl/dot.shader_test
PASS: tests/hlsl/discard.shader_test
...
```

**但一个测试都没跑。** 两处代码叠加造成：

```c
/* tests/shader_runner_vulkan.c:2142 */
if (!init_vulkan_runner(&runner))
    return;                       /* 找不到设备 ⇒ 直接返回，一个用例都不跑 */
```

```c
/* include/private/vkd3d_test.h:328 */
return vkd3d_test_state.failure_count || vkd3d_test_state.todo_success_count;
/* 跳过/未执行 都不计入 failure ⇒ 退出码 0 ⇒ automake 记 PASS */
```

### 判别判据（稳定、可自动化）

- 被测二进制在无设备时走的是**提前 return** 分支（`shader_runner_vulkan.c:2142`）；
- **且**日志里该程序的计数**为 `0 tests executed`**——注意
  `include/private/vkd3d_test.h:316` 在 `vkd3d_test_main()` 返回后**无条件**打印这一行，
  `:328` 的退出码只看 `failure_count || todo_success_count`，所以**无设备时这一行照样出现，
  只是 N=0**（行存在 ⇏ 真执行）。真执行的判据只能取 **N>0**。

⇒ 因此「日志里有没有计数行」**不是**可用判据（无设备时它也在）；正确判据是
「有没有 **N>0** 的计数行」。此时 `make check` 退 0 **不代表通过率**，不能写进申报表。
这就是「分母被环境悄悄抽空」——比显式红更危险，因为它看起来是绿的。

### 处置（两层封堵，不靠自觉）

**第一层（前置）**：配方在**取不到测试底衬时直接抛异常**，而不是照常跑 `make check`：

```python
pkg = self._swiftshader_package_folder()
if not pkg:
    raise ConanException(
        "refusing to run `make check` without a Vulkan device "
        "(that would report zero executed tests as passes)")
```

**第二层（后置断言）**：仅第一层不够——底衬**存在但运行期加载失败**（ABI/依赖不匹配、
ICD 被拒）时，287 份 `shader_runner` 仍会打印 `0 tests executed`、退 0，automake 仍记
293 PASS。所以 `make check` 之后必须**解析日志做 N>0 断言**并 `raise`：

```python
autotools.make(target="check")
self._assert_tests_really_executed()   # 6 个程序各自 N>0（vkd3d_api 允许 0+skipped 原文）
                                       # + 287 份 shader_runner 求和 >0，否则 raise
```

两层合起来才叫"结构性排除零执行＝全绿"；只有第一层时该说法是过度声明。

## 二、问题二：设备从哪来 —— ICD 可以直接顶替 loader

构建机 `uname -a` = `HarmonyOS … aarch64`，但：全盘无 `libvulkan*`、无 `*icd*.json`、
`/dev/dri` 不存在、无 GPU 节点；OHOS SDK sysroot 里也只有 Vulkan **头**。

已发布的 `swiftshader` 包（`package_type = shared-library`）提供：
`lib/libvk_swiftshader.so`（ELF 64-bit arm64）、`res/vk_swiftshader_icd.json`。

**关键判据**：ICD 会导出全部**全局**入口点，而 `dlopen` 型调用方只需要从某一个符号开始：

```text
$ llvm-nm -D --defined-only libvk_swiftshader.so | grep -E 'vk(CreateInstance|GetInstanceProcAddr|EnumeratePhysicalDevices|EnumerateInstanceVersion)$'
T vkCreateInstance
T vkEnumerateInstanceVersion
T vkEnumeratePhysicalDevices
T vkGetInstanceProcAddr
```

因此**把 `libvk_swiftshader.so` 命名成 `libvulkan.so.1` 放在 `LD_LIBRARY_PATH` 上，
就能被 `dlopen` 直接加载，不需要 Khronos Vulkan-Loader 包**——
这在"loader 包未发布"的 registry 上尤其关键（本例 `vulkan-loader/1.3.295` 恰好不可服务）。

30 行探针实测原文（正/反对照）：

```text
# 带底衬
DLOPEN_OK
vkGetInstanceProcAddr=0x5c9cd9a514 vkCreateInstance=0x5c9cd99b48
vkCreateInstance rc=0 inst=0x5c1b68cd38
vkEnumeratePhysicalDevices rc=0 count=1
DEVICE[0]=SwiftShader Device (LLVM 10.0.0) api=1.3.0 type=4

# 不带底衬（对照组）
DLOPEN_FAIL: Error loading shared library libvulkan.so.1: No such file or directory
```

正确执行后，`make check` 的日志会给出**带真实计数的行**（本例含 `XF`/`SK` 明细）：

```text
PASS: tests/hlsl/depth-out.shader_test (2 XF) (2 SK)
```

## 三、接线（配方侧）

```python
def build_requirements(self):
    self.tool_requires("swiftshader/0_git20260921")   # 测试期专用，不进消费者图

def generate(self):
    ...
    pkg = self.dependencies.build["swiftshader"].package_folder
    substrate = os.path.join(self.build_folder, "vk-substrate")
    os.makedirs(substrate, exist_ok=True)
    src = os.path.join(pkg, "lib", "libvk_swiftshader.so")
    for name in ("libvulkan.so.1", "libvulkan.so"):   # 后者给链接期探测兜底
        shutil.copy2(src, os.path.join(substrate, name))
    icd = os.path.join(substrate, "vk_swiftshader_icd.json")
    shutil.copy2(os.path.join(pkg, "res", "vk_swiftshader_icd.json"), icd)
    env.prepend_path("LD_LIBRARY_PATH", substrate)
    env.define("VK_ICD_FILENAMES", icd)
    env.define("VK_DRIVER_FILES", icd)
```

用 `shutil.copy2` 而不是 `os.symlink`：HMDFS 上软链接与 chmod 的行为都不可靠。

## 四、★附加要点：别让测试替身的 SONAME 污染生产语义

vkd3d 的 `configure.ac` 是这样取运行期 loader 名字的：

```m4
AC_ARG_VAR([SONAME_LIBVULKAN], [shared object name for the Vulkan library])
AS_IF([test "x$SONAME_LIBVULKAN" = "x"], [VKD3D_CHECK_VULKAN],
      [AC_DEFINE_UNQUOTED([SONAME_LIBVULKAN],["$SONAME_LIBVULKAN"], …)])
```

若不给值，`VKD3D_CHECK_VULKAN` 会 `AC_CHECK_LIB` 探测本机 `libvulkan.so` —— 在构建机上探到的
正是**测试替身**，于是替身自己的 SONAME 被烤进成品，运行期会去找 swiftshader 而不是真 loader。

⇒ 必须显式传**生产值**：`env.define("SONAME_LIBVULKAN", "libvulkan.so.1")`。
本例 `Makefile.am` 完全不引用 `VULKAN_LIBS`（grep 0 处），即 vkd3d **不链接** Vulkan loader，
所以这样传不损失任何功能，只是把"自动探测"换成"显式正确的值"。

## 五、适用边界与反例

| 情形 | 处置 |
|---|---|
| 上游测试在无设备时**显式失败**（非零退出） | 不要用底衬"救绿"；先分清缺设备还是被测代码问题 |
| 想用 `--without-vulkan` / 关掉图形后端让构建通过 | ⛔ 等于砍掉被测功能，不是适配 |
| loader 包已发布 | 优先用真 loader + `VK_ICD_FILENAMES` 指 ICD；本条的直接顶替是 loader 不可得时的等价路 |
| 底衬起不来 | 如实报「真执行数 / 零执行项数 / 首条错误原文」，⛔ 不把"全 PASS"当通过率；必要时按依赖未就绪转手 |
| swiftshader 是 CPU 实现 | 与光栅化精度/驱动特性相关的失败须逐项区分「CPU 实现差异」与「本次适配引入」 |

## 六、复现命令

```bash
# 底衬可用性（HTTP 200 = 可服务）
curl -s -o /dev/null -w '%{http_code}\n' \
  https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/v2/conans/swiftshader/0_git20260921/_/_/latest

# 装上并取路径
conan install --requires=swiftshader/0_git20260921 -r=ohpcd --build=never \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 探针正/反对照（见 §二 的 30 行 dlopen 程序）
LD_LIBRARY_PATH=<substrate> ./vkprobe    # 期望 DEVICE[0]=SwiftShader Device …
./vkprobe                                # 期望 DLOPEN_FAIL
```

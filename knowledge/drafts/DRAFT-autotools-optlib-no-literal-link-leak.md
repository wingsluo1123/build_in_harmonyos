# autotools 可选依赖检测失败把 *_LIBS 替换为字面量 "no" 泄漏进链接行：make 命令行变量覆盖处置法

> 对应 KV：`knowledge/drafts/DRAFT-autotools-optlib-no-literal-link-leak.kv`
> 实证来源：xroar 1.11 真机 shadow CI（2026-10-13，r4→r6）

## 一句话

部分 autotools 上游在可选依赖（OpenGL/音频库等）检测失败时，把 `AC_SUBST` 的
`<NAME>_LIBS` 变量替换为**字面量字符串 `"no"`**而不是空串，而消费这些库的源
文件又是**无条件编译**的——于是链接行出现一个叫 `no` 的文件参数
（`clang: error: no such file or directory: 'no'`）；单纯把变量置空则暴露出
真正的 `undefined symbol`。这不是平台问题，是上游 configure 模板缺陷，
用 **make 命令行变量赋值**即可在不打补丁的情况下修复。

## 使用说明（处置流程）

1. **识别**：链接阶段报 `no such file or directory: 'no'`（且编译全过）。
2. **定位泄漏变量**：在构建树里查值恰好是 `no` 的 make 变量：
   ```sh
   grep -n '^[A-Za-z_][A-Za-z0-9_]* = no$' <build-dir>/**/Makefile
   ```
3. **确认消费点**：报错符号属于哪个源文件（如 vo_opengl.c 引用
   glGenTextures）；确认该源文件在当前配置下无条件编入
   （grep 生成 Makefile 的 `xxx_OBJECTS` / Makefile.am 的条件块）。
4. **选值**：
   - 若 OHOS 设备有等价系统库提供同名符号（GL 3.0 核心符号 ←
     `/system/lib64/libGLESv3.so`），用 make 命令行注入：
     ```python
     self.run('CONFIG_SHELL=/bin/sh SHELL=/bin/sh make -j1 GL_LIBS=-lGLESv3',
              env="conanbuild")
     ```
   - 若消费源文件在禁用该依赖时本应成为纯 stub（无实际调用路径），置空
     `VAR=` 即可；但必须跑通消费者测试确认没有真实调用走到这些符号。
5. **验证**：`make V=1 <target>` 目检链接行不再出现 `no`/未定义符号。

## 与既有草稿的区分（查重记录）

- `DRAFT-jnoise-0.6.0-makefile-linkline-literal-cxx-name`：jnoise 是**编译器
  名硬编码在命令位置**，配方根本不引用 `$(CXX)`，`make CXX=` **无效**；
  本条是**变量被赋值为字符串 "no"** 且规则确实引用了 `$(VAR)`，`make VAR=`
  **有效**。判别方法：`make V=1` 看报错参数出现在"命令名"位置（jnoise 型）
  还是"参数"位置（本条型）。
- `DRAFT-ohos-gl-symbols-are-dispatcher-stubs`：本条只解决**链接期**符号落位；
  若包在运行期真的调用 GL 渲染，libGLESv3 直连符号是调度空桩，必须按该草稿
  走 `eglGetProcAddress`/gl4es/osmesa 路线。headless（不做渲染）包直连链接
  即可。
- `DRAFT-E590-libyal-optional-dep-autodetect-ohos`、
  `xfsprogs-7.2.0-autotools-libs-preset-poisons-ac-check`：讲的是"可选依赖
  自动检测在 OHOS 上的假阳/假阴"，不涉及 `= no` 字面量进入链接行。

## 适用范围

- 所有 autotools 项目、所有平台（非 OHOS 特有），conan/ci/手工构建均适用。
- 典型高危形态：configure.ac 自己拼 `AC_SUBST([X_LIBS])` 且失败分支写
  `X_LIBS="no"`；或 m4 宏把检测结果直接回填。
- 不适用：CMake/Meson 项目（无此替换模式）；命令位置硬编码型（见 jnoise 草稿）。

## 输入 / 输出

- 输入：构建树路径（含生成的 Makefile）、失败的链接日志。
- 输出：泄漏变量名；修复用 make 命令行赋值语句（含注入值或空值）；
  验证命令（`make V=1` 复核）。

## 示例（xroar 1.11 实测）

```
现象（r4）：
  OBJCLD   xroar
  clang-15: error: no such file or directory: 'no'
定位：
  grep '^[A-Za-z_]* = no$' src/Makefile   →   GL_LIBS = no
  链接行（make V=1）尾部：... ../portalib/libporta.a -lm   no
r5 置空 GL_LIBS= →
  ld.lld: error: undefined symbol: glGenTextures / glTexImage2D / ...
r6 GL_LIBS=-lGLESv3 →
  链接通过；conan create exit=0，test_package 5/5，L1e 反向验证 rc=1
```

## 验证命令

```sh
grep -c "directory: 'no'" <conan-create-log>   # 修复后为 0
make V=1 xroar 2>&1 | tail -1                  # 链接行无 'no'
```

# sct 1.0.0：make 命令行变量覆盖 Makefile 的 `+=` 追加，X11 链接参数被丢弃

> 草稿（DRAFT）— 来自 sct 1.0.0 HarmonyOS PC (aarch64) 适配的真实构建日志。
> 与 `.kv` 同 stem 配对，字段见
> `knowledge/drafts/DRAFT-sct-1.0.0-make-commandline-var-suppresses-append.kv`

## 问题

sct 1.0.0 是纯 Makefile 的 X11 小工具（`sct.c` + `Makefile`，无 configure）。
用 Conan 包装并交叉编译到 OHOS aarch64 时，第一次配方把 toolchain 参数写成
make 命令行变量：

```bash
make CFLAGS="$CFLAGS $CPPFLAGS -std=c99 -Wall" LDFLAGS="$LDFLAGS" INCS= LIBS=
```

编译阶段通过，链接阶段失败：

```text
undefined reference to `XOpenDisplay'
undefined reference to `XRRGetScreenResourcesCurrent'
undefined reference to `XRRSetCrtcGamma'
```

## 根因

GNU make 的变量优先级：**命令行赋值 > Makefile 内赋值（含 `+=`）> 环境变量**
（只有 `override` 指令能压过命令行）。上游 Makefile 的关键两行是：

```make
CFLAGS +=  -std=c99 -Wall ${INCS}
LDFLAGS += -lX11 -lXrandr ${LIBS}
```

一旦 `CFLAGS` / `LDFLAGS` 出现在 make 命令行上，这两行 `+=` 就被整体忽略。
Conan 的 AutotoolsDeps 只提供 `-I` / `-L` 路径，`-lX11 -lXrandr` 依赖 Makefile
自己追加；追加失效后链接行没有这两个库，于是 X11/XRandR 符号全部未定义。
注意写 `LDFLAGS="$LDFLAGS ..."` 仍然是命令行赋值，**不会**保留 Makefile 的追加。

## 修复

把变量放到 make 的**环境**里（shell 前缀赋值 + Conan `env="conanbuild"`），
命令行只保留要替换的项目变量：

```python
def build(self):
    apply_conandata_patches(self)
    self.run(
        f'cd "{self.source_folder}" && '
        'CFLAGS="$CFLAGS $CPPFLAGS -std=c99 -Wall" '
        'LDFLAGS="$LDFLAGS" '
        'make -j1 INCS= LIBS=',
        env="conanbuild",
    )
```

`INCS= LIBS=` 仍可安全放在命令行：它们只用于替换 Makefile 里指向
`/usr/local` 的宿主机默认路径，不影响那两行 `+=` 所追加的
`-lX11 -lXrandr`。

## 验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# 正向：conan create 与 test_package 通过（18/18 断言）
readelf -d package/bin/sct | grep NEEDED
#   NEEDED  libX11.so.6
#   NEEDED  libXrandr.so.2
# 负向：把 CFLAGS/LDFLAGS 改回 make 命令行变量，链接重新报上述 undefined reference
```

## 适用边界

- **适用**：Conan（或任何脚本）包装 raw Makefile；Makefile 用 `+=` 追加必需参数；
  交叉构建需要注入 toolchain 的 include/lib 路径。
- **不适用**：autotools / CMake / Meson 工程（由 toolchain 文件统一管理 flags）；
  Makefile 用 `override` 或直接引用 conan 变量时不会触发。
- **判别方法**：`grep -nE '^\s*(CFLAGS|LDFLAGS|LDLIBS)\s*\+=' Makefile`；
  命中即不要在 make 命令行上给同名变量赋值。

## 与既有知识的差异

- **E392**（raw-makefile-conan-recipe-pattern）覆盖 get() filename / 编译器显式传递 /
  make cwd 等陷阱；本条聚焦"命令行变量覆盖 `+=` 导致的链接参数丢失"。
- **E636** 记录的是反向情形：上游 Makefile 自己在子 make 命令行上写死
  `CFLAGS=`/`LFLAGS=`，让 conan 的环境变量失效；本条是配方侧在 make 命令行上
  写 `CFLAGS=`/`LDFLAGS=`，让上游 Makefile 的 `+=` 追加失效。两者同源于 GNU make
  的变量优先级，但触发方与修复方向相反（E636 改用 Makefile 自有旋钮；本条改用
  环境变量传 flags）。
- **E568** 记录的是 Diaz 系工具（tarlz/lzip）自身的构建三件套；本条是通用 make
  变量优先级问题，适用于任意 raw Makefile 包装场景。

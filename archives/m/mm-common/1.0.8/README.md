# mm-common 1.0.8 — 鸿蒙 PC conan 制品

`mm-common` 是 GNOME C++ 绑定（libsigc++ / glibmm / gtkmm / pangomm …）共享的构建支撑包：
`mm-common-get`、`mm-common-prepare` 两个命令，`mm-*.m4` Autoconf 宏，文档工具脚本、doctags，
以及 `mm-common-util` / `mm-common-libstdc++` 两个 pkg-config 模块。

`os=OHOS, arch=armv8`(=aarch64) 的 conan 包，包内不含任何编译产物，只有脚本 + 数据 + 手册页。

真机 shadow CI 全绿（`G0/KC/JC/L0/L1/L2/L4/L5` + L1e 反向验证，`test_package` 14/14，Total 1 / Success 1），
验证 commit `f2d58bf1a7`，profile `ohos-local`（clang 15 / libc++ / cppstd17 / OHOS 6.0）。

## 出包（鸿蒙 PC CI）

```bash
conan create archives/m/mm-common/1.0.8 \
  -pr:h=ohos-local -pr:b=ohos-local \
  --build="mm-common/*"
```

- 源码由 `conandata.yml` 的 url 在 `source()` 阶段下载并做 sha256 校验。
- 构建固定 `-Duse-network=false`：`doctags/libstdc++.tag` 从源码树复制，不访问 gcc.gnu.org。
- 配置期需要 `meson >= 0.62.0` 与 `ninja`（1.0.8 的硬性要求），以及任意可用 C 编译器做一次
  `project()` 探测（本包不编译 C/C++ 代码）。

## 前提

- conan 的 settings 必须认识 `os=OHOS`（OpenHarmonyPCDeveloper 分发的 conan，或
  `~/.conan2/settings_user.yml` 里补 `OHOS:`）。
- profile 里的 `tools.build:compiler_executables` 必须指向设备上真实存在的 `clang`/`clang++`。
- `/tmp` 不可写：记得 `export TMPDIR=$HOME/tmp`（zsh 另加 `TMPPREFIX`）。

## 消费 A：conan 工程（Meson / Autotools 模块）

```bash
conan install --requires=mm-common/1.0.8 -pr ohos-native
```

推荐作为构建期工具消费：

```python
def build_requirements(self):
    self.tool_requires("mm-common/1.0.8")
```

拿到包之后：

```bash
# Meson 模块（glibmm 等）
mm-common-get <buildscript_dir> <doctool_dir>

# Autotools 模块
mm-common-prepare -c -f configure.ac      # 读取 AC_CONFIG_AUX_DIR / MM_CONFIG_DOCTOOL_DIR

# pkg-config 变量（package() 已把 prefix 改写为 ${pcfiledir}/../..）
pkg-config --variable=doctooldir mm-common-util
pkg-config --variable=doxytagfile mm-common-libstdc++
```

`package_info()` 还会把 `<pkg>/share/aclocal` 追加到 `ACLOCAL_PATH`，Autotools 消费方可以直接
`aclocal` 找到 `mm-*.m4`。

## 消费 B：系统级安装（脚本直接可用）

```bash
conan install --requires=mm-common/1.0.8 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

`bin/mm-common-get`、`bin/mm-common-prepare` 会按自身位置找 `../share/mm-common`，
因此搬运到任意前缀仍然可用（这是 0001 补丁的效果）。

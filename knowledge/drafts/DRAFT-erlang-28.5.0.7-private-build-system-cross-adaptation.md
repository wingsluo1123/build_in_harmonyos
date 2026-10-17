# DRAFT-erlang-28.5.0.7: "自研构建体系"型上游的 Conan 交叉适配模式（含 2.29.1 API 三坑）

- 条目主题：上游不是单一 autotools/CMake 工程（手写 `configure` + 递归 `make` + 自研驱动如 `otp_build`）时的配方写法
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：erlang/28.5.0.7；同范式适用于 ocaml/ghc 类自举、vendor 自带 configure 的包
- 互链：`DRAFT-erlang-28.5.0.7-beam-ohos-musl-diagnosis-tree`、`CONFIG-GUESS-BUILD-TYPE-OHOS`

## 判定信号（先判断，再选配方骨架）

1. 根目录 `configure` 是**手写**的（或虽有 autoconf 生成物，但它只负责驱动 `erts`/少数子应用的 configure）；
2. 真正的工作由**递归 make / 自研驱动脚本**完成（`Makefile` 里多层 `$(MAKE)`、`otp_build setup`）；
3. 安装不依赖 `DESTDIR`，而是 `--prefix` + `make install`。

命中 ≥2 条 → **不要**用 `AutotoolsToolchain`（它注入的 `CFLAGS/CPPFLAGS/sysroot` 与上游对
CANONICAL_HOST、`CFLAGS` 自有默认值的假设会互相打架，实测把 erts 的探测搞成了 `__int64` size=0）。

## 配方骨架（实测 rc=0）

```python
def build(self):
    apply_conandata_patches(self)                    # 见坑 1
    configure = ["./configure",
                 "--prefix=%s" % self._staging_prefix(),
                 "--build=aarch64-unknown-linux-ohos",
                 "--host=aarch64-unknown-linux-ohos",
                 "--without-wx", "--without-odbc", "--without-javac",
                 "--with-ssl=%s" % self.dependencies["openssl"].package_folder,
                 "--with-ssl-incl=%s" % self.dependencies["openssl"].package_folder]
    with self._configure_env().vars(self, scope="build").apply():   # 见坑 2/3
        self.run(" ".join(configure), cwd=self.source_folder)
        self.run("make %s" % " ".join(self._make_args()), cwd=self.source_folder)

def package(self):
    with self._configure_env().vars(self, scope="build").apply():
        self.run("make install", cwd=self.source_folder)
    copy(self, "*", src=self._staging_prefix(), dst=self.package_folder)
```

`_configure_env()` 用 `conan.tools.env.Environment` 声明
`CC/CXX/CPPFLAGS/LDFLAGS/CONFIG_SHELL/SHELL/LC_ALL`；`_make_args()` 用 `self.run("make --version")`
探测版本，≥4.4 追加 `--jobserver-style=pipe`。

## Conan 2.29.1 API 三坑（文档/旧经验会踩）

| 坑 | 报错 | 正确写法 |
|---|---|---|
| `apply_conandata_patches` 不接受 `base_path` | `TypeError: ... got an unexpected keyword argument 'base_path'` | `apply_conandata_patches(self)`；补丁路径相对 `export_sources_folder`，应用根是 `source_folder`（`a/`、`b/` 前缀由 patch_ng 自行剥离，strip=0 即可） |
| `self.run(env=...)` 只接受 **env 文件名列表** | `AssertionError: env argument to ConanFile.run() should be a list` | 传 `env=["conanbuild"]`（默认）；要注入自定义变量用 `Environment`，不要传 dict |
| `Environment` 没有 `apply()` | `AttributeError: 'Environment' object has no attribute 'apply'` | `Environment` 只有 `define/vars/...`；上下文管理器在 `EnvVars` 上：`env.vars(self, scope="build").apply()` |

（`Environment.vars(...).apply()` 会把变量写进 `os.environ`，块结束恢复；`self.run` 的子进程继承。）

## 上游"测试驱动"会二次探测宿主

`otp_build tests` / `make release_tests` / `ts:install` 会再次调用 `config.guess` 推导 `TARGET`，
未显式给三元组时报 `Neither TARGET nor OVERRIDE_TARGET can be determined`。两种处理：
显式 `make TARGET=aarch64-unknown-linux-ohos ...`，或按 `CONFIG-GUESS-BUILD-TYPE-OHOS` 策略 B
给 `config.guess` 打 HarmonyOS 识别补丁（更彻底，一次修好所有二次探测点）。

## 验证

- `conan create archives/e/erlang/28.5.0.7 -pr:h/pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` → rc=0，
  test_package 15/15 断言通过。
- 全量本地 wall：9761s（-j8, HMDFS）→ 必须登记 `ci/config/build_timeouts.txt`（默认 3600s 会被 KILL）。

## 关联

`CONFIG-GUESS-BUILD-TYPE-OHOS`（config.guess 三策略）、`DRAFT-erlang-28.5.0.7-beam-ohos-musl-diagnosis-tree`（四面诊断树）。

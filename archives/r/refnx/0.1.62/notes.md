# refnx 0.1.62 适配笔记

## 编译环境
- 构建系统: meson（`meson setup` + `ninja` + `meson install`，Cython 3.3.0 生成 C/C++）
- 编译日期: 2026-10-15
- 编译器: clang / clang++（OHOS SDK `ohos-sdk_26.0.0.18`，target `aarch64-linux-ohos`），
  `Run-time dependency OpenMP found: YES 5.0`
- 目标解释器: CPython 3.12.9（musl，`EXT_SUFFIX = .cpython-312-aarch64-linux-ohos.so`）
- 状态: published（`conan create` 在真机 rc=0，含 test_package 阶段）

## 编译步骤

1. **源码**：官方 PyPI sdist `refnx-0.1.62.tar.gz`
   （sha256 `3e21751662cf675df569ce637c36ae8431cfaf6e08743edeca64b8489972280d`）。
   CI worker 网络策略阻断 `files.pythonhosted.org`，配方使用清华镜像的同一份字节
   （两端下载逐字节比对一致），sha256 由 `conan source` 校验通过。

2. **依赖**：`requires numpy/2.5.2`（C 头 + `numpy/__init__.pxd` + 运行期同一份 numpy）；
   `tool_requires python/3.12.9, meson/1.11.0, ninja/1.12.1, cython/3.3.0`。
   五者全部来自 OHPCD Conan 制品仓。scipy/pandas/orsopy 是运行期依赖，**不在构建图内**
   （见「注意事项」）。

3. **补丁**：无。refnx 的 meson 构建不需要任何 OHOS 适配——版本探测 `tools/gitversion.py`
   读 `pyproject.toml` 而非 git（sdist 中可用），且 4 个 `.pyx` 只 `cimport numpy` / `cython`，
   不存在 sklearn 那种跨三方包声明文件（`.pxd`）要 vendor 的问题。

4. **meson 环境**：`_create_sitecustomize()` 在 `_ohos_shim/` 写 sitecustomize
   （解析 posix_spawn 不搜 PATH 的路径 + 加载前自动签名），`_create_cython_wrapper()`
   写一个绑定目标解释器的 `cython` 包装（绕开制品仓 `bin/cython` 里构建机的绝对 shebang），
   `_create_exe_wrapper()` 供 meson 的 python 探测使用。

5. **configure**（`env_prefix` 把 shim + meson + Cython + numpy 的 site-packages 全塞进
   PYTHONPATH，LD_LIBRARY_PATH 指向 `<pyroot>/lib` 与 SDK `llvm/lib/aarch64-linux-ohos`）：

   ```
   meson setup <build>/builddir <src> --prefix=<package_folder> \
     --buildtype=release --native-file=<shim>/ohos-native.ini
   → Build targets in project: 4
   → Run-time dependency OpenMP found: YES 5.0
   ```

   native file 关键点：`[binaries]` 全指 SDK；`[properties] numpy-include-dir`；
   `[built-in options] c_link_args / cpp_link_args = ['-L<python libdir>', '-lpython3.12']`
   （musl E004 必需）；`[host_machine]` 与 build machine 完全相同（本机编译 + exe_wrapper）。

6. **编译**：`ninja -j1 -C builddir` → `[18/18]`，产出 **4** 个扩展：

   | 扩展 | 语言 | 位置 |
   |---|---|---|
   | `_cutil` | C（Cython） | `refnx/_lib/` |
   | `_creflect` | C++（Cython，调 `src/refcalc.c` + `src/refcaller.cpp`） | `refnx/reflect/` |
   | `_cyreflect` | C++（Cython + **OpenMP**） | `refnx/reflect/` |
   | `_cevent` | C（Cython） | `refnx/reduce/` |

7. **安装 + 签名**：`meson install --no-rebuild`（前缀即 package folder；`--no-rebuild`
   用于规避 E428——conan 的 env wrapper 会重置 PATH，meson 找不到 ninja），随后 `package()`
   对每个 `refnx/**/*.so` 执行 `llvm-objcopy --remove-section .codesign` →
   `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA` → `chmod 755`，
   日志：`refnx: re-signed 4 extension modules`。

8. **本地验证**：`conan create` 与 `conan test` 均 rc=0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 扩展 dlopen 时报 `undefined symbol: PyModuleDef_Init` | musl（E004）不把解释器符号导出给 dlopen 对象，扩展必须自己记录 `DT_NEEDED libpython3.12.so` | meson native file 的 `c/cpp_link_args` 加 `-L<pylib> -lpython3.12`；test_package 静态通道逐扩展断言首个 `DT_NEEDED` 以 `libpython` 开头 |
| 2 | CI 产出的 `.so` 无法 dlopen（E077 未签名） | DevBox 的 lld 自动写 `.codesign` 段，CI worker 的 lld 不写 | `package()` 里对每个 `.so` 先 `--remove-section .codesign` 再 `binary-sign-tool -selfSign`，幂等 |
| 3 | `meson install` 报找不到 ninja | E428：conan env wrapper 重置 PATH | `meson install --no-rebuild`（树刚编译完，无需再触发 ninja 查找） |
| 4 | test_package 用 PATH 上的 `python3` 校验时把 4 个扩展全判成 ABI 不符 | 设备 `/data/service/hnp/bin/python3` 的 `EXT_SUFFIX` 是 `.cpython-312.so`（HNP 自有标签），与产物标签不是同一个 ABI | 显式 `tool_requires python/3.12.9` 并**先验证候选解释器的 EXT_SUFFIX 含 `-linux-ohos`**，再拿它当基线；不满足的候选跳过并记录其真实后缀 |
| 5 | `import refnx.reflect` 报 `No module named 'scipy'` | scipy 是运行期硬依赖，制品仓未发布 | test_package 分三通道：live（有 scipy 等平台 wheel）/ E212 静态 / deps-missing 静态，计数不伪造 |
| 6 | 数据相关用例整体 skip（386 → 约 250） | 上游 conftest 从 github.com 下载 `refnx-testdata`，CI/设备沙箱不可达 | 本地镜像 zip + 一个 12 行 pytest 插件 monkeypatch `urllib.request.urlopen`，使这些用例真正执行 |

## 源码修改

无。`patches/` 为空目录。

## 依赖版本

| 包 | 版本 | 来源 | 用途 |
|---|---|---|---|
| numpy | 2.5.2 | OHPCD Conan 制品仓 | host requires：C 头 + `numpy/__init__.pxd` + 运行期 |
| python | 3.12.9 | OHPCD Conan 制品仓 | tool_requires：构建解释器（`.cpython-312-aarch64-linux-ohos.so`） |
| meson | 1.11.0 | OHPCD Conan 制品仓 | tool_requires |
| ninja | 1.12.1 | OHPCD Conan 制品仓 | tool_requires |
| cython | 3.3.0 | OHPCD Conan 制品仓 | tool_requires |
| scipy | 1.18.1 | 平台 pip 索引 `pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi`（ohos_aarch64 wheel） | 运行期 |
| pandas | 3.0.5 | 同上 | `import refnx.reduce` 需要 |
| orsopy | 1.2.3 | 同上（py2.py3-none-any） | `refnx.dataset` 模块级依赖 |

## 验证结果

**上游全量测试**（对**将要交付的 conan package 目录**直接运行，离线）：

```bash
python3 -m pytest refnx -q -p ohos_testdata \
  --ignore=refnx/reflect/_app/tests/test_app.py --junitxml=upstream-pkg.xml
# 386 passed in 746.46s   (collected 386, failures 0, errors 0, skipped 0)
```

**test_package**（真机，live 通道）：

```bash
# test_ohos_platform.py：6 静态 + 3 运行期
OHOS_PLATFORM_RESULT discovered=9 passed=9 failed=0 runtime=True
# test_refnx.py：真实消费者，公开 API
REFNX_CONSUMER_RESULT discovered=17 passed=17 failed=0
# 配方汇总
HMBS_TEST_PACKAGE_RESULT={"channel":"live","discovered":26,"passedCount":26,"failedCount":0,...}
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | meson + ninja + Cython 手工驱动；OHOS 下重签名 4 个扩展 |
| `conandata.yml` | 源码 URL/sha256（清华镜像，与官方 PyPI 同字节） |
| `test_package/test_refnx.py` | 17 项真实消费者检查（结构树/数值后端交叉验证/拟合/MCMC/持久化） |
| `test_package/test_ohos_platform.py` | 9 项鸿蒙特有检查（6 静态 ELF + 3 运行期） |
| `test_package/MANIFEST.yml` | 上游逐目录测试计数与排除说明 |

## 注意事项

1. **scipy 不是编译依赖**。refnx 的 4 个 `.pyx` 只 `cimport numpy`/`cython`，
   因此既不需要 scipy 的 `.pxd`，也不需要 `-lscipy`。构建图里只放 numpy 就够了。
2. **live 通道依赖 conanrun 的 PYTHONPATH 追加语义**。conan 生成的
   `conanrunenv-*.sh` 末尾是 `${PYTHONPATH:+:$PYTHONPATH}`，因此设备上已有的
   scipy/pandas/orsopy 覆盖层会存活下来，26 项检查才能跑满。CI 的 AppSpawn 沙箱里
   既没有这些 wheel 也不允许 dlopen 用户路径 `.so`，会自动落到 6 项静态通道，
   计数由配方按通道断言（`discovered != expected` 直接报错），不会出现"少跑还报绿"。
3. **`refnx/reflect/_app/tests/test_app.py` 结构上不可运行**：4 个 Qt GUI 测试需要
   `qtpy`，OHOS 平台 pip 索引与 Conan 制品仓均无 Qt 绑定，收集阶段即 1 error。
   已在 `test_package/MANIFEST.yml` 与 `manifest.yaml` 的 `excluded_modules` 中记录
   排除理由与证据命令。
4. **小整数计数陷阱**：`ReflectDataset(np.c_[q, y, err])` 会把二维数组当作"行的元组"，
   静默造出 3 点数据集（症状是任何拟合的 `chi2 ≈ 1e6`），必须传元组
   `ReflectDataset((q, y, err))`。这是上游 API 语义，不是平台差异，但排障时极易误判为
   数值后端出错。
5. **pytest 必须以 `pytest refnx` 的形式在 site-packages 目录内运行**；逐目录分派会破坏
   conftest fixture 与 `resources.files(refnx.reflect.tests)` 的资源解析。
6. **finish 的 G0 clean-verify 是本包唯一一条"假失败"**：`clean_verify.py` 把构建入口硬编码为
   `./configure && make`（autotools 假设），而 refnx 是 **meson-only**（无 `configure` 脚本），
   故 G0 报 `FAILED_STEP: configure` / `./configure: No such file or directory`。该检查不阻塞
   W3（finish 继续执行且 W3 门禁通过），真实构建验证由 `conan create`（rc=0）+ test_package
   26/26 + 上游 386/386 承担。这是工具对非 autotools 配方的结构性局限，非本配方缺陷。
7. **CI 首次构建红在 `ninja: fatal: posix_spawn: Resource temporarily unavailable`**：共享
   worker 上 ninja 默认并发把进程/沙箱资源耗尽（`posix_spawn` EAGAIN），失败发生在**第一个**
   扩展编译前（meson setup 与依赖解析均已成功，elapsed 363 s）。配方已把编译并发固定为
   `ninja -j1`（与仓库通用约定一致）。该签名的判定与处置见既有知识条目
   `DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent`（同类 `can't fork` /
   `Resource temporarily unavailable` 属 worker 环境资源压力，非配方缺陷；策略 2 = 降并发）。
8. **两次远程 CI 红在不同 worker 的不同步骤，均为「创建子进程失败」——环境性，非配方缺陷**：
   - CI-006 / build #93440（commit `51c8a710`）：`meson setup` 成功、依赖解析成功，红在
     `ninja` 阶段 `ninja: fatal: posix_spawn: Resource temporarily unavailable`（EAGAIN）。
   - CI-030 / build #93504（commit `be1bac4d`，相对上一版**只**加了 `ninja -j1` 与文档）：
     红在更早的 `meson setup`——`../src/meson.build:5` 的
     `run_command(['tools/gitversion.py'], check: true)` 返回 status 1。

   对照证据（说明不是脚本/sdist/解释器的问题）：
   | 项 | 本机 | CI-006 | CI-030 |
   |---|---|---|---|
   | `tools/gitversion.py` | 输出 `0.1.62` rc=0 | 通过（已进入编译） | status 1 |
   | conan 解释器 `python/3.12.9` package_id | `6c7db42132821d241106bb3c9ac38ad21bf97eec` | 同 | 同 |
   | 源码 | 同一清华镜像 sdist | 同 | 同 |

   解释器二进制、sdist、命令行逐位一致而结果不同 ⇒ worker 相关。两处失败都落在
   「spawn 一个子进程」，与 CI worker 的 AppSpawn 进程沙箱压力一致（同族签名见
   `DRAFT-11327`）。CI worker 环境本身也在报错（日志中
   `[fail] [Errno 2] No such file or directory: 'curl'`，`AppSpawnCheckUnexpectedExitCall=...`）。
   处置：属 R41 外部/基础设施类失败（同一 commit 换 worker 结果不同），重新触发构建换
   worker 复核，不据此改配方；`-j1` 保留（它确实让 CI-006 越过了原先的 ninja 失败点）。

## 最终状态

- 编译结束：`conan create`（含 test_package 阶段）rc=0
- 上游套件：386/386 通过，0 失败 / 0 错误 / 0 跳过（746.46 s，对交付产物直接运行）
- test_package：26/26 通过（17 真实消费者 + 9 鸿蒙特有）
- 平台合规：4/4 扩展满足 ELF64 aarch64 + `.codesign` + `libpython` DT_NEEDED + musl 无 glibc/BLAS 链接 + ABI 标签匹配
- 知识沉淀：DRAFT-ohpcp-cpython-stdlib-extensions-missing-native-dt-needed、
  DRAFT-ohos-two-cpython-abi-tag-ext-suffix（路径 B）
---

**编译结束**: 2026-10-15 18:26
**最终状态**: published

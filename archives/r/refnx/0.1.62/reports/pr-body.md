- **三方库名称**：refnx
- **上游版本**：0.1.62
- **上游仓库地址**：https://github.com/refnx/refnx
- **适配路径**：路径 B（贡献创新）——随附 2 条平台级知识条目（OHPCD CPython stdlib 扩展缺 DT_NEEDED、OHOS 两套 CPython 的扩展 ABI 标签规则）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 386 | 来源：上游 pytest 套件 `refnx/{_lib,util,dataset,reflect,analysis,reduce}/tests` + `refnx/reflect/_app/tests`，sdist 自带并随 meson install 装入 `site-packages/refnx/**/tests` |
| 集成测试 | 0 | 上游无独立集成测试套件 |
| 其他测试 | 4 | `refnx/reflect/_app/tests/test_app.py`：4 个 Qt GUI 用例（需 `qtpy` + Qt 绑定） |
| **合计** | **390** | 可收集用例；其中 386 个不依赖 Qt，可在 OHOS 上执行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 386 | 不变 | 386/386 通过，**0 失败 / 0 错误 / 0 跳过**（数据依赖用例已通过本地镜像供数真正执行） |
| 集成测试 | 17 | 新增 | `test_package/test_refnx.py`：真实消费者视角，通过公开 API 端到端跑结构建模 → 反射率 → 拟合 → MCMC → 数据集 IO → pickle/ORSO 持久化 |
| 鸿蒙特有测试 | 9 | 新增 | `test_package/test_ohos_platform.py`：6 项静态 ELF/加载契约 + 3 项运行期平台断言 |
| **合计** | **412** | **+22** | 上游可执行用例 386 全绿 + 新增 26 项 |

> 上游 4 个 Qt GUI 用例在 OHOS 上**结构上不可运行**（平台 pip 索引与 Conan 制品仓均未发布 Qt 绑定，
> `qtpy` 无法导入，pytest 在收集阶段即报 1 个 collection error），已在
> `test_package/MANIFEST.yml::excluded_modules` 与 `manifest.yaml` 中记录排除理由与证据命令。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] 是，存在对上游测试用例的修改

上游测试代码零修改、零补丁（`patches/` 为空）。运行时有两点**不改变上游代码**的说明：

1. **排除 1 个文件**：以 `--ignore=refnx/reflect/_app/tests/test_app.py` 排除 4 个 Qt GUI 用例，
   理由见上（缺 Qt 绑定，非平台移植缺陷）。
2. **新增 1 个 pytest 插件供数**：上游 `refnx/conftest.py` 通过 `pooch` 从
   `github.com/refnx/refnx-testdata` 下载测试数据归档，该域名在设备与 CI 沙箱内均不可达，
   **默认会让数据相关用例整体 skip（386 通过 → 约 250 通过 + 约 136 skip）**。
   本次用一个 12 行的插件（`-p ohos_testdata`）monkeypatch `urllib.request.urlopen`，
   把含 `refnx-testdata` 的 URL 重定向到本地镜像 zip，使这些用例**真正执行**——
   因此本 PR 报出的 `386 passed / 0 skipped` 是真实执行的计数，而不是靠跳过换来的通过率。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] 否
- [x] **是**，上游无「OHOS 平台合规性」与「已安装产物消费者视角」的测试，适配后补全

> - **补全的测试范围**：
>   1. **平台加载契约**（鸿蒙特有，9 项）：上游没有任何针对 OHOS 的 ELF/加载断言。新增
>      `test_package/test_ohos_platform.py`，用**纯 stdlib 自行解析 ELF64**（不依赖 `readelf`，
>      因而在拒绝 dlopen 用户路径 `.so` 的 E212 AppSpawn 沙箱内同样可执行），逐一覆盖本配方产出的
>      4 个扩展，并把扩展总数**钉死为 4**（`EXPECTED_EXTENSIONS`，来自 meson 的
>      `Build targets in project: 4`）——移走任一个产物即刻变红，而不是退化成 "3/3 全绿"：
>      aarch64/ELF64 魔数、`.codesign` 段（E077）、`DT_NEEDED libpython3.12.so`（E004）、
>      musl `libc.so` 且无 glibc/BLAS 链接、且各扩展的 `DT_NEEDED` 尾部**精确等于** meson.build
>      声明的契约（C 扩展仅 libc；C++ 扩展加 `libc++_shared.so`；仅 OpenMP 版 `_cyreflect`
>      加 `libomp.so`）、扩展文件名后缀 == 运行解释器的 `EXT_SUFFIX`、包内布局与 meson 生成的
>      `refnx/version.py` 版本号。
>      运行期 3 项（仅需 numpy）：平台字符串/LP64/扩展确从 `.so` 载入、扩展从包目录 dlopen +
>      OHOS 文件系统上 mmap 数组并让打包的 Cython 助手在其上运算（与纯 Python 参考一致）、
>      musl 分配器压力（50 万元素不规则展平）与非连续内存视图。
>   2. **产物消费者集成**（17 项）：`test_package/test_refnx.py`，安装后直接 `import refnx`，
>      数值核心从**四个互相独立的方向**交叉钉死：C（`refcalc.c`，经 `_creflect`）、
>      Cython+OpenMP（`_cyreflect`）、上游纯 Python 译本（`refnx.reflect._reflect`）
>      三者必须互相一致，且都必须复现 sdist 自带、由 Motofit 生成的参考曲线
>      （`theoretical.txt`，500 个 Q 点，相对偏差 < 1e-9）；六个可选后端全部比对；
>      `abeles_vectorised` 批量路径与标量逐条一致；极化核 `gepore` 在零磁化下非自旋翻转道
>      等于非极化核、自旋翻转道为 ~1e-29；`_cyreflect` 的 `threads=0/1/4` 结果**逐位相同**；
>      `CurveFitter.fit` 从 95 Å 起点恢复 100 Å（stderr 0.011）；`emcee` MCMC 后验 100.03±0.01；
>      `Data1D`/`ReflectDataset`/`OrsoDataset` 读写与 `Structure` pickle 往返逐位一致。
> - **补全原因**：上游测试全部面向 glibc/Linux + 从源码树运行，既不覆盖 OHOS 的 ELF 加载契约
>   （签名/DT_NEEDED/ABI 标签），也不覆盖「已安装产物 + 平台解释器」这一真实消费路径。
> - **新增测试文件清单**：
>   1. `archives/r/refnx/0.1.62/test_package/test_refnx.py` — 17 项真实消费者 API 检查（36 条 assert）
>   2. `archives/r/refnx/0.1.62/test_package/test_ohos_platform.py` — 9 项鸿蒙平台检查（32 条 assert，静态组对 4 个扩展逐个展开）
>   3. `archives/r/refnx/0.1.62/test_package/conanfile.py` — 按通道断言用例数（live 26 / 静态 6），计数不匹配即抛错

## 验证结果

- 编译状态：**通过**（`conan create` 含 test_package 阶段 rc=0；`meson setup` → `Build targets in project: 4`、`OpenMP found: YES 5.0` → `ninja [18/18]` → 4 个扩展安装并重新签名）
- 上游测试用例通过率：**386/386（100%）**，0 失败 / 0 错误 / **0 跳过**，746.46 s
  （对**本配方 `conan create` 产出的 package 目录**直接运行，非源码树）
- 新增测试用例通过率：**26/26（100%）**（`test_refnx.py` 17/17 + `test_ohos_platform.py` 9/9）

### 产物与平台合规

| 维度 | 结果 |
|------|------|
| 扩展数量 | 4（`_cutil` / `_creflect` / `_cyreflect` / `_cevent`），全部由 `refnx/**/*.so` 重新签名 |
| ELF 格式 | 4/4 为 ELF64 `EM_AARCH64` |
| 签名（E077） | 4/4 带 `.codesign` 段 |
| 解释器符号（E004） | 4/4 声明 `DT_NEEDED libpython3.12.so*` |
| C 库 | 4/4 仅链 musl `libc.so`，无 `libc.so.6` / `ld-linux*` / glibc-BLAS |
| ABI 标签 | 4/4 后缀 == `.cpython-312-aarch64-linux-ohos.so`（== 运行解释器 `EXT_SUFFIX`） |
| OpenMP | `_cyreflect` 链接 `libomp.so`；单线程 vs 4 线程结果逐位一致 |

## 补充说明

1. **无补丁**：refnx 的 meson 构建不需要任何 OHOS 适配。其版本探测 `tools/gitversion.py`
   读 `pyproject.toml` 而非 git（sdist 中可用），4 个 `.pyx` 只 `cimport numpy`/`cython`，
   不存在跨三方包声明文件需要 vendor 的问题（与 scikit-learn 的 `.pxd` vendor 问题不同）。
2. **scipy 不是编译依赖**：refnx 运行期硬依赖 `numpy>=2.0`/`scipy`/`orsopy`（`import refnx.reduce`
   另需 `pandas`）。构建图内只放制品仓已有的 `numpy/2.5.2`；scipy/pandas/orsopy 未在 OHPCD
   Conan 制品仓发布，由平台 pip 索引 `pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi` 的 OHOS wheel
   提供（`scipy-1.18.1-cp312-cp312-ohos_aarch64.whl` 等）。conan 生成的 `conanrunenv-*.sh`
   末尾追加 `${PYTHONPATH:+:$PYTHONPATH}`，因此设备上既有的覆盖层会存活，live 通道 26 项
   才能跑满；CI 沙箱两样都没有时会自动落到 6 项静态通道，且通道与用例数由配方硬断言。
3. **已知限制**：
   - `refnx/reflect/_app` 的 Qt GUI 在 OHOS 上不可用（无 Qt 绑定），上游 4 个 GUI 用例排除；
   - `refnx.reduce` 的归约算法针对真实束线原始文件，本次通过上游 86 个 reduce 用例验证，
     未额外在真实中子/X 射线数据上做端到端验证。
4. **随附知识条目（路径 B）**：
   - `DRAFT-ohpcp-cpython-stdlib-extensions-missing-native-dt-needed`：OHPCD 的 CPython 发行包把 stdlib 的 `_ssl`/`_sqlite3`/`_ctypes`
     编成**不链原生库**的扩展（`DT_NEEDED` 里没有 libssl/libcrypto/libsqlite3/libffi），
     任何 Python 消费者 `import ssl/sqlite3/ctypes` 都报 symbol not found。这不是单个下游库的
     问题，而是 Python 生态适配的系统性坑；条目给出纯 stdlib 诊断法与三级 workaround。
   - `DRAFT-ohos-two-cpython-abi-tag-ext-suffix`：OHOS 上并存两套 CPython（Conan `python/3.12.9` 的
     `.cpython-312-aarch64-linux-ohos.so` vs 设备 HNP `python3` 的 `.cpython-312.so`）。
     谁驱动构建谁决定扩展的文件名标签；校验通道若拿 PATH 上的解释器当基线，会把正确命名的
     扩展全判成缺陷。协议：先验证候选解释器 `EXT_SUFFIX` 再拿它当基线。
5. **构建期约束（E428）**：conan 的 env wrapper 会重置 PATH，`meson install` 会找不到 ninja，
   故安装阶段使用 `meson install --no-rebuild`。

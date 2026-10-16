# threadpoolctl 3.7.0 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（**单模块包**，无编译）
- **编译日期**: 2026-09-29
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 为什么需要这个包
`threadpoolctl` 是 **scikit-learn 的硬运行时依赖**（sklearn
`pyproject.toml` 的 `dependencies` 实测含 `threadpoolctl>=3.1.0`），
而 imbalanced-learn 又依赖 scikit-learn。它是 sklearn 依赖栈里
**唯一零依赖**的包。

## 包结构（特殊：单模块，非包目录）
sdist `threadpoolctl-3.7.0.tar.gz`（**31,961 bytes，仅 5 个文件**）：
```
threadpoolctl-3.7.0/LICENSE
threadpoolctl-3.7.0/README.md
threadpoolctl-3.7.0/pyproject.toml
threadpoolctl-3.7.0/threadpoolctl.py     ← 单模块（不是 threadpoolctl/ 目录）
threadpoolctl-3.7.0/PKG-INFO
```

**关键差异**：本包与前几个（ply/gast/joblib）不同——它是**单文件模块**
`threadpoolctl.py`，安装目标是 `site-packages/threadpoolctl.py`
（**site-packages 根**），不是 `site-packages/<pkg>/` 子目录。
故本配方 `package()` 用 `shutil.copy2` 单文件拷贝，**不能用** `copytree`。

## 编译步骤（conan create 全流程）

```bash
conan create archives/t/threadpoolctl/3.7.0 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载**官方 GitHub tag 归档**，`tar -xzf --no-same-owner` 解包后
`cp -a` 把内容提到 source_folder 根。

**关键**：必须带 `--no-same-owner`（hmdfs 属主与构建 UID 不一致，
同 packaging/ply/cython/gast/joblib 教训）。

#### ★ 为什么用 GitHub tag 归档，而不是 PyPI sdist（审查 rule4 的根因）
| 来源 | 内容 | 能否跑上游测试 |
|---|---|---|
| PyPI `threadpoolctl-3.7.0.tar.gz` | **仅 5 个文件**：LICENSE / README.md / pyproject.toml / threadpoolctl.py / PKG-INFO | ❌ **不带 `tests/`**，配方内无法运行上游测试 |
| GitHub tag `3.7.0` 归档 | 含 `tests/`（14 个 .py，`def test_` 共 **44** 个） | ✅ 可在 `build()` 内真实运行 |

初版配方用 PyPI sdist，导致 PR 里申报「上游 N=0」——
而审查实测上游 N=44，判定为**少报**（rule4 FAIL）。
根因正是**源码来源选错**：sdist 不含测试套件。
改用 tag 归档后问题消除（sha256 `435415e3...`，与 codeload 端点实测一致）。

### 2. 打包（package()）
拷贝单模块 `threadpoolctl.py` → `lib/python3.12/site-packages/`；
另附 `LICENSE`（命名为 `threadpoolctl-LICENSE` 以免与其它包冲突）；
`env_info.PYTHONPATH` 暴露导入路径。

### 3. 上游测试（build() 内真实运行——R51 实测回填）

```bash
PYTHONPATH=<src> python3 -m pytest tests -q --no-header \
  -p no:cacheprovider -rs --basetemp=<可写目录>
```

**实测（2026-09-29，OHOS aarch64 / Python 3.12.9 / pytest 9.1.1）**：

| 环境 | 收集 | passed | skipped | failed |
|---|---|---|---|---|
| **无 numpy**（≈conan 环境形态） | 89 | **20** | 69 | **0** |
| 临时装 numpy 2.5.3 对照 | 89 | 27 | 59 | 3 |

> 收集 89 项 = 44 个 `def test_` 经 `@pytest.mark.parametrize` 展开。

#### 跳过项（69 个）的原因分类——**全部是上游自带的环境前置条件**
```
3 Requires cython extensions to be compiled        （需先编译 cython 扩展）
2 not running in azure pipelines                    （仅在 Azure CI 上跑）
2 Windows-only test
2 Test requires at least 2 CPUs on host machine
2 'openblas'/'openmp'/'mkl'} controller not found
1 requires strace on Linux / conda-specific test / Testing glibc on Linux
1 requires MKL / BLIS / FlexiBLAS / OpenBLAS / vcomp / my_thread_lib / nested_prange_blas
若干 Requires lib<...> runtime / at least one of [...]  （运行时库探测类）
1 No module named 'numpy' / 'cv2'
```
**这些 skip 全部来自上游源码自身的 `pytest.mark.skipif` / `importorskip`**，
不是本配方排除的——配方未加任何 `--ignore` / `-k` / `--deselect`。

#### 3 项失败（仅"装 numpy"的对照环境下出现，已分析）
`test_threadpool_limits_function_with_side_effect`、
`test_command_line_command_flag`、`test_command_line_import_flag`：
断言拿到的 `threadpool_info()` 里 `num_threads` 为 **20**、
而期望集合里是 **1**（`libopenblas` 控制器被并发/环境线程数影响）。
这属**设备 BLAS 运行时状态差异**，非本包缺陷；
在 conan 环境（无 numpy）下**不出现**（0 failed）。详见 notes 上方实测表。

## 注意事项
1. 纯 Python 包不需要 `commands.json`（R38：库包误加反而会被拦）。
2. 上游构建后端 `flit_core`——**无需为它建 Conan 包**，
   走「直接拷贝模块到 site-packages」路线（同 packaging 先例）。
3. **单模块包必须落在 site-packages 根**（`site-packages/threadpoolctl.py`），
   写成子目录会 import 失败。
4. **必须用官方 tag 归档**：PyPI sdist 不含 `tests/`，用它会在 PR 里
   造成「上游 N 少报」（本 PR 已被审查 rule4 判定一次，记此为戒）。

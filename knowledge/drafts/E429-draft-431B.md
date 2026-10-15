# E429 — 交叉编译 Boost.Python 扩展的单一目标 ABI 契约

## 错误特征

旧式 `setup.py` 常同时使用当前执行构建脚本的 `sys.version_info` 选择
Boost.Python 组件，并让 distutils/setuptools 从该解释器的 `sysconfig`
生成扩展后缀。在交叉编译中，即使已经注入目标 clang、目标 Python
头文件和库，产物仍可能是：

- ELF 架构正确，链接成功；
- 文件名却带构建端 `EXT_SUFFIX`；
- 目标 Python 导入时直接报 `ModuleNotFoundError`，根本没有进入动态加载。

minieigen 0.50.3 的原始 `setup.py` 在构建 Python 3.14 上选出
`boost_python-py314`；目标包则是 Python 3.12，要求
`libboost_python312.so`、`libpython3.12.so.1.0` 和
`.cpython-312-aarch64-linux-ohos.so`。

## 触发条件

- 使用 setup.py/distutils/setuptools 构建 CPython C/C++ 扩展；
- 构建解释器与目标 Python 的小版本、架构或平台标签不同；
- Boost.Python 等库名本身带 CPython ABI token；
- 通过手工补 `-I/-L/-l` 已经让编译链接成功，但没有校验目标导入发现。

## 根因分析

CPython 扩展的可用性不是单一“库名”问题，而是一个四元契约：

1. 目标 `Python.h` 及它定义的 C API；
2. 目标 `libpythonX.Y` 动态依赖；
3. 与同一 `X.Y` 绑定的 Boost.Python 组件；
4. 目标导入器接受的 `SOABI/EXT_SUFFIX`。

这四项必须来自同一个目标 Python 契约。交叉编译时可以不运行目标
Python，而是读取目标 Python 包内 `_sysconfigdata*.py` 的
`build_time_vars`。

## 三臂实证

### Arm A：原始设置

原始 `setup.py` 直接以构建解释器的 `sys.version_info[1]` 拼接
`boost_python-py3X`，并硬编码 `/usr/include/eigen3`。在本次构建端它选出
`boost_python-py314`，与目标 Python 3.12 不同。

未修改源码以 OHOS AArch64 编译器执行原始 `setup.py build_ext --inplace`
真实返回 1，首先报 `Eigen/Core file not found`，证明其硬编码宿主 include
路径在同一交叉环境即不可用。这个失败没有被改写成尚未发生的链接错误；
对原始 `setup()` 元数据的独立捕获则确认下一层仍绑定构建端
`boost_python-py314` 和 `.cpython-314-x86_64-linux-gnu.so`。

### Arm B：错误修复反例

在原始 `setup.py` 上仅注入目标头库、目标链接驱动器并移除不支持 AArch64
的 vendored double-conversion 编译单元，不改 setuptools 的扩展命名逻辑，
宿主 Python 3.14 的 `build_ext --inplace` 会自然生成有效 AArch64 ELF：

```text
minieigen.cpython-314-x86_64-linux-gnu.so
NEEDED: libboost_python312.so, libpython3.12.so.1.0, libdouble-conversion.so
```

目标 Python 3.12 对该自然产物返回：

```text
ModuleNotFoundError: No module named 'minieigen'
```

此外，以最终正确 ELF 复制出的错误/正确后缀两臂保持 SHA256 完全相同，
作为排除编译参数差异的单变量对照。

### Arm C：正确修复

对同一个、SHA256 完全相同的 AArch64 ELF 使用目标
`.cpython-312-aarch64-linux-ohos.so` 后缀，目标 Python 成功导入，
`Vector3(1,2,3).sum()` 返回 `6.0`。这个单变量对照证明 Arm B
的失败发生在导入发现阶段，不是 ELF 架构或 C++ 行为问题。

## 解决方案

1. 从目标 Python 包内唯一 `_sysconfigdata*.py` 读取 `SOABI` 和
   `EXT_SUFFIX`。
2. 从目标 Python 版本派生一个 ABI token，同时选择 `Python.h`、
   `libpythonX.Y.so` 和 `libboost_pythonXY.so`。
3. 构建后联合验证 AArch64 `e_machine`、`PyInit_<module>`、
   `DT_NEEDED`、文件后缀、无 RPATH/RUNPATH 以及目标解释器真实导入。
4. 把“实测构建端 3.14 后缀必须失败、目标后缀必须成功、两臂 SHA256
   必须相同”作为回归对照，避免只验证编译成功。

## 禁止做法

- 不得只把 `boost_python-py314` 改成 `boost_python312`就宣布完成；
- 源码构建不得只在打包阶段改名 `.so`，而不核对其他三项 ABI 组件；
- 不得用构建机 `/usr/include` 或 `sysconfig` 代替目标包元数据。

## 验证

```bash
readelf -h minieigen*.so
readelf -d minieigen*.so
readelf -Ws minieigen*.so | grep PyInit_minieigen
target-python -c 'import minieigen; print(minieigen.__file__)'
```

## 适用边界与查重差异

- `E580-draft-4E17` 处理已预编译 wheel 被 pip 安装后，文件名与当前
  运行解释器接受后缀不同的后处理。本条处理源码交叉构建在链接前的
  四元目标 ABI 契约，不以改名作为修复。
- `E583-draft-4E17` 处理 CI worker 与设备 Python 对已安装扩展的后缀归一化及
  守卫判定。本条区分的是构建解释器与目标解释器，并把
  Boost.Python 组件和 libpython 一并纳入。
- `DRAFT-ohos-python-require-no-host-so` 建议可选加速扩展回退纯 Python；
  minieigen 的 C++ 扩展是主产物，不存在纯 Python 等价回退。
- 本条只约束配方交付的目标 Python 契约，不推断设备上另一套 Python 的
  `EXT_SUFFIX`；当构建端就是目标环境，且解释器、头库与 Boost.Python 均由同一包集提供时，
  本故障不触发。

# minieigen 0.50.3 路径 B 三臂证据

## 主张

交叉编译 CPython/Boost.Python 扩展时，目标 `Python.h`、`libpython`、
Boost.Python 组件和 `EXT_SUFFIX` 必须从同一目标 Python ABI 契约派生。
只修正编译与链接路径，可以得到架构正确却无法被目标导入器发现的 ELF。

## 证据对象

- 上游 `setup.py` SHA256：`1333448bda90128327c4feddca53a2cab33ca52fe108d4dbf8e9d9c8097a6d88`
- 最终 AArch64 扩展 SHA256：`f59c1aaa673b317c4fe61de5a34bb4727de3fa4324c98b5be810bc37ef406f94`
- 构建端：CPython 3.14，`SOABI=cpython-314-x86_64-linux-gnu`
- 目标端：CPython 3.12.9，`SOABI=cpython-312-aarch64-linux-ohos`
- 真机闭环原始日志 SHA256：`60903a25b90ba1b0b085fbf573a73b704e466ad23e750775324df6c0261c81a7`

## Arm A：原始构建脚本

上游在非 Windows 分支直接从 `sys.version_info[1]` 生成
`boost_python-py3X`，并硬编码 `/usr/include/eigen3`。本次构建解释器的实际选择是：

```text
ARM_A_SETUP_CHOICE=boost_python-py314
```

目标依赖仅提供 Python 3.12 契约；原始选择与目标不一致。

在未修改的 0.5.3 源码中将 `CC/CXX/LDSHARED` 指向 OHOS AArch64
工具链并执行 `python3 setup.py build_ext --inplace`，真实返回码为 1：

```text
src/common.hpp:16:9: fatal error: 'Eigen/Core' file not found
error: command '.../clang++' failed with exit code 1
```

这条原始失败首先命中硬编码宿主 include 路径，不能伪称已经走到
Boost.Python 链接阶段。对同一原始脚本拦截 `setup()` 元数据得到：

```text
HOST_EXT_SUFFIX=.cpython-314-x86_64-linux-gnu.so
ARM_A_LIBRARIES=boost_python-py314
ARM_A_INCLUDE_DIRS=src,/usr/include/eigen3,/usr/local/include/eigen3,minieigen
```

仓外保留的完整原始构建日志 SHA256 为
`4d90d2a7ce4f342d054f29fd41d486b990359fd65d08cd1e030462e4289309e4`，
元数据捕获日志 SHA256 为
`c966f6162a45b14c4f4badf0e71d8ace11d9f4a4dc60337f8ad0db7fbe41aaa4`。

## Arm B：只修正目标库的错误修复

在原始 `setup.py` 上只完成交叉编译所必需的局部修复：注入目标 Eigen、
Python 3.12、Boost.Python 与 double-conversion 的头库，移除不支持
AArch64 的 vendored double-conversion 编译单元，并让链接器只搜索目标库。
没有替换 setuptools 的扩展命名逻辑，也没有在构建后重命名产物。宿主
Python 3.14 的 `build_ext --inplace` 因而自然生成：

```text
minieigen.cpython-314-x86_64-linux-gnu.so: ELF 64-bit LSB shared object, ARM aarch64
NEEDED: libboost_python312.so
NEEDED: libpython3.12.so.1.0
NEEDED: libdouble-conversion.so
```

该自然产物 SHA256 为
`42a2c9b94ef29bcb7eccab4c2017e33651a26ebe1f01c4903b26647512f94dd1`；
目标 Python 3.12 导入结果：

```text
ARM_B_RC=1
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'minieigen'
```

仓外自然产出及导入日志 SHA256 为
`5db88cfc88fd57a120f63aebee616713f0f825359a602f3a46161096688b1821`。
这补齐了“局部修复路径自然产生宿主后缀”的证据，不再只依赖人为改名。

该局部修复可按以下约束复现；`TARGET_*` 均来自 Conan 依赖包，不运行目标
Python，也不设置 `ext_suffix`、`SOABI` 或输出文件名：

```python
libraries = ['boost_python312', 'python3.12', 'double-conversion']
library_dirs = [TARGET_BOOST_LIB, TARGET_PYTHON_LIB, TARGET_DOUBLE_CONVERSION_LIB]
include_dirs = [TARGET_EIGEN_INCLUDE, TARGET_BOOST_INCLUDE,
                TARGET_PYTHON_INCLUDE, TARGET_DOUBLE_CONVERSION_INCLUDE]
# 从 Extension.sources 删除 src/double-conversion/*.cc；仍由宿主
# setuptools 的 build_ext 决定 build/lib.* 和扩展文件名。
```

```bash
CC="$TARGET_CC" CXX="$TARGET_CXX" python3 setup.py build_ext --inplace
python3 -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))'
file minieigen*.so
readelf -d minieigen*.so
PYTHONPATH=. $TARGET_RUNNER $TARGET_PYTHON -c 'import minieigen'
```

构建端 distutils 还会注入宿主库搜索目录；实验中的 target-linker 包装只删除
该宿主搜索目录并指定 `TARGET_CXX`，没有覆盖 setuptools 的扩展命名逻辑。
因此文件名是 `build_ext` 的自然输出，不是事后 `cp`/`mv` 的结果。

## Arm C：单一目标 ABI 契约

对字节完全相同的 ELF 使用目标
`.cpython-312-aarch64-linux-ohos.so` 后缀。目标 Python 导入与行为探针：

```text
ARM_C_RC=0
minieigen.cpython-312-aarch64-linux-ohos.so
6.0
```

为排除自然构建中编译参数差异，自动回归另以最终 Arm C ELF 做单变量
发现对照：复制相同字节到宿主后缀和目标后缀目录。两份文件 SHA256 都是
`f59c1aaa673b317c4fe61de5a34bb4727de3fa4324c98b5be810bc37ef406f94`，
唯一变量是文件后缀。

以上 Arm B/Arm C 对照在 HarmonyOS PC 真机上使用随包 `python/3.12.9`
复测：Arm B 返回 1 并报告 `ModuleNotFoundError`，Arm C 成功导入；真机
报告的 `SOABI`、`EXT_SUFFIX`、模块路径与配方读取的目标 sysconfigdata
完全一致。真机同时执行上游 31 项操作和 12 项消费者断言，全部通过。

## 最终联合门禁

```text
ELF machine: AArch64
exported init: PyInit_minieigen
NEEDED: libboost_python312.so
NEEDED: libpython3.12.so.1.0
NEEDED: libdouble-conversion.so
RPATH/RUNPATH: none
.codesign sections: exactly 1
```

`test_package/conanfile.py` 每次构建都会使用 Arm A 实测的
`.cpython-314-x86_64-linux-gnu.so` 重做上述同 ELF 单变量对照，断言外来
后缀被拒绝、目标后缀可导入、两臂 SHA256 相同，并同时检查 ELF、动态
依赖、初始化符号和签名。自然产出实验负责证明错误后缀不是测试人为发明；
自动单变量对照负责把失败精确归因到导入发现阶段。

## 可复现命令

`EXT` 指向打包后的扩展，`TARGET_PYTHON` 指向目标 Python，
`TARGET_RUNNER` 是目标执行前缀：

```bash
mkdir -p probe/arm-b probe/arm-c
cp "$EXT" probe/arm-b/minieigen.cpython-314-x86_64-linux-gnu.so
cp "$EXT" probe/arm-c/minieigen.cpython-312-aarch64-linux-ohos.so

PYTHONPATH=probe/arm-b $TARGET_RUNNER "$TARGET_PYTHON" -c 'import minieigen'
PYTHONPATH=probe/arm-c $TARGET_RUNNER "$TARGET_PYTHON" -c \
  'import minieigen; print(minieigen.__file__); print(minieigen.Vector3(1,2,3).sum())'

sha256sum probe/arm-b/minieigen*.so probe/arm-c/minieigen*.so
```

依赖动态库搜索路径由 Conan 运行环境提供；上述命令不要把个人缓存绝对路径固化进报告或配方。

## 边界

本条契约绑定的是配方交付的 `python/3.12.9` 解释器及其 sysconfigdata，
不声称设备上的任意其他 Python 都接受同一后缀。目标环境原生构建且所有
Python ABI 输入天然同源时，本问题不触发。
预编译 wheel 安装后的扩展后缀归一化属于 `E580-draft-4E17`，不属于本条。

# DRAFT — OHOS conan 构建环境对 Python 包适配的污染链与环境卫生规范

> 拟提升编号：E557（最终编号由知识库主编确认）
> 来源：yte 1.5.4 适配（2026-10-14，鸿蒙 PC 真机）
> 关联：Issue #4008 / PR !15729

## 错误特征

四类报错，前两类指向 buildenv 污染，后两类指向解释器与依赖选择：

```
# 1) conan build()/test() 环境里扩展模块加载被劫持
ModuleNotFoundError: No module named '_posixsubprocess'
File .../subprocess.py, line 106, in <module>
    from _posixsubprocess import fork_exec as _fork_exec

# 2) hnp python3 自带旧 pip 解析不到专用轮子
ERROR: Could not find a version that satisfies the requirement pyyaml (versions: none)

# 3) py3.12 移除 asyncore 后旧版纯 Python 依赖不可用
ModuleNotFoundError: No module named 'asyncore'

# 4) 配方硬编码本机解释器路径，CI worker 上不存在
env: exec /storage/Users/currentUser/usr/local/bin/python3: No such file or directory
```

## 根因分析

1. **LD_LIBRARY_PATH 劫持**：conan OHOS profile 的 `[buildenv]` 把
   `LD_LIBRARY_PATH` 指向 hnp SDK llvm lib（ohos-sdk.../native/llvm/lib）。
   在 conan `build()`/`test()` 的 `self.run` 环境里运行 python3 时，CPython
   扩展模块（_posixsubprocess、math 等）加载被该 lib 目录劫持——同一解释器
   在干净 shell 里完全正常。
2. **hnp python3 的 pip 不认专用轮子**：PATH 上的 hnp python3.12 自带旧 pip，
   无法解析 pypi.cnb.cool 镜像的 `cp312-ohos_aarch64` 专用轮子（报 versions: none）。
3. **py3.12 兼容性**：纯 Python 依赖存在 py3.12 兼容问题（如 plac 1.3.5
   import asyncore，py3.12 已移除该模块），需在满足上游版本约束 (^x.y.z)
   前提下选兼容版本。
4. **硬编码解释器路径**：配方把本机调试用的解释器绝对路径写死进 conanfile，
   CI worker 上不存在该文件，build() 直接 exec 失败（R33：应使用
   `sys.executable`，archives 先例 zipp/decorator/dtfabric/smmap/gitdb 均如此）。

## 解决方案（环境卫生规范）

```python
# (a) 所有 python/pip 调用钉定 conan 运行时解释器，禁止硬编码绝对路径
import sys
py3 = sys.executable          # CI worker 上为 /data/app/bin/python3；
                              # 本机调试时经 conan profile/环境注入完好解释器

# (b) pip/测试命令剥离 conan buildenv 污染，test_package 的 self.run 同样处理
PFX = f'env -u LD_LIBRARY_PATH -u PYTHONHOME -u PYTHONPATH'
self.run(f'{PFX} "{py3}" -m pip install --no-input --no-deps ...')

# (c) 依赖未发布到制品仓时（R36 例外），按 DRAFT-10175 先例 vendoring：
#     python3 -m pip install --no-deps --index-url <pypi.cnb.cool 镜像> \
#       --target <source>/_pydeps <pkgs>；package() 一并拷入 site-packages，
#     并在 notes.md/test-report.md 披露

# (d) 选依赖版本先在真实 python3.12 上 import 验证（asyncore/asynchat 等已移除
#     模块会让旧版纯 Python 依赖直接 import 失败），且必须仍满足上游约束
```

## 验证

```bash
# 命中判定：package_type="python-require" 或配方在 build()/test() 里调 python3
grep -n 'python-require\|self.run.*python3' conanfile.py
# 污染复现：同一解释器干净 shell 正常、conan self.run 报 ModuleNotFoundError 即坑 1

# yte 1.5.4 实证：plac 1.3.5→1.4.3、pyyaml 6.0.2 cp312-ohos 轮子、
# LD_LIBRARY_PATH 剥离后 conan create + test_package 全绿；
# 上游 pytest --co 42/42 collected；CI 修复提交 0732f453（sys.executable 替换硬编码路径）
```

## 推广价值

覆盖所有**纯 Python 包（python-require）**及在 conan `build()`/`test()` 里调用
python3 的配方；含 C 扩展的 Python 包在 OHOS worker 上同样受 LD_LIBRARY_PATH
污染影响。四个坑是环境属性而非单库 bug，任何 Python 包适配都会踩。
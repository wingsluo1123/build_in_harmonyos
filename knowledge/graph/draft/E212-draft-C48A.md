# E212: Python package pip/python3 not found in Conan build environment

> **结构化数据**: [E212-draft-C48A.kv](E212-draft-C48A.kv)
> **严重度**: 🔴 blocking | **分类**: L2 模式经验（构建系统兼容） | **自动修复**: ✅

---

## 错误特征

```
/bin/sh: pip: inaccessible or not found
/bin/sh: python3: inaccessible or not found
ConanException: Error 127 while executing
```

## 根因分析

Conan build environment uses `/bin/sh` to execute commands. On OpenHarmony/OHOS, the system Python is installed at a non-standard path (e.g., `/storage/Users/currentUser/.harmonybrew/opt/python@3.14/bin/python3.14`), and neither `pip` nor `python3` are in the default PATH that `/bin/sh` sees.

When a Conan recipe's `build()` method calls `self.run("pip install ...")` or the test_package's `test()` method calls `self.run("python3 -c ...")`, the shell cannot find these executables, resulting in exit code 127.

## 解决方案

Use `sys.executable` to get the full path to the Python interpreter that's running Conan itself, then use it with `-m pip` for pip commands:

### In conanfile.py build() method:
```python
import sys

def build(self):
    python_exe = sys.executable
    # Install dependencies
    self.run(f'{python_exe} -m pip install --break-system-packages "package>=1.0"')
    # Install the package
    self.run(f'{python_exe} -m pip install --break-system-packages --no-deps --prefix="{self.package_folder}" "{src_dir}"')
```

### In test_package/conanfile.py test() method:
```python
import sys

def test(self):
    if can_run(self):
        python_exe = sys.executable
        self.run(f'{python_exe} -c "import mypackage; print(mypackage.__version__)"')
```

## 涉及软件

All pure Python packages packaged with Conan on OpenHarmony/OHOS platform:
- internetarchive 5.10.1
- Any future Python packages using setuptools/pip

## 验证

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <software> <version>
```

---

*Draft E212 · contributor C48A · 2026-07-01*

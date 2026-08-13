# E257 — Conan out-of-tree 构建时 make check 找不到测试数据文件

## 错误特征
Conan `conan create`（out-of-tree 构建）执行 `make check` 时失败，典型日志：

```
./testcms
lcms: Error #12288; File 'sRGB Color Space Profile.icm' not found
Testing profile decoding (sRGB)make[1]: *** [Makefile:489: check] Error 1
```

## 触发条件
- 构建系统: autotools（其他构建系统同理）
- 阶段: testing（make check）
- 前提: 上游测试程序从 CWD 读取测试数据文件（如 .icm / 数据文件 / 样例输入）

## 根因分析
Conan 的 Autotools helper 默认进行 out-of-tree 构建：configure 与 make 在 `build_folder`
执行，测试程序运行时 CWD 是构建目录。而测试数据文件（如 lcms testcms 所需的
`sRGB Color Space Profile.icm`）位于源码目录 `source_folder/testbed`，不会被复制到
构建目录，导致测试程序打开文件失败。

## 解决方案

### 推荐方案
在 `build()` 中、`make check` 之前，用 `conan.tools.files.copy` 把上游测试数据复制到
构建树对应子目录：

```python
from conan.tools.files import copy
import os

def build(self):
    apply_conandata_patches(self)
    autotools = Autotools(self)
    autotools.configure()
    autotools.make(args=["-j1"])
    # 把测试数据复制到构建树（out-of-tree 下 testcms 从 CWD 读 .icm）
    copy(
        self,
        "*.icm",
        src=os.path.join(self.source_folder, "testbed"),
        dst=os.path.join(self.build_folder, "testbed"),
        keep_path=False,
    )
    autotools.make(target="check", args=["-j1"])
```

### 禁止做法
- ❌ 在 make check 失败后直接把失败项从测试中剔除（掩盖问题）
- ❌ 手动 chmod / 符号链接 hack（每次干净构建都会被清除，不可复现）

## 验证
```bash
grep -n "copy" conanfile.py | grep -i "icm\|testbed"   # 确认复制逻辑存在
conan create . --build=missing                          # make check 通过
```

## 关联条目
- 相关: E011（HMDFS 临时目录权限）、E007（config.guess HarmonyOS 识别）

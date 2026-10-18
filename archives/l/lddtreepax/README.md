# lddtreepax

## 简介

lddtreepax 是 ELF 动态链接依赖树查看工具，为 gentoo/pax-utils 项目的 Python 实现（`lddtree.py`）。
Alpine Linux 将其从 pax-utils 拆出重命名为 `lddtreepax` 的 noarch 子包；核心产物是纯 Python 脚本，
运行时依赖 `elftools`（pyelftools）解析 ELF `.dynamic`/`.dynsym` 并渲染依赖树。

## OHOS 适配

- `build()` 不编译：仅校验交付脚本 `lddtreepax` 存在且可执行；解释器用设备 `python3`（CI worker 保证存在）
- 唯一 conan 依赖 `pyelftools/0.33`（`requires(..., run=True)` 显式声明，原因见 conanfile.py 注释）
- 唯一补丁 `0001-lddtreepax-portable-python3-shebang.patch`：交付脚本 shebang 改 `#!/usr/bin/env python3`
  （上游 `/usr/bin/python` 在 OHOS 不存在）
- 上游冒烟测试 `lddtree-py` 在 OHOS 为空跑（fixture `/bin/bash` 不存在且 `/bin` 只读），真实行为由
  `test_package` 覆盖，详见 `1.3.9/notes.md` R51 申报表

## 依赖

- 运行时：`pyelftools/0.33`（Python 模块 elftools）
- 解释器：`python3`（设备 PATH，非 conan 包依赖）

## 功能验证

```bash
lddtreepax /bin/sh    # 输出 ELF 依赖树（musl 下无法解析的库显示 None，上游平台边界）
```

## 参考

- 上游：https://github.com/gentoo/pax-utils （tag v1.3.9，`lddtree.py`）
- 兄弟包：`archives/p/pax-utils/1.3.10`（scanelf 等 C 工具子包）

# qmake 命令行 `CONFIG-=debug` 覆盖不了 `.pro` 内的 `CONFIG += debug`

> Draft: `DRAFT-XDRAWCHEM-1111-QMAKE-CONFIG-DEBUG-NOT-OVERRIDABLE`
> Stem: `xdrawchem-1.11.1-qmake-config-debug-not-overridable` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-XDRAWCHEM-1111-QMAKE-CONFIG-DEBUG-NOT-OVERRIDABLE
- **严重度**: 3
- **类别**: build-system|qmake|packaging|build-type
- **触发工具**: qmake|conan
- **阶段**: build|packaging

## 现象

conan profile 是 `build_type=Release`，配方也按 expected 传了覆盖参数：

```bash
qmake xdrawchem.pro -spec linux-clang CONFIG+=release CONFIG-=debug PREFIX=...
```

结果 Makefile 里：

```
CFLAGS   = -pipe -g -Wall -Wextra -D_REENTRANT -fPIC $(DEFINES)
CXXFLAGS = -pipe -g -O0 -g3 -Wall -Wextra -D_REENTRANT -fPIC $(DEFINES)
```

产物是 **12 MB**、`-O0` 带全套调试信息、且没有 `-DQT_NO_DEBUG` 的二进制。
**不报错、不使用失败**——只在体积/L5 基线/性能对比上露头。

## 根因

上游 `xdrawchem.pro`：

```qmake
QMAKE_CXXFLAGS_DEBUG += -O0 -g3
CONFIG += debug
```

qmake 对工程文件的求值发生在**命令行变量赋值之后**：`CONFIG` 是累积型变量，
`.pro` 里后写的 `CONFIG += debug` 会把命令行 `CONFIG-=debug` 的效果抵消掉
（实测 `CXXFLAGS` 仍含 `-g -O0 -g3`）。发行版也用同样的结论处理——
Fedora `xdrawchem.spec` 的 Patch0 说明即 "remove -O0 -g3 from CXXFLAGS"。

## 修复

1. **先自证**：跑一次 qmake 后 `grep '^CXXFLAGS' Makefile`，确认不是自己传参写错
   （避免在"应该能覆盖"的假设上反复调参 → R43 调参螺旋）。
2. 用 `refresh-patch` 打补丁**只删一行**：`-CONFIG += debug`。
   保留 `QMAKE_CXXFLAGS_DEBUG += -O0 -g3` 无害——它只在 debug 档生效，Debug 构建仍可用。
3. 配方按 conan `build_type` 驱动配置：

```python
build_config = "CONFIG+=debug" if str(self.settings.build_type) == "Debug" else "CONFIG+=release"
```

补丁前后实测（xdrawchem 1.11.1）：

| | CXXFLAGS | 二进制约 |
|---|---|---|
| 补丁前 | `-pipe -g -O0 -g3 -Wall -Wextra` | 11.9 MB |
| 补丁后 | `-pipe -O2 -Wall -Wextra`（含 `-DQT_NO_DEBUG`） | 明显更小 |

## 反例（禁止）

- 保留 `CONFIG += debug` 只在 `QMAKE_CXXFLAGS` 叠 `-O2`：Qt 头/宏仍按 debug 档
  （`QT_NO_DEBUG` 缺失、断言路径保留），既不是干净 Release 也没拿到 Debug 的好处。
- 引入 `CONFIG += debug_and_release`：会生成 `Makefile.Debug` / `Makefile.Release`
  两套产物，破坏 conan 单档打包语义，L4/L5 产物基线无法判定。

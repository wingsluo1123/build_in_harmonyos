# DRAFT: BC/Belledonne 系包经 Conan CMakeDeps 消费三连坑——版本闸门 AnyNewerVersion + 上游 CMake 辅助宏回退 + 裸 target 名 ALIAS

> 配套条目：`DRAFT-conan-cmakedeps-bc-family-consumption-traps.kv`（本 md 与 kv 成对）
> 状态：pending-editor-review（拟提升编号 E7xx，最终由主编确认）
> 首发实现：ortp 5.2.0，PR #15245 commit `b2ea917714`
> 同场景佐证：bctoolbox/5.3.115 配方自身对 BCUnit 的 `cmake_config_version_compat=AnyNewerVersion` 处理（同根因第 1 坑的先例）

## 1. 错误特征（可机器匹配）

坑一（版本闸门）：

```
CMake Error at CMakeLists.txt:81 (find_package):
  Could not find a configuration file for package "bctoolbox" that is
  compatible with requested version "0.2.0".

  The following configuration files were considered but not accepted:

    .../generators/bctoolbox-config.cmake, version: 5.3.115
```

- error_signature：`Could not find a configuration file for package "bctoolbox".*compatible with requested version`

坑二（辅助宏缺失）：

```
CMake Error at src/CMakeLists.txt:97 (bc_apply_compile_flags):
  Unknown CMake command "bc_apply_compile_flags".
```

- error_signature：`Unknown CMake command "bc_`

坑三（裸 target 名丢 include）：

```
fatal error: 'bctoolbox/logging.h' file not found
#include "bctoolbox/logging.h"
```

（链接行只剩 `-lbctoolbox`，无对应 `-I`；仅当上游写 `target_link_libraries(x bctoolbox)` 裸名时触发。）

## 2. 根因

BC 系项目（ortp/bctoolbox/bellesip/mediastreamer2…）假定"整树同源安装"：上游 `find_package` 拿到的是自家 config 文件，附送版本兼容声明、`bc_*` 辅助宏与 `BCTOOLBOX_*` 变量。Conan CMakeDeps 生成的替代 config **只有导入 target**，三样都不带：

1. 版本兼容策略默认 SameNewerVersion——BC 系上游声明的老版本号（如 ortp 要求 bctoolbox 0.2.0）与 registry 实际版本（5.3.115）跨 major 即拒；
2. `bc_apply_compile_flags` 等宏定义在上游 config 里，CMakeDeps 不复制；
3. 消费方链接裸名 `bctoolbox` 时 CMake 找不到同名 target，退化为 `-lbctoolbox` 标志，`INTERFACE_INCLUDE_DIRECTORIES` 全丢。

## 3. 修法（三个都可配方侧自愈）

```python
# 坑一：generate() 里放宽版本兼容
deps.set_property("bctoolbox", "cmake_config_version_compat", "AnyNewerVersion")
```

```cmake
# 坑二：消费项目补丁——宏缺失时 no-op 回退（STRICT 关闭时旗标列表仅 advisory）
if(NOT COMMAND bc_apply_compile_flags)
	macro(bc_apply_compile_flags)
	endmacro()
endif()
```

```cmake
# 坑三：消费项目补丁——命名空间 target 别名到裸名
if(TARGET bctoolbox::bctoolbox AND NOT TARGET bctoolbox)
	add_library(bctoolbox ALIAS bctoolbox::bctoolbox)
endif()
```

## 4. 佐证

ortp 5.2.0 真机预构建（PR #15245）三轮修前红/修后绿完整证据链：版本闸门（第 1 轮红 → AnyNewerVersion 后过）、宏缺失（第 2 轮红 → 0002 补丁后过）、裸名（第 4-5 轮红 → 0003 补丁后过）；最终 conan create 全链路 exit 0，消费者探针真机运行 PASS。

## 5. 适用范围

所有消费 BC/Belledonne 系包的 Conan 配方（当前已知：osmo 链的 ortp、未来 mediastreamer2/bellesip 系）；同类"上游 config 带私货（宏/变量/兼容声明）"的非 BC 包同样适用坑二/坑三的判定思路。

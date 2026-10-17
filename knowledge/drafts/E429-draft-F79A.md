# E429 — conan 下 CMake 工程的四处目标名/路径不匹配

## 错误特征（同一根因的四种面貌）
```
1) CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
     Compatibility with CMake < 3.5 has been removed from CMake.
2) CMake Error at CMakeLists.txt:32 (target_link_libraries):
     Target "mlc" links to:  libjpeg-turbo::libjpeg-turbo
     but the target was not found.
3) flactomp3.h:4:10: fatal error: 'lame.h' file not found
4) include_directories() 注入了却不生效（放在 add_executable 之后）
```

## 触发条件
- 构建系统: CMake（上游按**系统布局**写，用 `find_package` + `pkg_check_modules`）
- 阶段: configure / build

## 根因分析
1. **CMake ≥4 的策略收紧**：`cmake_minimum_required(VERSION 3.0)` 不再被接受。
2. **目标名风格不一致**：上游写内置模块风格的 `FLAC::FLAC` / `JPEG::JPEG`；conan 的 CMakeDeps
   生成小写目标 `flac::flac` / `libjpeg-turbo::libjpeg-turbo`。
3. **config 文件按包名命名**：conan 产出 `libjpeg-turbo-config.cmake`，所以上游的
   `find_package(JPEG REQUIRED)` 找不到它 → 目标未定义。
4. **include 不通过目标传播**，且部分包在 conan 里是**嵌套头目录**（LAME：`include/lame/lame.h`），
   而上游写 `#include <lame.h>`；同时 `include_directories()` **只对其后创建的 target 生效**。

## 解决方案
```python
# ① 策略下限（不改上游文件）
tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

# ②③ 改写上游的目标名与 find_package 包名
new = new.replace("FLAC::FLAC", "flac::flac") \
         .replace("JPEG::JPEG", "libjpeg-turbo::libjpeg-turbo") \
         .replace("find_package(JPEG REQUIRED)", "find_package(libjpeg-turbo REQUIRED)")

# ④ 在 add_executable() **之前**注入依赖 include，并把嵌套头目录一起带上
inc_dirs = []
for r in ("flac", "lame", "taglib", "libjpeg-turbo"):
    root = <dep(r)>/include
    inc_dirs.append(root)
    if r == "lame":
        inc_dirs.append(root + "/lame")          # ← include/lame/lame.h
new = new.replace("add_executable(mlc", "include_directories(%s)\nadd_executable(mlc" % " ".join(inc_dirs), 1)
```

### 禁止做法
- ❌ 直接把上游 CMakeLists 的 `find_package` 全删掉凑过去（会丢依赖语义）
- ❌ 在文件末尾追加 `include_directories()`（对已创建的 target 无效）
- ❌ 只加 `<dep>/include` 而不处理嵌套头目录（LAME 这类必然失败）

## 验证
```bash
grep -rn 'FLAC::\|JPEG::\|find_package(' CMakeLists.txt
grep -rhoE 'add_library\([A-Za-z0-9_:.+-]+' <build>/generators | sort -u   # 看 conan 真实目标名
ls <dep_lame>/include                                                     # 确认是否嵌套目录
<build产物> --help                                                        # 真跑一次
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它适配条目：上游 CMake 假定系统路径与 CMAKE_SKIP_RPATH /
  平台清单版本 vs 真实上游版本 / 上游无测试时补测并摊开构成 / 判依赖先扣仓库已有 /
  脚本式工具入口打包三坑 / autotools 依赖 include 与 LIBS 顺序 等）

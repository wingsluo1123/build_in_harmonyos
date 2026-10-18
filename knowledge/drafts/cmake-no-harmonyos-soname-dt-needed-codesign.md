# CMake 无 Platform/HarmonyOS 模块：SONAME 缺失与 DT_NEEDED 剥离后 .codesign 重签名

> 对应知识草稿：`knowledge/drafts/cmake-no-harmonyos-soname-dt-needed-codesign.kv`
> 来源：libkdegames 24.12.3 适配（PR !16602，HarmonyOS PC / aarch64）

## 触发场景

- 用 CMake 交叉编译共享库到 OHOS（`CMAKE_SYSTEM_NAME` 无对应平台模块，CMake 反复打印
  `System is unknown to cmake, create: Platform/HarmonyOS`）；
- KDE/ECM 系库尤为典型：`KF6::KDEGames` 等目标链接时**不带 `-Wl,-soname`**；
- 下游（Conan CMakeDeps 生成文件 / test_package 链接命令）拿不到 SONAME，
  只能把发布库当时的**绝对路径**写进自己的 `DT_NEEDED`；
- 另一类触发：对发布库 ELF 做内容级修补（DT_NEEDED 路径剥离、等长字符串替换）
  后直接交付，未重签 `.codesign`。

## 适用库范围

一切 CMake 构建的 OHOS 共享库包；对发布产物做过任何字节级修补的交付流程。
非 KDE 专属——任何「System is unknown to cmake」目标都在风险面内。

## 问题机理（R1-R3）

- **R1 SONAME 缺失**：`Platform/<os>` 模块负责定义
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG`。OHOS 无此模块，变量为空 →
  链接命令没有 `-Wl,-soname` → `readelf -d` 无 `SONAME` 条目；
- **R2 绝对路径烙进下游**：下游链接时解析不到 soname，回退为记录库文件完整路径
  （如 `/storage/Users/.../p/lib/libKDEGames6.so`）进 `DT_NEEDED`，换机/换沙箱即断链；
- **R3 修补毁签名**：HMDFS 在 mmap-exec 装载时校验 ELF `.codesign`。任何内容改写
  （包括「无害」的 DT_NEEDED 路径剥离）都使签名失效 → `dlopen` 报 Permission
  denied（错误形态极具迷惑性，见 DRAFT-HMDFS-SIGNED-ELF-BYTE-REWRITE）。

## 处理策略

1. 配方注入平台缺口补齐参数：
   `-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`
   `-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname`（CXX 同名）
2. `package()` 阶段**只**对 `DT_NEEDED`（tag=1）做路径剥离；
   `DT_SONAME`/`DT_RPATH`/`DT_RUNPATH` 保持原值（改 SONAME 会破坏库查找语义）；
3. 剥离改写后**立即重签 `.codesign`**；签名工具不可用时报错并回滚原文件，
   禁止产出「已改写但未签名」的库。

## 限制

- `-Wl,-soname` 传入 CMake 变量时逗号需转义（`-Wl\,-soname`），否则被当列表切分；
- L2 冒烟检查（`--version`）对纯库包无意义，按设计 skip；
- popup 等纯视觉行为无法无头断言，仍需真机人工确认一次。

## 复现脚本

```sh
# 1) 确认 SONAME 与 DT_NEEDED 形态（无绝对路径、SONAME 正确即达标）
/data/service/hnp/bin/readelf -d <pkg>/lib/libKDEGames6.so | grep -E 'SONAME|NEEDED'

# 2) 确认产物带签名段
/data/service/hnp/bin/readelf -S <发布库> | grep codesign

# 3) 复现「改写未重签」的拒载（对照：原始签名件可 dlopen，翻转一字节即 denied）
python3 - <<'EOF'
import ctypes, sys
f = sys.argv[1]
d = bytearray(open(f, 'rb').read()); d[0x200] ^= 0xFF
open('/tmp/t.so', 'wb').write(bytes(d))
try:
    ctypes.CDLL('/tmp/t.so')
    print('LOADED (unmodified-platform? recheck)')
except OSError as e:
    print('DENIED:', e)
EOF
```

实测矩阵（libkdegames 24.12.3）：剥离 DT_NEEDED + 重签名 → 加载正常、
`SONAME=libKDEGames6.so`、`DT_NEEDED` 无绝对路径（清洗 26 项依赖条目）；
剥离不重签 → `dlopen` Permission denied。

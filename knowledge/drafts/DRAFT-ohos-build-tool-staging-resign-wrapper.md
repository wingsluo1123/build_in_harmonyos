# DRAFT-ohos-build-tool-staging-resign-wrapper：制品仓 ELF 构建期工具在 OHOS 上不可直接执行——staging 拷贝 → DT_NEEDED 改写 → 重签名 → wrapper 后交 find_program

> Contributor: sea_crab | Status: Draft | Updated: 2026-10-15
> Source: wob-0.16 适配（path B 知识库扩展，候选 dca30c0803）
> 对应：`knowledge/drafts/DRAFT-ohos-build-tool-staging-resign-wrapper.kv`

## 问题

OHOS(HMFS) 内核只加载含有效 `.codesign` 签名段的 ELF（机理见 graph
E077）。制品仓 conan 包 `bin/` 里的**原生构建期工具**——wayland-scanner、
glib-compile-resources、gdk-pixbuf-pixdata 这类协议/资源代码生成器——是
构建机上的构建产物，拿到 OHOS 上直接执行有双重障碍：

1. **签名缺失/失效 → EPERM**。失败证据来源分布（如实标注）：
   graph E077 收录的机理与自包含探针
   （`llvm-readelf -S <elf> | grep codesign`）；历史 run 的实测 EPERM
   记录在 archives/w/wdisplays/1.1.3/conanfile.py docstring（"wayland
   包 bin/wayland-scanner 直接执行报 EPERM（HMFS 未签名 ELF 不可执行）"）。
2. **DT_NEEDED 绝对路径残留**。工具编译时链接了构建机缓存里的
   `.so`，NEEDED 记录的是绝对路径而非 soname，loader 不查
   LD_LIBRARY_PATH，换一台机器/一种缓存布局即找不到依赖。本 run 正面
   坐实：`runs/wob-0.16/logs/conan_build_wob_0.16.log:202` 中 staged
   scanner 的 DT_NEEDED 确含
   `/storage/Users/currentUser/.cache/conan2/p/expat9fb72708ad085/p/lib/libexpat.so`
   （旧缓存布局残留），`patchelf --replace-needed … libexpat.so` 实际执行。

上游 meson.build 以 `find_program('wayland-scanner')`（或
`dependency(..., native: true)`）消费这类工具——直接把制品仓包内 bin/
路径交出去必然失败。

## 方案：generate() 内 staging 五步（顺序不可倒）

wob/0.16 配方（candidate dca30c0803）generate() 完整实现，要点：

```python
# ① copy：依赖包 bin/<tool> → 构建目录 conan-native-tools/<tool>.elf
#    （改写不得污染制品仓原件）
shutil.copyfile(os.path.join(dep.package_folder, "bin", "wayland-scanner"), real)

# ② 改写 DT_NEEDED：绝对路径 NEEDED → soname
#    （llvm-readelf -d 正则 NEEDED.*/ 布点，逐条 replace-needed）
for entry in self._absolute_needed(real):        # NEEDED.*\[(/[^\]]+)\]
    self.run(f"{patchelf} --replace-needed {entry} {os.path.basename(entry)} {real}")

# ③ 重签名：remove .codesign → selfSign（顺序不可倒，E077 forbid_1）
self.run(f"{objcopy} --remove-section .codesign {real} 2>/dev/null || true")
self.run(f"{sign_tool} sign -inFile {real} -outFile {real} -selfSign 1")

# ④ wrapper：同名 /bin/sh 脚本，exec 前注入各依赖包 libdir
#    LD_LIBRARY_PATH=<dep1>/lib:<dep2>/lib:… exec <real> "$@"

# ⑤ PATH 置顶：工具目录放构建环境 PATH 最前（meson find_program 命中）
env.prepend_path("PATH", tools_folder)   # 最后 prepend ⇒ 排最前
```

**本 run 端到端实证**（正面必要性证据，`runs/wob-0.16/logs/`）：

| 步骤 | 证据（conan_build_wob_0.16.log） |
|---|---|
| ② 改写真实执行 | :202（`.cache/conan2/.../libexpat.so` → `libexpat.so`） |
| ③ 改写后重签 | :204-206（remove-section + selfSign，"add codesign section success"） |
| ⑤ wrapper 命中 | :230（`Program wayland-scanner found: YES (…/conan-native-tools/wayland-scanner)`） |
| ④ env 生效 | :250-257（staged scanner 完成 8 个协议生成任务，含 staging/fractional-scale） |
| 全链路 | :280-287（上游 meson test color PASS：1/1 OK + Ok:1/Fail:0 + PASSED 汇总）；ci-wob-0.16.log:466-472（test_package A1-A5 全 PASS）、:488-492（L0/L1/L4/L5 pass、L2 skip 门禁结果汇总） |

## 与相邻条目的辨析（避免语义冲突）

**E186（cargo copy→patchelf RUNPATH→sign）场景差异——重点辨析**。
E186 根因句："OHOS musl ldso 使用 namespace 机制解析库路径，
**LD_LIBRARY_PATH 对非标准路径的二进制无效**"（E186.kv:17）。其场景是
**消费端运行期**：ELF 产物已落盘发布、由用户/loader 直接 exec，此时依赖
解析由 musl ldso 的 namespace 机制主导，修法是 patchelf 写 RUNPATH
（`$ORIGIN/../lib`）。本条 staging wrapper 是**构建期子进程**场景：
wrapper 本身是普通 sh 脚本，在 exec 真实 ELF **之前**显式
`export LD_LIBRARY_PATH`，子进程 env 由父 shell fork/exec 传递——
ldso namespace 机制决定的"发布产物加载期"行为管不到这里。本 run
conan_build_wob_0.16.log:250-257（staged scanner 在 wrapper 注入的
LD_LIBRARY_PATH 下完成全部协议生成）即该场景差异的实证。两条目语义
分层不冲突：E186 管"发布的 ELF 产物加载依赖"，本条管"构建期临时工具
的执行环境组装"。

**E537**（Conan cache absolute DT_NEEDED leakage and relocatable
SONAME/link repair）治理**随包分发的产物**：post-build patchelf 改写
shipped artifact 会被 HMDFS 拒绝、其 fallback 改写后未重签执行
Permission denied。本条治理**构建期临时工具**：staged 产物留在构建
目录、不随包发布，恰好绕开 shipped-artifact 禁区；而 E537 的"改写必须
重签"教训（forbid_2）在本条为硬约束（本 run :204-206 顺序执行）。

**E077** 是签名机理底座（ELF 必须含有效 .codesign；patchelf/objcopy
修改使签名失效）；本条是其"构建期工具"场景的工程化封装，把机理落成
可复用的配方 generate() 模式。

**方案空间定位**：

| 条目/草稿 | 方案 | 场景 |
|---|---|---|
| 本条 | staging（copy→改写→重签→wrapper） | 制品仓既有 ELF 工具，构建期消费 |
| DRAFT-ohos-static-tool-bypass-dlopen-limit | 静态重编译工具本体 | 工具源码可得、staging 不可行时的回退（两方案互补非重复） |
| E537 | 链接期 SONAME/RUNPATH 治理 | 随包分发的自有产物 |
| DRAFT-12412-zsa-wally-ohos-lld-placeholder-codesign | 新链接产物 force re-sign | 本地新链产物，非制品仓既有工具 |
| E186 | RUNPATH 运行期修复 | 已发布消费端工具的加载期 |

## 自检（verification）

```
# 探针1：制品仓工具绝对 DT_NEEDED 残留（有输出=不可直接使用）
llvm-readelf -d <wayland-pkg>/bin/wayland-scanner | grep -E 'NEEDED.*\[/'
# 探针2：HMFS 直接执行（历史实测 EPERM，来源 E077/wdisplays docstring）
<wayland-pkg>/bin/wayland-scanner --help
# 探针3/4：staging 五步后，绝对 NEEDED 应消失、工具应可执行
llvm-readelf -d <build>/conan-native-tools/wayland-scanner.elf | grep -E 'NEEDED.*\[/'
<build>/conan-native-tools/wayland-scanner --help
```

## 跨库适用

任何在 OHOS 上以 native 构建工具消费制品仓 ELF 工具的配方均适用：
Wayland 客户端族（wayland-scanner）、GLib/GTK 栈（gnome 模块的
glib-compile-resources 等）、gdk-pixbuf（pixdata 生成器）。仓内同模式
实践 ≥4 处（wdisplays/1.1.3、glade/3.40.0、gtk/3.24.43、
gdk-pixbuf/2.44.6），本 wob/0.16 为独立复验实例（权威 CI 首过绿，
121s，L0-L5 全过）。

## 诚实边界

- 本 run 无 staging 失败日志（主动应用先验、首过绿）：失败证据物理上
  分布于历史来源（E077 机理 + wdisplays 配方 docstring 实测），本 run
  提供的是改写必要性（:202 绝对路径残留实测）与链路有效性
  （:204-206/:230/:250-257）的正面证据。
- 本条只覆盖构建期工具；运行期依赖加载（RUNPATH/LD_LIBRARY_PATH 对
  发布产物）另见 E186/E537，勿混用。

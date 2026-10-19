# asterisk-opus 22.10.1 适配笔记

## 编译环境
- **构建系统**: autotools（Asterisk 全量 configure + make）
- **编译日期**: 2026-10-03
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: HarmonyOS/aarch64 真机构建与 test_package 已通过
- **补丁数量**: 8（沿用 asterisk-speex/pgsql 的 OHOS 移植补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/a/asterisk-opus/22.10.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub codeload tag 下载（downloads.asterisk.org
在 OHOS 沙箱 404，codeload 实测可用）。

### 2. 依赖注入（generate()）
- libedit/libxml2/ncurses/e2fsprogs/jansson/sqlite3 为 Asterisk 主 configure
  与 menuselect 子 configure 的硬要求（沿用 asterisk-pgsql 注入方式）
- `res_format_attr_opus.so` 只使用 Asterisk 内部模块 ABI；实际 Opus 编解码器
  属于独立的 `codec_opus` 模块，因此本包不声明 `libopus` 依赖。

### 3. 构建（build()）
- 全量 configure 后只编译 `res/res_format_attr_opus.so`
- `packaging/menuselect.makeopts` 保留上游生成的模块选择结果
- 只编译 `res/res_format_attr_opus.so`（不依赖 Asterisk 主程序）

### 4. 打包（package()）
- 产物 `res_format_attr_opus.so` 到 `lib/asterisk/modules/`

## 真机验证
- 构建在 WSL worktree `/home/codex-work/asterisk-opus` 中执行，并通过 HDC 连接 HarmonyOS/aarch64 真机。
- `conan create` 完成；产物为 `res_format_attr_opus.so`。
- `test_package` 输出：`OK: res_format_attr_opus.so present + ELF + Asterisk entry data`，退出码 0。

## 依赖
- Asterisk 主 configure 与 menuselect 的硬要求依赖（当前远端预检未发布）
  （libedit/libxml2/ncurses/e2fsprogs/jansson/sqlite3）

## 上游测试（rule 4）
- Asterisk 的 C 测试在 test/ 目录；Opus 格式属性模块**无专属上游测试**
  ——rule 1.2 如实声明"上游无测试"（非跳过）
- 本地验证：已在鸿蒙真机执行 `conan create`
- 适配后：test_package R34 真实产物校验——模块存在 + ELF shared
  object + Asterisk 模块入口字符串

## 已知限制
- 仅打包 Opus 格式属性模块，不包含 Asterisk 主程序或 `codec_opus`

## 2026-10-13：真实核心格式属性消费者

结构校验不能证明模块注册的格式属性接口可用。新增与生产模块同树、同配置编译的 `packaging/res_opus_consumer.c`，只把探针放入 `share/asterisk-opus-tests`，正常模块目录仍只有 `res_format_attr_opus.so`。

`test_package` 将官方已发布的同版本 Asterisk 22.10.1 核心作为本机运行工具（build context）；避免把核心的私有 jansson/libxml2 别名依赖强行覆盖到插件依赖图。已验证 OHOS 6.0/armv8 graph 命中核心缓存二进制。

消费者在临时配置/数据/模块目录启动真实核心，加载安装包模块和专用探针，执行大小写混合 SDP 属性解析、双声道检查、七项生成字段和 SDP 回读。未注册接口、ABI 不一致、启动失败或 60 秒未产出 PASS 均失败。OHOS 在临时副本上签名，不修改依赖缓存；退出时回收进程。不覆盖 codec_opus 编解码、呼叫或真实音频流。

当前修订的 OHOS 功能结果仍待 CI/设备，不能沿用上面的历史结构检查结果作为新功能测试通过证据。

编译前必须真正生成 `menuselect.makeopts`，再生成 `buildopts.h`；只有 configure 的 `makeopts` 不够。已发布核心启用默认 `OPTIONAL_API`，其 ABI 摘要为 `da6642af068ee5e6490c5b1d2cc1d238`；缺失模块选择文件会生成空标志摘要并触发真实核心拒绝加载。保留默认 ABI 标志，不改校验摘要、不绕过加载校验。

## 2026-10-15：导出资源的 source/build 布局修复

CI #89272 仍报 `packaging/menuselect.makedeps` 缺失。之前仅检查 Conan export 缓存，漏掉 `basic_layout(src_folder="src")`：导出资源复制在 base source 根，实际 source_folder 位于其 `src` 子目录；build() 中 export_sources_folder 也不能作为稳定入口。

在 source() 解包后，把两份资源从导出根目录明确复制进 source_folder/packaging，并对缺失立即报错。build() 统一从已经复制的 worktree/packaging 读取 Makefile 资源和测试探针。已使用 SHA256 固定官方归档实际执行 Conan source，再模拟隔离 build-source 复制，逐字节确认两份资源都保留。该验证覆盖源目录与构建目录链路，不再仅凭 export 成功宣称问题解决；新 OHOS 构建/功能结果仍待 CI。

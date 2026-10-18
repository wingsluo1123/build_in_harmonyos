# wlrobs 1.2 — 测试报告（OHOS PC aarch64）

日期：2026-10-17 ｜ profile：ci/conan/profiles/ohos-aarch64（Release/armv8/clang 15）
构建日志：~/tmp/wlrobs-create7.log（conan create RC=0）

## 一、上游测试（R51 三步法）

**清点**：v1.2 源码树顶层 COPYING.md / README.md / inc/ / meson.build /
meson_options.txt / proto/ / src/ —— 无 tests/ 或 test/ 目录；
meson.build 无 test() 声明（仅 1 个 shared_library 目标）；
meson_options.txt 仅 use_scpy / use_dmabuf 两个构建选项。

**实测**：上游无自动化测试，`meson test` 无用例可运行（将报
"no tests defined"）。

| 项 | 值 |
|---|---|
| 测试命令 | meson test（上游未注册任何用例） |
| 用例总数 | 0 |
| 通过 / 失败 / 跳过 | 0 / 0 / 0 |
| 结论 | 上游确无测试入口（非未运行），证据见 test_package/MANIFEST.yml |

## 二、鸿蒙侧新增消费者用例（适配后新增 ≥1，test_package 实测）

### 用例 1：test_link.c — 链接期 ABI 探针

- 命令：`clang test_link.c -o test_link -L<pkg>/lib/obs-plugins -lwlrobs`
- 断言：链接器从打包 libwlrobs.so 解析 OBS 插件契约入口 obs_module_load
- 结果：**PASS**（rc=0，日志 wlrobs-create7.log "Testing the package: Building"）

### 用例 2：test_elf.sh — 运行期 ELF 结构断言（exec 执行）

- 命令：`bash test_elf.sh <pkg>/lib/obs-plugins/libwlrobs.so`
- 断言与结果：
  - PASS: ELF64 AArch64 ET_DYN（aarch64-linux-ohos 交叉编译产物、共享对象）
  - PASS: DT_NEEDED libobs.so + libwayland-client.so（依赖闭包声明正确）
  - PASS: dynsym exports obs_module_load/obs_module_set_pointer（插件 ABI 导出）
  - 收尾输出：WLROBS_ELF_STRUCT_OK

### 汇总

| 项 | 值 |
|---|---|
| test_package 用例 | 2（均在本设备真实执行） |
| 断言总数 | 6 |
| 通过 / 失败 | 6 / 0 |

## 三、平台限制与设计说明

- OHOS PC 对未签名 ELF 的 dlopen/动态映射一律 EACCES（E258/E077）。实测：
  binary-sign-tool 自签名 wlrobs.so 后 dlopen 错误转移至 NEEDED 的
  libwayland-client.so；libobs→ffmpeg 整链（数十个依赖包 .so）整链签名
  不属本包职责。故消费者用例采用「链接期解析 + ELF 结构断言」组合。
- 真实截屏需 wlroots 合成器 Wayland 会话，OHOS PC 无此桌面栈（与
  obs/32.1.2 适配口径一致：库/插件构建并验证 ABI，桌面功能不在平台 surface）。

## 四、conan create 关键证据链

| 阶段 | 结果 | 证据 |
|---|---|---|
| 依赖解析 | obs/32.1.2 + wayland/1.24.0 + expat/2.8.2.1(force) 全部命中制品仓二进制 | wlrobs-create7.log "Already installed" |
| meson configure | wayland-client/libobs 经 fixed_pkgconfig 命中 | meson-log.txt pkg-config rc=0 |
| ninja build | 7/7 目标（3 源文件 + 2 协议胶水 + 链接） | wlrobs-create7.log |
| test_package | 用例 1/2 全过 | 上表 |

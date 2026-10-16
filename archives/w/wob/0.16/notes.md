# wob 0.16 适配笔记

## 编译环境
- 构建系统: meson（上游 meson.build）
- 编译日期: 2026-10-15
- 编译器: clang（OHOS SDK，aarch64-linux-ohos，musl）
- 状态: built（权威 CI ohos-aarch64 全绿：L0/L1/L4/L5 pass，L2 skip 非阻塞）
- 归档: archives/w/wob/0.16
- 权威 CI conan create 全程墙钟约 121s

## 软件说明

wob（wayland overlay bar）是轻量 Wayland overlay 进度条：经 wlr-layer-shell
在屏幕上叠加显示进度/音量/亮度等状态（详见软件级 README.md）。纯 C99 +
Meson，产物为单一可执行文件 bin/wob（application 包）。

## 依赖核验（制品仓已发布版本）

| 依赖 | 上游要求 | 制品仓版本 | 结论 |
|---|---|---|---|
| wayland-client | meson dependency() | wayland/1.22.0 | ✅（transitive_headers/libs） |
| wayland-protocols | >= 1.31 | wayland-protocols/1.36 | ✅（xdg-shell/viewporter/fractional-scale XML） |
| inih | meson dependency('inih') | inih/r62 | ✅（静态库） |
| cmocka | meson dependency('cmocka')（测试） | cmocka/2.0.2 | ✅ |
| librt/libm | meson cc.find_library() | OHOS SDK sysroot（musl stub） | ✅ |

## 编译步骤

```bash
# 权威 CI 同源命令
conan create archives/w/wob/0.16 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部：
1. `source()`：官方 GitHub tar.gz（conandata.yml sha256 校验）
2. `generate()`：VirtualBuildEnv + PkgConfigDeps + wayland-scanner staging
   五步 + wayland-protocols.pc 注入 pkgdatadir + MesonToolchain
   （werror=false 等）+ c_link_args 注入 -Wl,-rpath-link + machine file
   注入 ar/ranlib/pkg-config/ninja 绝对路径
3. `build()`：meson configure + meson build + meson test color（上游测试
   在 build() 内真实运行）
4. `package()`：meson install + LICENSE + OHOS ELF 自签名（bin/）

meson 配置（零 patch，全部配置/生成期注入）：
`-Dseccomp=disabled -Dsystemd-unit-files=disabled -Dman-pages=disabled
-Dtests=enabled -Dwerror=false`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson `find_program('wayland-scanner')` 命中的制品仓 OHOS ELF 直接执行 EPERM | HMFS 只加载含有效 .codesign 签名段的 ELF；制品仓工具是构建机产物 | 配方 generate() 内 staging 五步：拷贝 → patchelf --replace-needed → remove .codesign + selfSign 重签 → wrapper 注入 LD_LIBRARY_PATH → PATH 置顶（wdisplays/1.1.3 同款；见 knowledge/drafts/DRAFT-ohos-build-tool-staging-resign-wrapper） |
| 2 | staged scanner 的 DT_NEEDED 记录构建机 conan 缓存绝对路径（旧缓存布局 libexpat.so 残留） | 工具编译时链接了构建机缓存 .so，NEEDED 记绝对路径而非 soname，loader 不查 LD_LIBRARY_PATH | patchelf --replace-needed <绝对路径> <soname>（conan_build_wob_0.16.log:202 实测；patchelf 破坏签名，必须"改写→重签"顺序） |
| 3 | meson 读 wayland-protocols 的 pkgdatadir 定位协议 XML 取不到 | PkgConfigDeps 生成的 .pc 不含 pkgdatadir 变量 | 配方向生成的 .pc 注入 pkgdatadir=<pkg>/share/wayland-protocols（wdisplays 同款） |
| 4 | 上游 meson.build 默认 werror=true | gcc CI 磨合产物；clang 15 告警面不同 | 配置覆盖 werror=false，不打补丁 |
| 5 | OHOS 无 systemd 用户单元目录；scdoc 为 native 文档工具 | 平台差异 | systemd-unit-files / man-pages 显式 disabled |
| 6 | lld 对 DT_NEEDED 闭包依赖的隐式查找跨 worker 不确定 | lld 定律：用户路径定位失败时静默跳过检查 | c_link_args 显式注入各依赖 libdir 的 -Wl,-rpath-link |

## 上游测试

`meson test color`：test/color_test.c 单一测试程序，5 个 cmocka 用例
（大小写不敏感 / alpha 通道可选 / 非法长度 / 非法字符 / 合法值边界），
纯字符串解析断言，无需 compositor——OHOS 沙箱无 compositor 不影响。
build() 内真实运行，1/1 OK（conan_build_wob_0.16.log:280-287）。

## 鸿蒙特有测试（新增，test_package/src/test_wob_ohos.sh）

5 条 OHOS 专属断言全 PASS：

```
PASS A1: ELF Machine = AArch64
PASS A2: musl interpreter (ld-musl-aarch64)
PASS A3: seccomp=disabled 生效（DT_NEEDED 无 libseccomp）
PASS A4: wob --version 真实执行成功（签名/动态闭包 OK）
PASS A5: wob --help 真实执行成功
```

A4/A5 为真实执行（签名 + 动态链接闭包在 HMFS 上验证，未签名 EPERM 在此
暴露）；加 test_package conanfile.py 的 bin/wob 存在性断言共 6 断言
（ci-wob-0.16.log:466-472）。

## 验证结果（权威 CI / 日志）

- 权威 CI（ci/conan/build_and_test.sh，profile ohos-aarch64）：
  conan create passed，全程墙钟约 121s
- 门禁汇总（ci-wob-0.16.log:488-492）：L0 pass / L1 pass / L2 skip
  （非阻塞：version/help 冒烟在依赖库路径 env 外失败；A4/A5 已在正确
  env 下真实执行成功）/ L4 pass（no patches）/ L5 pass（bin/ has content）
- 上游测试：meson test color 1/1 OK（5 个 cmocka 用例，
  conan_build_wob_0.16.log:280-287）
- test_package：6/6 断言 PASS（含 5 条 OHOS 专属，ci-wob-0.16.log:466-472）

## 注意事项

1. 运行期需要支持 wlr-layer-shell 的 Wayland compositor；OHOS 沙箱无
   compositor，不影响构建与测试，完整显示功能需真实 Wayland 会话。
2. seccomp 仅运行期 self-sandbox（src/pledge_seccomp.c），显式关闭不影响
   功能主体（上游 musl CI 同款先例）。
3. 零 patch：全部适配以配置/生成期注入完成（conandata.yml 无 patches 段，
   L4 no patches 亦据此通过）。

---

**编译结束**: 2026-10-15
**最终状态**: built

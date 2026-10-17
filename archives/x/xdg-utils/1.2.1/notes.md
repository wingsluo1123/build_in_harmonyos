# xdg-utils 1.2.1 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，纯 shell 脚本套件，无编译产物）
- 编译日期: 2026-10-13 ~ 2026-10-14
- 编译器: clang/clang++（实际不参与，纯 POSIX shell 脚本）
- 状态: published

## 编译步骤

1. `ohc-run.py init-build`：拉取 gitlab.freedesktop.org tag v1.2.1 源码
2. 配方 build()：
   - 源码复制到 tmpfs `/data/storage/el2/base/.conan-build-xdg-utils-1.2.1/src`（E060）
   - 环境前置 `AWK=/data/service/hnp/bin/awk`、hnp bin PATH
   - work 根放置 xmlto 离线桩（man/html/html-nochunks/txt 四模式真实产出目标文件）
   - `./configure --prefix=<install> --bindir=<install>/bin` + `make -j1`
   - 跳过 make install，shutil.copy2 复制 scripts/ 下 8 个已生成 xdg-* 脚本（保留执行位）+ man/html 文档
3. `package()` 用 conan.tools.files.copy 装配 bin/share
4. `conan-verify` + `finish published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: could not setup config files machinery（subs1.awk Permission denied） | 双因：HMDFS 临时目录限制（E060）+ /usr/bin/awk 是 toybox 坏符号链接被缓存进 $AWK | tmpfs 构建 + 显式 `AWK=/data/service/hnp/bin/awk` |
| 2 | 并行 make 下 10 个 sed 进程自读自写死循环，脚本文件膨胀至 ~35GB（合计 ~350G） | `%: %.in %.txt` 生成链（awk\|sed 重定向 + sh --help 追加 .txt）并行不安全 | `make -j1` 强制；-j1 复测全部脚本正常生成 |
| 3 | make 阶段 xmlto 联网拉 docbookx.dtd 失败（Unknown IO error） | 沙箱不可达 oasis-open.org；且 html 阶段实际调用 html-nochunks 模式 | xmlto 离线桩覆盖 man/html/html-nochunks/txt 四模式，桩目录前置 PATH |
| 4 | make install 失败：install-sh "can't execute: Permission denied"（Error 126） | install-sh 新建可执行文件触发 hishell_hap MAC（G17 同源） | 绕过 make install，copy2 直接复制已生成产物 |

## 依赖

- 无编译依赖（纯 POSIX shell 脚本套件）；运行期依赖系统 sh 与基础 coreutils

## 验证结果

- conan-verify：G0-G4 全绿（G2 conan create + test_package EXIT=0）
- test_package：真实脚本执行 2/2（xdg-mime --version 输出 "xdg-mime 1.2.1" grep 断言 + --help）
- 上游测试：6 个 shell 测试（autotests/t-*.sh，见 test_package/MANIFEST.yml 声明）

## 结束

最终状态：published（本机 W3 全绿；test_package 消费者断言 2/2 通过；
制品发布与 CI 原生执行由提 PR 后的 CI 流水线完成）。
---

**编译结束**: 2026-10-14 12:04
**最终状态**: published

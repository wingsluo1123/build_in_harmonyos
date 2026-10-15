# theseus 3.3.0 适配笔记

## 软件
THESEUS — 宏分子结构最大似然超叠（ML superposition）与分析，C 语言，
依赖 GNU Scientific Library（GSL）。官方主页 http://www.theseus3d.org/
（Theobald 实验室，Brandeis）。

## 构建系统
纯 GNU make + `make.inc` 平台扩展文件（上游文档明确："Do not modify this
file, modify make.inc instead for platform specific compilation"）。
`make` 依次构建 6 个静态库（libdistfit/libDLTutils/libmsa/libdltmath/
libdssplite/libtheseus）与主程序 `theseus`，链接 `-lgsl -lgslcblas`。

## OHOS 适配
- 上游 make.inc 默认 `ARCH=libtool`、`CC=/usr/bin/gcc`、`OPT` 含
  `-mtune=native`（macOS 默认块），均不可用于 OHOS 交叉编译。
  conanfile build() 按 Conan 解析的工具链与 GSL 依赖路径重新生成 make.inc
  （ar -rvs、clang、gsl 的 -I/-L/-Wl,-rpath）。
- 移植 2 个上游社区（Debian）修复补丁：缓冲区尺寸（gcc-7 检查，bug
  #853681）与 strncpy/digit 缓冲溢出（bug #908459）。未启用 -Werror，
  编译器选项类补丁（30_fix_gcc_options、gcc-16）不需要。
- 1 个大小写兼容补丁：NWfill.c 引用小写 `error.h`（头文件实为 Error.h，
  macOS 大小写不敏感能过、Linux/OHOS 直接 fatal error）——全量扫描确认
  这是唯一的大小写不匹配（bimultinom.h/dmalloc.h/theseus_sa.h 三处引用
  均在注释或 #ifdef DMALLOC 内不激活）。
- 不打包 `theseus_align` 包装脚本：它依赖外部序列比对程序
  （MUSCLE/MAFFT/CLUSTALW 等），OHOS 上无这些工具，装了也不能跑。

## 源码溯源（重要）
官方托管站 theseus3d.org / theobald.brandeis.edu 在 2026-10-13 从本机
（Windows 与 WSL 两条网络路径）均不可达：theobald.brandeis.edu DNS 解析
失败，www.theseus3d.org（129.64.68.88）TCP 连接超时。conandata.yml 采用
Debian 源池托管的同一份上游原始发布文件 `theseus_3.3.0.orig.tar.gz`
（HTTP 200，22548124 字节），sha256=3cfd4f906717f9cb8e77f689fc97059b32df355c0696077034ea99a485e3f2fe
与三处独立记录一致：MacPorts 2020 年从官网记录的校验和、Debian GPG 签名
的 .dsc、本机两次实际下载（deb.debian.org 池原件 + TUNA 池镜像）逐字节
比对。池源站 deb.debian.org 在本环境间歇性卡顿（20s 超时，期间 conan
源码下载阶段空转 7 分钟），故 conandata 取 TUNA 清华镜像的同池文件
（sha256 相同，国内 CI worker 走此链路更快）。若官方站恢复，建议换回
官网 URL（同文件，sha256 不变）。

## 测试
上游无测试套件（Debian 用 autopkgtest 冒烟）。test_package 采用上游
examples/README 的官方演示命令 `theseus 1s40.pdb`（10 模型 NMR 家族，
2.8MB，随 test_package 分发），断言：退出码 0 + 输出含真实计算结果
（Maximum Likelihood <sigma> / Marginal Log Likelihood）。

## 2026-10-14 CI 门禁整改

CI 判定为「需改代码」后的整改记录（只记事实与构建号）：

CI build #90812 报 `[fail] L0k: CLI tool detected but commands.json missing (R38)`；补 `archives/t/commands.json`。

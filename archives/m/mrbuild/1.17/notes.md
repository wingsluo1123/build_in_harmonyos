# mrbuild 1.17 适配笔记

## 软件是什么
mrbuild（https://github.com/dkogan/mrbuild，MIT，Caltech / Daniel Kogan）是一套 GNU Makefile 构建样板：
Makefile.common.header / Makefile.common.footer 两个模板 + bin/make-pod-from-help（perl 脚本，把命令的 --help 输出转成 POD）+ README.org + build_examples/。
v1.17 tarball 共 6 个文件，**纯文件分发包，无任何编译步骤**。

## 上游来源
- URL: https://github.com/dkogan/mrbuild/archive/refs/tags/v1.17.tar.gz（HTTP 200）
- sha256: d577e2cc4a2bc598ca7dd78235b7f9fea4bbd6099926b78f26ef18dbb4c94ceb
- 依赖：无 conan 依赖；make-pod-from-help 运行期需要 perl（系统工具，测试里按存在与否自适应）

## 配方设计
- package_type=application；build() 打补丁 + 载荷完整性自检；package() 安装：
  - Makefile.common.{header,footer} → include/mrbuild/
  - make-pod-from-help → bin/（0755）
  - README.org、build_examples/ → share/mrbuild/
- package_info 提供 MRBUILD_DIR / MRBUILD_BINDIR（buildenv+runenv）；
  消费者 Makefile 直接 include $(MRBUILD_DIR)/Makefile.common.{header,footer}。

## 适配要点（两个坑）
1. **GNU make 4.3 引号 include 缺陷**：工程 Makefile 里第二条带双引号的 include 不被剥引号，
   报 "No such file or directory"（已用最小工程复现）。模板 README 示例本就无引号 →
   test_package/project/Makefile 用无引号 include 路径。
2. **--default-symver 是 GNU ld 扩展**：footer 在非 Darwin 平台给 .so 链接硬编码 -Wl,--default-symver，
   LLVM lld（OHOS NDK，ld.lld-15）直接报 unknown argument，链接必挂。
   补丁 0001 增加一次性链接器探测（SYMVER_PROBE，探测文件进 EXTRA_CLEAN）：
   链接器接受该 flag 才保留 → GNU ld 环境行为与上游完全一致，LLVM lld（OHOS）自动降级。

## 本地验证（WSL ext4 原生盘，2026-10-13）
    conan create archives/m/mrbuild/1.17 --name=mrbuild --version=1.17 \
      -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
→ PASS（日志 /root/ohpcd-work/mrbuild-create3.log）。test_package 真实执行：
- 用安装后的模板交叉构建迷你工程 libmrtest（lib.c → .so 符号链接链）+ run（run.c → 可执行），
  工具链 /opt/lpk-fixed/clang++ 15，target aarch64-linux-ohos；
- 11 条无条件断言：载荷文件/可执行位/shebang、.so.0.1 存在、libmrtest.so 与 .so.0 符号链接、
  两个产物的 ELF magic；perl 存在时另加 2 条动态断言（make-pod-from-help 真实运行并断言其
  缺参报错契约 "Need exactly one argument" / "Usage:"）。

## 待办
- 平台 CI 首跑待观察；若设备侧 lld 接受 --default-symver，探测会自动保留该 flag，无需改码。

## 路径例外说明（需平台知悉）
- 门禁 L0k(R38) 为 **fail 级**（非 ARCHIVE-SPEC 所述 warn 级）：产物含可执行文件时**必须**有
  软件级 commands.json → 本 PR 因此包含 `archives/m/mrbuild/commands.json`（软件级元数据，
  属本任务包自身，非其他包/框架文件）。这是 CI 可绿的必要条件，特此在 PR 正文中一并声明。

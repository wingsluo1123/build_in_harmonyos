# patches

U-Boot 2026.07 适配共 15 个补丁，全部在 conandata.yml 的
`patches."2026.07"` 列表中登记（按序 apply）。

（原 0014「headless 视频存根」与 0016「非 SDL 构建 usbkbd stdin 门控」
两条补丁已随 sdl2 制品仓依赖接入删除：sandbox 直接构建上游原生 SDL
驱动——conanfile.py 的 requirements()/build() 以 sdl2/2.30.10 的三件套
接线让 HOST_HAS_SDL 探测命中，VIDEO_SANDBOX_SDL 测试面（video/cedit/
expo）全量回归，两条补丁的前提（OHOS 无 SDL2）不再成立。）

- `0001-outputmakefile-source-link-fallback.patch`（portability）：
  HMDFS/OHOS 全域禁 symlink，O= 分离构建的 source 链接创建失败时物化
  为路径文件（该链接无任何构建消费者，仅便利入口）。
- `0002-kbuild-script-exec-via-shell.patch`（portability）：
  OHOS 内核无脚本 execve（binfmt_script 缺失，直接 exec 一律
  EACCES rc=126），Kbuild/Kconfig 直接 exec 的辅助脚本
  （gcc/clang-version.sh、check-of.sh、check-local-export）改经
  sh/$(CONFIG_SHELL) 解释执行，覆盖 Kconfig $(shell,) 解析期与
  make 配方执行期两条路径；check-local-export 是 bash 脚本（shopt）
  且上游裸 exec，配方以 CONFIG_SHELL=bash（Kbuild 标准覆盖位，
  设备 /bin/sh 无 shopt、bash 在 HNP 工具链 PATH）提供 POSIX 超集
  解释器。
- `0003-binman-stamp-python-enable-guard.patch`（portability）：
  NO_PYTHON=1 模式下 .binman_stamp 不再调用 binman（PYTHON_ENABLE 门）；
  OHOS python 环境无 SWIG/setuptools 无法构建 pylibfdt，而 sandbox.dts
  的 binman 节点为空（构建期 binman 为 no-op），跳过不改动任何产物。
- `0004-tools-version-h-for-host-tools.patch`（portability）：
  host 工具以尖括号包含 <version.h>，UBOOTINCLUDE 被 tools/Makefile
  降级为 -idirafter（系统头之后才搜索）；OHOS SDK sysroot 自带
  version.h 遮蔽 u-boot shim 头（PLAIN_VERSION 未定义编译失败）。常规
  tools 目标也依赖上游已有的 tools/version.h 拷贝规则，使
  objtree/tools/version.h 进入 -I 路径（先于系统目录），与
  envtools/tools-only 目标行为一致。
- `0005-image-host-fit-check-sign-tools-gate.patch`（bugfix）：
  上游 TOOLS_LIBCRYPTO=n（无 OpenSSL 构建机文档化模式）+ FIT_SIGNATURE=y
  组合无法构建的修复之一：image-host.c 中 fit_check_sign() 的守卫用了
  裸 #ifdef CONFIG_FIT_SIGNATURE（目标符号），未走 include/linux/kconfig.h
  的 USE_HOSTCC 重映射，导致 host 工具在无 OpenSSL 时仍编译出引用
  TOOLS_LIBCRYPTO 门控对象的代码；改为与文件内其余守卫一致的
  CONFIG_IS_ENABLED(FIT_SIGNATURE)（host 构建解析为
  CONFIG_TOOLS_FIT_SIGNATURE）。
- `0006-fit-check-sign-gated-by-tools-fit-signature.patch`（bugfix）：
  修复之二：fit_check_sign 工具的启用条件从 CONFIG_FIT_SIGNATURE
  （目标符号）改为 CONFIG_TOOLS_FIT_SIGNATURE（宿主侧签名栈开关，
  depends on TOOLS_LIBCRYPTO），与 FIT_SIG_OBJS 等签名对象的
  TOOLS_LIBCRYPTO 门控对齐，避免链接到不存在的签名对象。
- `0007-fit-cipher-host-gate-via-tools-symbol.patch`（bugfix）：
  修复之三：include/image.h 中 host 加密能力门用了裸
  #if defined(CONFIG_FIT_CIPHER)（目标符号），host 工具编译包含共享的
  generated/autoconf.h（目标侧 FIT_CIPHER=y 时必然定义）→ 无 OpenSSL
  设备上 include <openssl/evp.h> 直接炸；改为
  CONFIG_IS_ENABLED(FIT_CIPHER)（host 构建经 USE_HOSTCC 重映射解析为
  新增的 CONFIG_TOOLS_FIT_CIPHER，depends on TOOLS_LIBCRYPTO），有
  OpenSSL 时能力保留、无 OpenSSL 时正确回落。
- `0008-sandbox-syshdrs-wchar-musl.patch`（portability）：
  arch/sandbox/cpu 的 CFLAGS_USE_SYSHDRS 文件（eth-raw-os.o/initjmp.o/
  os.o/sdl.o）以系统头构建：上游 syshdrs_rule 去掉 -nostdinc 并把 -I
  转 -idirafter（libc 头优先），但保留 -fshort-wchar。musl
  <bits/alltypes.h> 硬编码 typedef unsigned wchar_t（aarch64 32-bit），
  与 clang 在 -fshort-wchar 下的 __WCHAR_TYPE__ typedef（16-bit）重定义
  冲突（真机 initjmp.o 实证：alltypes.h:15 vs 资源目录 stddef.h:74）。
  上游已为 sdl.o 打同款补丁（filter-out -fshort-wchar，注释明言
  musl），本补丁把该覆盖扩展到其余三个文件：这些文件零宽字符 API
  使用，去掉旗标后 wchar_t 交由 C 库定义，与 sdl.o 先例一致，
  glibc 平台行为不变。
- `0009-capsule-esl-gen-via-python.patch`（portability）：
  lib/efi_loader 的 capsule_esl_file 生成规则硬编码调用 efitools 的
  外部 C 工具 `cert-to-efi-sig-list`（上游 CI 以 apt 安装 efitools；
  OHOS 工具链既无该命令也无 OpenSSL 开发头可自行构建 → Error 127）。
  本补丁随源码附上该工具的忠实 Python 移植
  `scripts/cert-to-efi-sig-list.py`（纯标准库：PEM 证书体 base64 解码
  即 i2d_X509 的 DER 字节，按 UEFI 规范包装 EFI_SIGNATURE_LIST /
  EFI_SIGNATURE_DATA —— SignatureType=EFI_CERT_X509_GUID、
  SignatureHeaderSize=0、SignatureOwner 全零，与上游调用参数一致），
  并把生成规则改为 `python3 $(srctree)/scripts/cert-to-efi-sig-list.py`。
  本地已用 `openssl x509 -outform DER` 交叉验证：移植输出与
  i2d_X509 字节级一致（沙箱测试证书 787 字节 DER）。由此
  CONFIG_EFI_CAPSULE_AUTHENTICATE=y 的 EFI 胶囊认证自测
  （test/lib/efi_loader）完整保留，无需关闭任何测试面。
- `0010-dhcpv6-ethaddr-compound-literal.patch`（portability）：
  net/dhcpv6.c:35 的静态初始化器 `IPV6_ALL_NODE_ETH_ADDR(dhcp_mcast_ip6)`
  对 const 限定全局变量做成员下标访问。GCC 作为扩展接受 const 全局
  对象为常量表达式，clang 严格按 C99 6.6 拒绝（真机 clang 15.0.4
  实证 `initializer element is not a compile-time constant`；设备 clang
  最小复现双向验证：左值形式报错、复合字面量形式通过）。修复：改用
  同一初始化器的复合字面量 `(struct in6_addr)DHCP6_MULTICAST_ADDR`——
  C99 文件作用域复合字面量有静态存储期，其常量下标成员访问是标准
  常量表达式；字节值与原形式完全相同（同一宏展开）。`dhcp_mcast_ip6`
  全局变量保留（dhcpv6.c:207/257 仍以值使用）。
- `0011-keep-syms-lto-script-via-shell.patch`（portability）：
  CONFIG_LTO=y（sandbox 经 arch/Kconfig `imply LTO` 默认开启——上游
  默认构建形态，defconfig 无字面量不等于关闭，Kconfig 的 imply/default/
  select 都会在 syncconfig 生效）下，顶层 Makefile 的 keep-syms-lto.c
  生成规则直接 exec `scripts/gen_ll_addressable_symbols.sh`（生成链接器
  列表符号的 __ADDRESSABLE 引用、防 LTO 优化消符号）——OHOS 内核无
  脚本 execve，真机 make[1] Error 126 实证，与 0002 同族；改为
  `$(CONFIG_SHELL)` 前缀经 bash 解释执行。配套配方层
  `LTO_FINAL_LDFLAGS=-fuse-ld=lld`（仅 OHOS）：clang -flto 链接需
  LLVMgold 插件而设备无（实测），ld.lld 在工具链 PATH（实测）；
  LTO_FINAL_LDFLAGS 是命令行覆盖位（Makefile 内 := 置空后 += -flto
  附加到命令行值），仅链接 cmd_u-boot__ 使用，qemu_arm64 无 LTO
  不受影响。
- `0012-ldflags-no-warn-rwx-guard-for-lld.patch`（portability）：
  KBUILD_LDFLAGS 的 `--no-warn-rwx-segments` 是 GNU ld 的警告抑制
  旗标（bfd 2.39+；上游以 ld-option 对 $(LD)=GNU ld 探测通过后
  加入），lld 无此旗标且硬报 unknown argument——真机 lld 链接
  u-boot 目标实证（`ld.lld: error: unknown argument`）。探测用
  链接器与实际链接器错配的典型：ld-option 探 GNU ld，实际链接经
  配方层 `-fuse-ld=lld` 由 lld 执行。修复：仅当 LTO_FINAL_LDFLAGS
  携带 `-fuse-ld=lld`（OHOS 分支）时跳过该探测，其余环境（上游
  gcc、CI clang+GNU ld）保持原样；EFI 链接的 KBUILD_EFILDFLAGS
  同名探测走 $(LD) 不受影响、未修改。跳过后 OHOS 上失去的仅是
  bfd 警告抑制（lld 本不产生该警告），无功能差异。
- `0013-create-symlink-cp-fallback.patch`（portability）：
  scripts/Makefile.autoconf:136 的 create_symlink 规则（CONFIG_CREATE_
  ARCH_SYMLINK，arm/arm64 架构专属，sandbox 不触发故前 12 补丁无感）
  用 `ln -fsn` 建立 asm/arch 源码树链接——OHOS 全域禁 symlink（EPERM）
  → include/config.h 依赖链断 → auto.conf 缺失连锁（真机 qemu_arm64
  首建实证）。修复：`ln -fsn` 失败即回退 `cp -r`，但回退必须对齐 ln
  的悬空语义——上游 `ln -fsn` 对缺失源静默建悬空链接（无害：无
  `<asm/arch/*>` 消费者），`cp -r` 对缺失源却是硬错误，而
  qemu_arm64 的 dest=arch-armv8 恰在上游源码树不存在（arch-armv7/
  arch-qemu-sbsa 有、armv8 无，本地+真机双实证）；故 cp 前加
  `elif [ -e 源 ]` 存在性门，缺失即跳过（与悬空链接等价）。O= 与
  in-srctree 两分支同款修复。
- `0015-sandbox-nand-tmpdir.patch`（portability）：
  sandbox NAND 驱动（drivers/mtd/nand/raw/sand_nand.c）经 os_mktemp
  在硬编码路径 /tmp/u-boot.nand<N>.XXXXXX 创建后备文件；OHOS /tmp
  只读 → os_mktemp EROFS，probe 整体失败（真机实证
  board_nand_init() -30，NAND 容量退化 0 MiB），依赖 UCLASS_MTD 的
  测试面（test/dm/nand.c、bootstd 等）随之失去设备。修复：
  sand_nand.c 改读宿主 TMPDIR 环境变量（测试环境已将其导出到
  可写目录，未设置回退 /tmp）；固定 30 字节栈缓冲改按
  strlen(tmpdir)+40 动态分配（真机
  TMPDIR 路径远超 30 字节），malloc 失败 -ENOMEM 走既有 err_chip
  清理、成功路径 free。因上游 sandbox 并无读取宿主环境变量的接口
  （include/os.h/arch/sandbox/cpu/os.c 均无 os_getenv），补丁一并
  在 os.c 新增直通宿主 getenv() 的实现、include/os.h 补声明——
  缺之 sand_nand.c 引用即编译失败。Linux/CI（TMPDIR 未设置）行为
  与上游逐字节一致；真机 NAND 恢复 4100 MiB 枚举。
- `0017-expo-textline-cursor-at-text-end.patch`（bugfix）：
  expo 文本行（scene_textline）打开态渲染的光标位置。SDL 门控测试面
  接入后暴露 cedit_render_lineedit 失败（16 项中最后一项）：
  test/boot/cedit.c:413 断言既存文本 my-machine 打开渲染帧的 bz2
  压缩长度 = 5283——该帧内光标画在文本末尾，测试引入提交 c43791c4
  的提交信息亦明言 The cursor should start at the end（常量自此在
  各发行标签间未变）。v2026.07 的 scene_textline_render_deps 打开
  分支先执行 `vidconsole_entry_restore(cons, &scn->entry_save)`，
  把控制台状态回卷到 scene_textline_open 时刻的存档（set_cursor_pos
  已把笔位钉在字段起点）→ `vidconsole_set_cursor_visible` 经 xcur
  分支把光标画在字段起点（帧长 5270）≠ 烘焙值。修复：该处改调
  `vidconsole_entry_start()`（清位置历史、不回卷笔位），光标回归
  刚绘完文本的实时笔位＝文本末尾，与烘焙帧逐字节一致。逐键编辑
  路径 scene_textline_send_key 的 entry_restore/entry_save 配对
  保持原样；真机验证：cedit_render_lineedit 四帧
  5336/5363/5283/5170 全中、0 失败，cedit_render 12 帧逐字节不变、
  空场帧 4851 不变；上游测试文件零修改（恢复上游行为语义，而非
  改测试常量）。

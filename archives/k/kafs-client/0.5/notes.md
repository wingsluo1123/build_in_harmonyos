# kafs-client 0.5 适配笔记

## 上游信息

- 名称：kafs-client 0.5（kAFS 用户态客户端工具）
- 主页：https://www.infradead.org/~dhowells/kafs/
- git：http://git.infradead.org/users/dhowells/kafs-client.git（Anubis 保护，本机无法拉取）
- 源码包：https://archive.ubuntu.com/ubuntu/pool/universe/k/kafs-client/kafs-client_0.5.orig.tar.gz
- sha256：561b6416f8f7234ddc1e66d8e479d96625c1655463365ea0f954e469ba8aa051（大小 54787，45 文件）
- 许可证：GPL-2.0-or-later（LICENCE.GPL）
- 构建系统：纯 Makefile（顶层 Makefile + src/Makefile + src/Makefile.config + src/version.lds）

## 产物

- 库：libkafs_client.so.0.1（含 SONAME libkafs_client.so.0、开发链接 libkafs_client.so）
- 头文件：include/kafs/cellserv.h、profile.h、reporting.h
- 工具：bin/aklog-kafs、bin/kafs-check-config、bin/kafs-preload、bin/kafs-dns
- 本配方为 library 包（cpp_info.libs=["kafs_client"]，bindirs=["bin"]，system_libs=["resolv"]）

## 依赖

- krb5/1.22.1（aklog-kafs 需 krb5/krb5.h，仓库已发布）
- libkeyutils/1.6.3（aklog-kafs、kafs-dns 需 keyutils.h，仓库已发布）
- 系统 libresolv（-lresolv，src/Makefile 显式链接）
- openssl 在 0.4 后已不再使用（改走 AF_ALG，见 spec changelog），故不依赖

## OHOS 适配点

1. 顶层 Makefile 与 src/Makefile.config 以 `file /usr/bin/make | sed` 探测 32/64-bit 并追加 -m32/-m64（x86 专属，clang aarch64 拒收）。配方在每次 make 调用传入 `BUILDFOR=` 中和该探测。
2. src/Makefile.config 以 `ldd /usr/bin/make | grep libc` 推导 LIBDIR，在 OHOS 上失效。配方显式传入 LIBDIR/INCLUDEDIR/BINDIR/SBINDIR/LIBEXECDIR/ETCDIR/DATADIR/MANDIR（均指向 package_folder 内）。
3. 顶层 install 会写 /etc/kafs、systemd units、man 到宿主，Conan 打包仅执行 `make -C src install`（库 + 头 + 四个程序），不污染宿主。
4. 全程 `os.umask(0o022)`（HMDFS 对 077 临时目录打包异常，kstart 同类教训），make 统一 -j1（HMDFS jobserver fifo EPERM 规避）。
5. R33：CC 取自 `tools.build:compiler_executables:c`（回退 clang），CFLAGS/CPPFLAGS/LDFLAGS 透传 conanbuild 环境并追加 Conan 依赖的 -I/-L/-rpath，不裸用 shell 变量。
6. OHOS 下对四个 bin 做 binary-sign-tool 自签名（kstart 同款逻辑，缺工具即抛错）。

## 上游测试审计（no_tests）

- 解包 orig.tar.gz 全量 45 文件：无 tests/、test/ 目录。
- 顶层 Makefile 目标：all/install/clean/distclean/tarball/rpm/rpmlint，无 check/test。
- src/Makefile 目标：all/lib/progs/install/clean/distclean/show_vars，无 check/test。
- 全仓无 ctest/pytest/gtest 注册，无 TESTS 变量，无 enable_testing/add_test。
- man/ 仅文档，conf/ 仅配置样例。
- 结论：上游 0.5 确无自动化测试，`status:"no_tests"`，`discovered:0/executed:0`，审计见 test_package/MANIFEST.yml。

## test_package 设计（R34）

- test_kafs_client.c（6 用例，离线，无网络）：
  1. kafs_profile_parse_file 解析 kafs_test.conf
  2. kafs_profile_get_string 取 thiscell=test.example.com（含 defaults 层回退）
  3. kafs_profile_count_strings 计数接口
  4. kafs_lookup_bool + kafs_lookup_constant 纯函数
  5. kafs_record_source + kafs_lookup_status 字符串化
  6. kafs_alloc_server_list / kafs_free_server_list 内存管理
- CLI 烟囱（第 7 用例）：`kafs-check-config -c kafs_test.conf -P -N dns`（-N dns 禁掉全部 DNS，纯离线解析，应 exit 0）。
- kafs_test.conf 为静态 cell（use_dns=no，address=127.0.0.1），不发起外网 DNS。
- 计数口径：C 侧解析 `^CASE \d+ PASS` 行（单一确定源），CLI 侧以 returncode 判定；discovered=7，passedCount=实际通过数；双通道打印 HMBS_TEST_PACKAGE_RESULT 与 HMBS_UPSTREAM_TEST_RESULT（no_tests 复发，覆盖 cache-hit 轮）。

## 风险与待真机验证

- linux/if_alg.h 在 OHOS 是否可用（aklog-kafs 直接包含该内核头做 AF_ALG 加密）。若真机缺该头，需补 patch 改走用户态实现或条件降级，待预检日志判定。
- krb5 与 libkeyutils 的 transitive_headers 是否在真机完整透传 -I/-L（配方已显式拼接 -I/-L/-rpath，kstart 同款验证过）。
- 四个 bin 在真机是否一次签名成功（SIGN_TOOL_PATH 与 /data/service/hnp/bin 双路径探测）。

## 验证命令（真机预检用，本地不执行 conan）

```bash
conan create archives/k/kafs-client/0.5 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 身份

- 申请人：gcw_6a3w2yXz
- 队伍：来都来了

## 2026-10-14 真机 compile 失败修复
- 现象：lib_object.c 报 8x use of undeclared identifier _res + res_nclose conflicting types（预检 compile 阶段）。
- 根因：上游自带 _res 依赖的 res_n* 兼容实现；OHOS/musl 无 _res 全局量；上一轮追加的 shim 自身也引用 _res 且与上游 res_nclose 重复定义。
- 修复：配方改为前置 per-TU static _hmbs_res_fallback + #define _res 重映射（__GLIBC__ 守卫，glibc 不动）；缺失的 res_n* 才在定义 TU 内追加无 _res 版本（res_init/res_query 顶层），避免重复定义。

## 2026-10-14 第二轮 compile 修复
- 进展：_res 未声明从 8 个降到 0，残留 1 个 conflicting types for res_nclose（line39 隐式声明与 line178 定义冲突）。
- 根因：OHOS resolv.h 无 res_n* 声明，调用点先隐式声明为 int res_nclose()，与上游 void res_nclose(res_state) 冲突。
- 修复：前置块追加 BIND 标准签名的 res_ninit/res_nclose/res_nquery/res_nsearch 前向声明；定义 TU 缺失的符号才追加无 _res 实现（含 res_nsearch 回退到 res_query）。

## 2026-10-14 第三轮 link 修复
- 现象：编译全部通过，链接 kafs-check-config 时报 ld.lld undefined reference (res_nquery/res_ninit/res_nclose referenced by libkafs_client.so, --no-allow-shlib-undefined)。
- 根因：上一轮“已定义”检测在前置声明追加之后运行，正则 (int|void) sym\s*\( 会把自家前向声明（分号结尾）误判为定义，missing 恒为 []，shims 从未追加；.so 仍带未定义 res_n*，而 OHOS/musl libresolv 根本不提供 res_n*（仅 res_init/res_query），严格链接器拒绝 consumer 链接。已用本地复现脚本证实旧正则误判、新正则是非定义不误判、V1 剥离不伤 V2。
- 修复：_ensure_musl_res_n_compat 改为 V2：先剥离旧 V1 HMBS 块（幂等重打）；在大括号感知（static/extern 容忍、分号原型不算）的正则下先算上游已定义符号，再加前置声明；仅 OHOS 打补丁（配方级门控，不再依赖 __GLIBC__ 宏探测）；缺失的 res_ninit/res_nclose/res_nquery/res_nsearch 在 lib_object.c 内以 res_init/res_query 为顶层实现。

## 2026-10-14 第四轮 link 修复（rindex）
- 现象：res_n* 修复生效，共享库存活；链接 kafs-dns 时报 ld.lld undefined symbol: rindex（dns_main.o main 引用，链接器提示仅存在 index）。
- 根因：上游 dns_main.c 用 BSD 遗留 rindex（POSIX 等价 strrchr）；OHOS libc 无该符号（musl 精简 BSD 兼容层），与上一轮 res_n* 缺符号同类不同域。
- 修复：_make_base_args 内 OHOS 时追加 -Drindex=strrchr（POSIX 等价别名，非桩；覆盖全部 TU；glibc 不动）。未动 index（真机 libc 存在，无需处理）。

## 2026-10-14 第五轮 package/install 修复
- 现象：编译链接全过，package() 的 `make -C src install` 在 src/Makefile:84 挂：`install -D -m 0644 h1 h2 h3 <pkg>/<pkg>/include/kafs/` 报 `Error 64`。
- 根因有二：（1）配方把 LIBDIR/INCLUDEDIR 等传成 package 内绝对路径，又另传 `DESTDIR=package_folder`，而上游规则是 `$(DESTDIR)$(INCLUDEDIR)` 形式，目标路径被重复前缀（日志 `p/.../p/storage/.../p/include/kafs` 为证）；（2）该行是 3 源多文件 `install -D` 调用，真机 HMBS install shim 只接受单源双参（多源即 exit 64，xeyes/cvechecker 同款 E182/E188），与缺 busybox 的 Error 127 不同域。
- 修复：package() 不再传 DESTDIR（目录已是绝对路径，直接落包内，保持与 build() 烘焙的 ETCDIR 一致）；新增 `_write_install_shim()`（cvechecker 同款 cp/mkdir 多源 shim，-D/-c/-p/-s/-m/-d/-- 全兼容，chmod 容错，os.open 0o755 生成），PATH 前置遮蔽单源 shim 并兼传 INSTALL 变量。

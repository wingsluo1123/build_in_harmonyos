# globus-openssl-module 5.2 适配笔记

## 来源与版本

- 上游项目：Grid Community Toolkit（GCT）的 Globus OpenSSL 模块包装库，`globus_module_activate(GLOBUS_OPENSSL_MODULE)` 时初始化 OpenSSL 并注册 GSI 代理证书相关 OID 与 X509V3 扩展方法（PROXYCERTINFO / OLD PROXYCERTINFO / 四个代理策略 OID），供 GSI 链上层库使用。
- 源码归档：https://deb.debian.org/debian/pool/main/g/globus-openssl-module/globus-openssl-module_5.2.orig.tar.gz（SHA256 见同目录 conandata.yml）。
- 版本状态：5.2 为最新 GCT v6.2.20260123 发布版所含组件版本；GCT master 的 5.3 尚未发布，未采用。
- 许可证：Apache-2.0。
- 依赖（单 flavor，无 thr/nothr 变体）：configure.ac 闭包 = globus-common >= 14 + globus-gsi-proxy-ssl >= 4 + globus-gsi-openssl-error >= 2 + openssl >= 1.0（本仓分别钉 18.15 / 6.6 / 4.4 / 3.5.6）；源码 include globus_error_openssl.h 与 proxycertinfo.h，与闭包一致；无 libltdl。

## 编译环境

- 构建系统：autotools（源码自带预生成 configure，autoconf 2.69 / automake 1.11 生成，无需 autoreconf）
- 目标平台：HarmonyOS PC（OHOS），aarch64
- 编译器：clang
- triplet：--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos

## 适配要点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 以 umask 077 运行，生成文件权限异常 | 上游脚本 mktemp / mkdir 两处 umask 077（automake 1.11 生成的旧式脚本），与鸿蒙环境权限语义冲突 | source() 阶段一次替换 umask 077 → umask 022，两处全覆盖 |
| 2 | configure 报无法识别的 host 类型 | 源码内 config.guess 2013-06-10 / config.sub 2013-04-24 不识别 *-linux-ohos | 补丁 patches/0001-config.sub-ohos.patch，三 hunk 添加型（maybe_os 列表行加 linux-ohos*、linux-ohos 子分支插入、os 归一化大表追加 -linux-ohos*），派生自 globus-gsi-openssl-error 4.4 同代先例（2013 系同形状；区别于 globus-gsi-proxy-ssl 6.6 的 2018 系替换对形状） |
| 3 | 链接阶段 libtool 解析依赖 .la 失败 | libtool 2.4.2 的 .la dependency_libs 记录无效 libdir | configure 生成 Makefile 后、make 前，将 library/Makefile（本包仅此一个目标）中 -lglobus_common / -lglobus_proxy_ssl / -lglobus_openssl_error 三个 globus token 逐一替换为对应包内 .so 绝对路径；注意 -lglobus_openssl_error 以 -lglobus_openssl 为前缀，按完整 token 替换互不污染；openssl 无 .la，-lssl/-lcrypto 不动 |
| 4 | 运行期跨库符号不被解析（L1e 前的正向验证曾暴露） | 本工具链 libtool 链接 .so 形式 deplibs 时直接丢弃，GSI 链各库产物（含 globus-common / gsi-openssl-error / gsi-proxy-ssl）均不带兄弟库 DT_NEEDED，仅含 libltdl.so.7 | 平台既定约定：消费者链接完整闭包（cpp_info.requires 已全量传递四依赖；test_package 直接链接 -lglobus_openssl -lglobus_common -lglobus_proxy_ssl -lglobus_openssl_error -lssl -lcrypto），musl 加载器全局符号域下重定位即可绑定，与既有 GSI 链产物行为一致 |
| 5 | test_package 断言 3 失败（sn=proxyCertInfo） | OpenSSL 3.x 已内置 1.3.6.1.5.5.7.1.14 对象（短名 proxyCertInfo、内置 X509V3 方法），activate 走"已注册"分支，OBJ_nid2sn 返回内置短名而非 OBJ_create 注册名 | 改用 OID 文本往返断言（OBJ_txt2obj → OBJ_obj2txt 与 PROXYCERTINFO_OID 逐字比对）；OLD OID（1.3.6.1.4.1.3536.1.222）无内置对象，其 X509V3 扩展方法断言仍精确归因本库 |

## 上游无测试套件，L1 由 test_package 承担

- 上游测试：无。discovery 核对（基准 = conandata.yml 所列 orig tarball，逐项实核）：顶层 Makefile.am `SUBDIRS = library`（无 test 目录、无 check 目标）；configure.ac AC_OUTPUT 列表不含任何 test Makefile；全源码树无 test*/ 目录、无 TESTS / check_PROGRAMS 变量。核对结论：官方无上游测试，NO_UPSTREAM_TESTS 成立，核对清单与结论已记录于 test_package/MANIFEST.yml。
- L1 覆盖由 test_package 承担（消费者视角，12 项断言出口，与 test_package/MANIFEST.yml 审计口径一致）：activate → 断言 PROXYCERTINFO OID 注册（OBJ_txt2nid + OBJ_txt2obj/OBJ_obj2txt 文本往返；OpenSSL 3.x 内置对象短名不参与断言）、OLD PROXYCERTINFO OID 及其 X509V3 扩展方法（X509V3_EXT_get_nid——OpenSSL 无该 old OID 内置方法，只能来自本库 activate 内 X509V3_EXT_add）、四个代理策略 OID → deactivate → re-activate 循环后断言全部恢复 → 最终 deactivate。

## 验证结果

- 本地验证（设备端 conan cache 含全部依赖，`conan create` 完整通过，rc=0、无 ERROR）：本包因上游依赖 globus-gsi-openssl-error/4.4 与 globus-gsi-proxy-ssl/6.6 尚未发布到制品仓，本轮未运行权威 CI 入口，改为等价本地构建验证——依赖（libtool/2.5.4、openssl/3.5.6、globus-common/18.15、globus-gsi-proxy-ssl/6.6、globus-gsi-openssl-error/4.4）全部命中本地缓存，configure 以 --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos 通过（host 识别依赖补丁），soname libglobus_openssl.so.0（-version-info 5:2:5），install 产物 libglobus_openssl.so.0.5.2 + include/globus_openssl.h + pkgconfig，包内无 .la；权威 CI 待依赖发布后补跑。
- test_package 消费者测试（L1）：真机 aarch64 通过（12 项断言出口全绿：首次激活 PROXYCERTINFO OID 文本往返、OLD PROXYCERTINFO OID + X509V3 扩展方法、四个代理策略 OID 全部命中；deactivate/re-activate 循环后全部恢复）。
- 破坏性负向测试（L1e）：移走 conan cache 中本包 lib/ 与 include/ 后重跑 conan test，编译即失败（globus_openssl.h not found，符合预期）→ 恢复产物后复跑 conan test rc=0 且断言全绿——确认测试真实依赖本包产物，非伪测试。
- 本地验证执行环境说明：本地复跑时在权威 profile 基础上仅把 CONFIG_SHELL/SHELL 指向系统 /bin/sh（该 hnp musl bash 在设备存储挂载点 getcwd 不可用）；此为本地执行环境适配，不进交付文件，权威 CI 补跑仍用权威 profile。
- 门禁：L4/L5 与知识库检查通过；L0/L1 权威判定待 CI 补跑；L2 skip（纯库，无 bin/ 可执行冒烟项）。

## 已知限制

- 权威 CI（ci/conan/build_and_test.sh + ohos-aarch64 profile）本轮未执行：等 globus-gsi-openssl-error/4.4 与 globus-gsi-proxy-ssl/6.6 发布到制品仓后由 Coordinator 补跑；补跑通过前本候选不算完整交付。
- 仅在真机 aarch64 验证，模拟器未覆盖。
- 无其他已知限制。

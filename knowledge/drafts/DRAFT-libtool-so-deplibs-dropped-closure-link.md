# DRAFT-libtool-so-deplibs-dropped-closure-link — libtool 丢弃 .so deplibs，消费者须链接全闭包

> title: libtool 2.4.x link mode 丢弃 .so 形式 deplibs——产物 DT_NEEDED 仅 libltdl+libc、不带任何兄弟库；消费者必须链接全闭包、musl 全局符号域完成跨库重定位；编译链接全绿不构成可用性证据，终判以真机运行消费者探针为准

## 摘要

本平台的 autotools 共享库产物普遍**不带兄弟库 DT_NEEDED**（实测多库
`NEEDED = libltdl.so.7 + libc.so` 而已）。这不是单包 bug，而是工具链行为：
libtool 2.4.x link mode 会把 LIBADD 中的 .so 形式 deplibs 从最终驱动命令里
丢弃。musl 加载器无惰性绑定、只在全局符号域做重定位——只要可执行文件
（消费者/test）直接链接了完整依赖闭包，跨库符号就能在运行期绑定成功。

## 现象

- 编译、链接全部成功；test_package 一跑即
  `Error relocating libX.so.0: <symbol>: symbol not found`，退出码 127。
- `llvm-readelf -d libX.so.0 | grep NEEDED` 看不到它实际调用的兄弟库
  （无 llvm-readelf 时用 readelf）。

## 证据

- globus-common 18.15 / globus-gsi-openssl-error 4.4 / globus-openssl-module
  5.2 三个产物的 NEEDED 均只有 libltdl.so.7 + libc.so；
- globus-openssl-module 5.2 的 test_package：仅链 `-lglobus_openssl
  -lglobus_common -lssl -lcrypto` 时报 `PROXYCERTINFO_OLD_x509v3_ext_meth` /
  `globus_i_gsi_openssl_error_module` relocating 失败；补链
  `-lglobus_proxy_ssl -lglobus_openssl_error` 后全绿。

## 两条禁则

- forbid_1：消费者/test 只链顶层库就期望跨库符号运行期自动解析——musl 无
  惰性绑定，产物又没有兄弟 DT_NEEDED，运行即
  `Error relocating ... symbol not found`（rc=127）。
- forbid_2：以编译链接全绿判定适配完成、不在真机跑消费者级运行验证——该
  缺陷仅运行期重定位暴露，会以绿姿态漏到下游，排障点远离根因。

## 正确姿势

1. 配方 `cpp_info.requires` 全量声明依赖（`pkg::pkg` + system_libs），
   下游自然拿到完整链接行——不要漏项，否则下游断依赖。
2. test_package/消费者显式链接全闭包：
   `-lglobus_openssl -lglobus_common -lglobus_proxy_ssl
   -lglobus_openssl_error -lssl -lcrypto`。
3. 运行期 `LD_LIBRARY_PATH` 覆盖全部依赖包 lib 目录。
4. 不要给每个库强行制造 DT_NEEDED（与平台全部既有产物不一致，且 .la 解析
   回归时会被打回）。
5. 适配完成的终判 = 真机跑通消费者级运行探针（pristine 裸链失败 + 闭包
   链接恢复，自包含探针序列见 .kv 的 verification_cmd：full_deploy 出包 →
   readelf 审 NEEDED → 裸链 rc=127 → 闭包链 rc=0）。

## 适用边界（与 E429 的衔接）

本条适用于多库互链家族、且平台既有产物一致不带兄弟 DT_NEEDED 的场景
（本仓 GSI 链等）；单个远古 libtool（如 1.3.3 old_deplibs 机制）库、确需
自持 NEEDED 时，按 E429-draft-E29C 的重建产物方案处理，勿混用。

## 与既有条目的关系

similar_to：E429-draft-E29C、E669-app-consumer-run-closure-skips-transitive-so-libs、
draft-ohos-dlopen-own-dt-needed-closure、E465、E502、E236、E522、E050。

- E050：install 阶段 soname 链接（不同环节）。
- 与 ".la dependency_libs 陷阱"（Makefile 中 -l token 替换为包内 .so 绝对
  路径）同源：替换解决了 .la 解析失败，但 libtool 对 .so deplibs 的丢弃是
  该手法的伴生结果，须靠消费者闭包链接兜底。
- principles：P-BUILD-001

## 已知限制

机制归因基于最终 link 命令对比（libtool 展开行含 .so、驱动命令行不含）与
多产物 readelf 审计；未单独最小复现 libtool 上游行为分支。

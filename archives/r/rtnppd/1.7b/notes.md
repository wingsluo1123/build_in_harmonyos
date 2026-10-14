# rtnppd 1.7b — 适配记录

> 分支: feat/rtnppd-1.7b
> 最后更新: 2026-10-13

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | rtnppd（TNPP 3.8 分组路由守护进程，串口/IP 寻呼组网） |
| 版本 | 1.7b |
| 状态 | built（待真机预检复核） |
| 构建系统 | makefile（无 configure/cmake/meson/autotools，单一 Makefile） |
| 真实上游 | https://sourceforge.net/projects/rtnppd/ |
| 源码 URL | https://downloads.sourceforge.net/project/rtnppd/Original/1.7/rtnppd-1.7b.tar.gz |
| sha256 | 06651a98c99048d9a211a92a68d8e5ed03ffdf2caf04904923a8ae7418a5eca4 |
| 大小 | 44248 字节（SourceForge Original/1.7 目录，2007-03-19 发布） |
| 依赖 | 无（`Makefile:15` `LIBS +=` 为空，默认不链接 SQL 后端） |
| 包类型 | application（守护进程 + 工具二进制，R38: 软件级 commands.json 已声明） |

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 官方源码包 rtnppd-1.7b.tar.gz（2026-10-13 下载校验, sha256 见上）

- 顶层文件: Makefile / README / COPYRIGHT / rtnppd.c / rtnppd.h /
  readcfg.c / readcfg.h / crc.c / crc.h / blowfish.c / blowfish.h /
  testq.c / tnpppage.c / rtnppd.conf / tnpp_dev.conf / tnpp_trans.conf /
  new_rtnppd.conf / new_tnpp_dev.conf / new_tnpp_trans.conf /
  example.complex / from_sendmail_to_tnpppage.pl / CVS/
- 无 tests/、test/、spec/、t/ 目录；
  全树无 `TEST(`/`TEST_F`（gtest）、无 `def test_`（pytest）；
  全树 `*test*` 仅命中 testq.c（随包发布的外部队列示例工具，非测试）
- Makefile 仅定义 `default` / `rtnppd` / `testq` / `tnpppage` / `clean` /
  `install` / `install.config` / `key` 目标, 无 `check` / `test` / `TESTS` /
  `check_PROGRAMS` 目标；`make check` 无规则可执行
- 上游是 TNPP 分组路由守护进程, 功能验证只能靠真实执行二进制完成

结论: 上游 rtnppd 1.7b 确实不存在测试套件, test_package/MANIFEST.yml 声明
`upstream_tests_exist: false` + 非空 `upstream_test_audit`；不虚构测试数字。
功能验证由 test_package 真实执行三个二进制完成（usage/getopt 启动路径断言 +
OHOS aarch64/musl ELF 身份断言），详见 test_package/MANIFEST.yml。

## 三、补丁清单
| 补丁 | 内容 | 类型 |
|------|------|------|
| 0001-blowfish-h-stdint.patch | 引入 `<stdint.h>`，`u_int32_t/u_int64_t` 改为 `uint32_t/uint64_t`：BSD 类型名仅由 glibc 的 `sys/types.h` 提供，OHOS/musl 无此定义（无平台宏） | portability |
| 0002-blowfish-c-portability.patch | blowfish.c 同上类型替换（34 处）+ 补 `<arpa/inet.h>`：`htonl/ntohl` 在原文件中为隐式声明（与 Alpine gcc14.patch 同因） | portability |
| 0003-rtnppd-c-portability.patch | ① `<sys/fcntl.h>`（glibc 专有重定向头，musl 无此文件）改为 `<fcntl.h>`；② 补 `decrypt_packet()` 前置声明（先用后定义）；③ `u_int64_t` 改 `uint64_t`（5 处） | portability |
| 0004-testq-c-main.patch | `main(int argc, ...)` 补 `int` 返回类型（隐式 int 在现代 C 为硬错误）+ 补 `<stdlib.h>/<unistd.h>`（exit/unlink 隐式声明） | portability |
| 0005-tnpppage-c-return.patch | `send_tnpp_packet()`（返回 int）的裸 `return;` 改为 `return 0;` | portability |

补丁对照: Alpine 官方 aports gcc14.patch 已实证 0002（arpa/inet.h）、0003（decrypt_packet
原型）、0004（main 类型与两个头文件）、0005（return 0）四类修复；本适配在其基础上把
`void main` 改为标准 `int main`，并新增 musl 必需的 stdint/fcntl 两项。

## 四、配方要点（conanfile.py）
- 纯 Makefile、无依赖: `make CC=<工具链 cc> CFLAGS="-O2 -Wall" -j1`
 （Makefile 自带 `-O2 -pipe -g -I./` 追加与 `$(CC)` 链接）
- 编译器从 `self.conf.get("tools.build:compiler_executables")` 获取（R33），
  以 `make CC=... -j1` 传入（R9: 单作业）；仅当 conf 路径真实可执行时采用，
  否则回退到 PATH 中的 clang/cc（2026-10-13 预检机无
  `/data/service/hnp/bin/clang`，make 报 Error 127），make 取
  `HMBS_MAKE`/PATH 探测；test_package shell 按 CONFIG_SHELL->SHELL->PATH
  探测，test.sh 首行改为 `#!/bin/sh`
- 平台守卫 `self.settings.os in ("Linux", "OHOS")`（R32）
- package_type=application, `cpp_info.bindirs=["bin"]`, `cpp_info.libs=[]`（R38）
- build() 不调用 `make check`（上游无该目标）; MANIFEST 中
  `upstream_test_in_build: false` 如实声明
- 上游 `make install` 会写 `$(PREFIX)/etc`、建 `/var/spool/rtnppd` 并用 dd 从
  /dev/urandom 生成密钥，不适合 Conan 打包；package() 改为直接拷贝
  `rtnppd`/`testq`/`tnpppage`、`COPYRIGHT` 与配置样例/README
- build() 沿用 rbootd 实证的 OHOS 构建卫生模式：`< /dev/null` 脱离 socket
  stdin、`cd` 代替 `cwd=`、日志回放（见 rbootd/3.4 notes 第七节）

## 五、验证记录
- 本机: 源码下载 + sha256 校验通过（06651a98…5eca4, 44248 字节）；
  5 个补丁由 orig/work 双树 difflib 生成，`git apply --check -p1` 全通过，
  全量应用后与 work 树内容一致（仅 Windows 侧 CRLF 换行转换差异）
- 真机预检: 待 HMBS 后台执行（本轮仅交付未提交工作树，不 commit、不 push）
- test_package（消费者视角）: 设计 5 断言，含 2 项鸿蒙特有用例（OHOS
  aarch64 ELF 身份 + musl loader 链接）；上游无测试套件（0 用例）
- 停在首轮交付：未 commit / 未 push / 未创建 PR / 未上传制品

## 六、遗留问题
- 无已知编译阻塞；零外部依赖（W0 无需制品仓检查项）
- `rtnppd` 运行时需串口/IP 组网与配置文件, test_package 仅覆盖 usage/getopt
  安全启动路径，不做真实组网（需 root/网络, CI 不可复现）
- `rtnppd.c` 使用 syslog/termios；musl 均提供对应头与符号，属链接期验证项，
  真机预检若报缺符号再补齐

## 七、可复用发现（供后续同类 Makefile 配方参考）
1. **SourceForge Twice 布局**：rtnppd 的发布文件在 `Original/1.7/` 子目录，
   直接下载地址为 `downloads.sourceforge.net/project/<proj>/Original/1.7/<file>`；
   CI 对 sourceforge.net 自动加镜像回退（R39：配方只写官方 URL）
2. **musl 缺 BSD 类型名**：`u_int32_t/u_int64_t` 等仅 glibc 提供，替换为 C99
   `uint32_t/uint64_t` + `<stdint.h>` 在三 libc 通吃，比平台宏更干净（PF5 无感）
3. **`<sys/fcntl.h>` 是 glibc 专有**：musl/bionic 均无此文件，一律用 `<fcntl.h>`
4. **Alpine aports 是老软件的预言机**：gcc14.patch 这类发行版补丁直接给出
   现代编译器报错清单，可逐项转写为本仓补丁
---

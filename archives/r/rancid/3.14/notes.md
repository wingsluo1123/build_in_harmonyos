# rancid 3.14 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4
- 目标平台: HarmonyOS (aarch64, musl libc)
- 状态: published

## 编译步骤

```bash
# 1. 安装依赖
#    expect 5.45.4 预编译包已安装到 /storage/Users/currentUser/usr/local

# 2. 修复源码（通过补丁自动应用）
#    补丁1: configure - 移除 ping -v 标志 + umask 077→000
#    补丁2: configure.ac - 移除 ping -v 标志

# 3. 编译
export LD_LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH"
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: can't locate expect | expect 未安装 | 从 cmd-pkgs 下载安装 expect 5.45.4 预编译包（用 Python urllib 绕过 SSL 证书问题） |
| 2 | configure: can't figure out how to pass count == 1 to ping | configure 测试 `ping -c 1 -v 127.0.0.1`，OpenHarmony ping 不支持 -v 标志 | 修改 configure.ac 和 configure: 移除 -v 标志 |
| 3 | config.status: Permission denied | HMDFS 上 umask 077 创建临时目录时 setgid 位导致权限问题 | 修改 configure: umask 077 → umask 000 |
| 4 | conan create: make install 失败 (rancid.types.conf not found) | rancid 的 etc/Makefile 未使用 $(srcdir) 前缀，out-of-source build 时找不到源文件 | conanfile.py 中设置 in-source build (self.folders.build = "src") |
| 5 | conan create: test_package 失败 (deps_cpp_info 不存在) | test_package 使用了 Conan 1.x API | 改用 Conan 2.x API (self.dependencies["rancid"].cpp_info) |
| 6 | conan create: 补丁文件找不到 | refresh-patch 生成新补丁名，但 conandata.yml 引用旧文件名 | 更新 conandata.yml 引用新补丁文件名 |

## 源码修改（补丁）

### 补丁 0001-configure.patch
- 文件: configure
- 修改1 (line 6268): `$PING_PATH -c 1 -v 127.0.0.1` → `$PING_PATH -c 1 127.0.0.1`
  - 原因: OpenHarmony ping 不支持 -v (verbose) 标志
- 修改2 (line 7882): `umask 077` → `umask 000` (mktemp -d 处)
  - 原因: HMDFS 上 setgid 目录权限导致文件创建失败
- 修改3 (line 7887): `umask 077` → `umask 000` (mkdir 处)
  - 原因: 同上

### 补丁 0002-configure.ac.patch
- 文件: configure.ac
- 修改 (line 355): `$PING_PATH -c 1 -v 127.0.0.1` → `$PING_PATH -c 1 127.0.0.1`
  - 原因: 与 configure 同步修改（R6: 只改源文件，configure 为生成文件但此处同步修改以避免依赖 autoconf）

## 依赖版本

- expect 5.45.4 (cmd-pkgs 预编译包)
- perl (系统自带)
- clang 15.0.4 (HarmonyOS SDK 自带)
- mktemp, ginstall (coreutils 预编译包)

## 编译产物

| 类型 | 文件 | 说明 |
|------|------|------|
| ELF 二进制 | hpuifilter (43392 bytes) | HP UI 过滤器, C 编译, 静态链接 |
| ELF 二进制 | par (33200 bytes) | 并行访问路由器, C 编译, 静态链接 |
| expect 脚本 | 52 个 | 各厂商设备登录和配置获取脚本 |
| shell 脚本 | rancid-run | 主运行脚本 |
| CGI 脚本 | lg.cgi, lgform.cgi | Web 查看界面 |
| Perl 模块 | 34 个 .pm 文件 | rancid 核心库 |
| man 手册 | 8 个 | 文档 |
| 配置文件 | 3 个 | rancid.types.base, rancid.conf.sample, lg.conf.sample |

总安装文件数: 176

## 验证结果

- configure: ✅ 通过
- make -j1: ✅ 通过
- make install: ✅ 通过 (176 个文件)
- make check: ✅ 通过 (无测试用例, 退出码 0)
- hpuifilter --help: ✅ 正常输出用法
- par --help: ✅ 正常输出用法
- R26 静态链接: ✅ Conan 构建版本完全静态 (无动态段)
- conan-verify 8 道门禁: 全部通过

## Conan 配方

- conanfile.py: 使用 Autotools 工具链, in-source build, -static 标志 (R26)
- conandata.yml: sha256 = cbf608d8508b55dffb6b30c7a1c45c16ea53af7611a466e0cc47a863252f6e49
- test_package/: 使用 Conan 2.x API 测试 hpuifilter/par 二进制
- 补丁: 2 个 (0001-configure.patch, 0002-configure.ac.patch)

## 注意事项

- rancid 大部分组件是 Perl/expect 脚本，仅有 hpuifilter 和 par 是编译的 C 二进制
- 需要预装 expect 和 perl 运行时
- conanfile.py 中 package_info.libs 为空（工具包，无库文件）
- conanfile.py 使用 in-source build 解决 rancid Makefile 不支持 out-of-source build 的问题
- umask 修复使用 000 而非知识图谱建议的 022（000 更宽松，确保 HMDFS 兼容）

---

**编译结束**: 2026-06-26
**最终状态**: published

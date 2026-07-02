# perl-net-xmpp 1.05-r0 适配笔记

## 编译环境
- 构建系统: Perl Module::Build (via Makefile.PL compat wrapper)
- 编译日期: 2026-06-29
- 编译器: N/A (纯 Perl 模块，无 C 编译)
- Perl 版本: 5.42.0 (aarch64-linux)
- 平台: OpenHarmony (aarch64-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 1. 下载源码
# URL: https://cpan.metacpan.org/authors/id/D/DA/DAPATRICK/Net-XMPP-1.05.tar.gz
# sha256: 4c02200577c2b235a163a09bfaa152bf000fe5f1499ad80ce16ab66808949362

# 2. 解压源码
tar xzf Net-XMPP-1.05.tar.gz
cd Net-XMPP-1.05

# 3. 生成 Makefile (Makefile.PL 是 Module::Build::Compat 包装器)
perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX

# 4. 编译 (纯 Perl 模块，无 C 代码)
make -j2

# 5. 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX

# 6. 测试
make test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | XML::Stream::Parser.pm 警告: "Possible precedence problem between ! and numeric eq (==)" | XML::Stream 1.24 依赖模块中的运算符优先级问题 | 非阻塞警告，不影响功能。属于上游 XML::Stream 模块问题，非 Net::XMPP 本身 |
| 2 | t/gtalk.t 测试失败 | 需要 Google Talk XMPP 服务器网络连接 | 环境限制（无网络），非代码问题 |
| 3 | t/srv.t 测试失败 | 缺少 LWP::Online 测试依赖 (build_requires only) | 测试专用依赖缺失，非代码问题 |
| 4 | t/memory_cycle.t 跳过 | 需要 Test::Memory::Cycle 模块 | 可选测试依赖，非阻塞 |
| 5 | t/memory_leak.t 跳过 | 需要 Devel::LeakGuard::Object 模块 | 可选测试依赖，非阻塞 |

## 源码修改

无补丁。Net::XMPP 1.05 是纯 Perl 模块，在 OpenHarmony 平台上无需修改源码即可编译和运行。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| Perl | 5.42.0 | 运行时 |
| XML::Stream | 1.24 | 运行时 |
| Digest::SHA | 6.04 | 运行时 |
| Authen::SASL | 2.2000 | 运行时 |
| MIME::Base64 | 3.16_01 | 运行时 |

## 验证结果

```bash
# 模块加载验证
$ perl -MNet::XMPP -e 'print $Net::XMPP::VERSION'
1.05

# Conan 验证 (8 道门禁全部通过)
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-net-xmpp 1.05-r0
G0: PASS | G1: PASS | G2: PASS | G3: PASS | G4: PASS | L2: PASS | L4: PASS | L5: PASS

# 功能测试 (20/20 PASS)
$ perl xmpp_test.pl
PASS: 20 | FAIL: 0 | WARN: 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Net/XMPP.pm | 11920 | 主模块 |
| Net/XMPP/Protocol.pm | 104669 | XMPP 协议实现 |
| Net/XMPP/Stanza.pm | 45032 | XML Stanza 基类 |
| Net/XMPP/Namespaces.pm | 24421 | XMPP 命名空间定义 |
| Net/XMPP/Roster.pm | 25755 | 花名册管理 |
| Net/XMPP/Connection.pm | 16210 | 连接管理 |
| Net/XMPP/Message.pm | 13404 | 消息处理 |
| Net/XMPP/IQ.pm | 11452 | IQ (Info/Query) 处理 |
| Net/XMPP/Debug.pm | 10533 | 调试支持 |
| Net/XMPP/JID.pm | 9940 | JID 解析 |
| Net/XMPP/Presence.pm | 9768 | 在线状态处理 |
| Net/XMPP/Client.pm | 8323 | 客户端接口 |
| Net/XMPP/PrivacyLists.pm | 8388 | 隐私列表 |
| conanfile.py | 3183 | Conan 配方 |
| conandata.yml | 296 | 源码与补丁声明 |

## 注意事项

1. **XML::Stream 警告**: 运行时会产生 "Possible precedence problem" 警告，来自上游 XML::Stream 1.24 模块，非 Net::XMPP 问题，不影响功能。
2. **纯 Perl 模块**: 无 C/XS 代码，不受 SELinux HMDFS 限制影响（对比 perl-dbd-pg 的 XS 模块限制）。
3. **网络测试**: 2 个测试文件 (t/gtalk.t, t/srv.t) 需要网络连接或额外测试依赖，在离线环境中会失败，但不影响模块功能。
4. **R26/R32 合规**: 纯 Perl 模块无 .so 输出，不涉及系统同名库冲突；conanfile.py 的 `settings.os` 未做 `== "Linux"` 判断，符合 R32。

---

**编译结束**: 2026-06-29 20:09
**最终状态**: published

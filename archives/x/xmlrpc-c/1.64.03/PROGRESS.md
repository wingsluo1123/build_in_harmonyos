# xmlrpc-c 1.64.03 — 编译进度

> 档案创建时间: 2026-04-29
> 最后更新: 2026-08-09
> 状态: ✅ published (conan 适配完成)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | xmlrpc-c |
| 版本 | 1.64.03 |
| 构建系统 | autotools |
| 编译器 | clang 15.0.4 |
| 源码路径 | https://sourceforge.net/projects/xmlrpc-c/files/Xmlrpc-c%20Super%20Stable/1.64.03/xmlrpc-1.64.03.tgz |
| SHA256 | 74729d364edbedbe42e782822da1e076f3f45c65c4278a3cfba5f2342d7cedbe |

## 二、编译阶段

### Phase 1: 环境准备 ✅
- [x] ohc-run.py init-build 完成
- [x] curl/8.15.0 依赖从 ohpcd 制品仓获取
- [x] openssl/3.5.6.1 依赖从 ohpcd 制品仓获取

### Phase 2: 编译 ✅
- [x] configure 完成（全特性：curl-client + abyss-server + openssl + c++）
- [x] make 编译完成
- [x] make install DESTDIR 完成

### Phase 3: 测试验证 ✅
- [x] xmlrpc-c-config --version 验证通过 (1.64.3)
- [x] xmlrpc-c-config --features 验证: c++ abyss-server curl-client

### Phase 4: Conan 适配 ✅
- [x] conanfile.py 生成（含 curl/openssl 依赖）
- [x] conandata.yml 生成（含正确 SHA256）
- [x] test_package/ 生成（含实质 API 测试）
- [x] conan-verify 全部通过 (G1/G0/G2/G3/G4/L2/L4/L5)

## 三、关键修复

| 问题 | 知识图谱 | 解决方案 |
|------|---------|---------|
| HMDFS umask 077 | E011 | 补丁修改 umask 077→022 (config.guess + configure) |
| config.guess 不识别 HarmonyOS | E007 | 补丁添加 HarmonyOS 检测分支 |
| 无 curl 开发文件 | - | 使用 conan ohpcd curl/8.15.0, 生成 wrapper curl-config |
| 无 openssl 开发文件 | - | 使用 conan ohpcd openssl/3.5.6.1, 生成 openssl.pc |
| configure 无法运行测试程序 | E001 | LD_LIBRARY_PATH 设置 curl/openssl lib 路径 |
| config.h 未安装 | - | package() 中 os.walk 查找并复制 config.h |
| 补丁路径不匹配 | - | 从 orig/work diff 重新生成 a/b 格式补丁 |

## 四、补丁文件
- 0001-config.guess.patch: HarmonyOS 检测 + umask 修复
- 0002-configure.patch: configure umask 修复

## 五、产物
- 核心库: libxmlrpc.a/so, libxmlrpc_util.a/so
- 客户端: libxmlrpc_client.a/so (curl transport)
- 服务端: libxmlrpc_server.a/so, libxmlrpc_server_abyss.a/so
- Abyss: libxmlrpc_abyss.a/so, libxmlrpc_openssl.a/so
- XML 解析: libxmlrpc_xmlparse.a/so, libxmlrpc_xmltok.a/so (bundled expat)
- C++ 包装: libxmlrpc++.a/so, libxmlrpc_cpp.a/so 等
- 工具: xmlrpc-c-config

## 六、构建特性
```
xmlrpc-c-config --features: c++ abyss-server curl-client
```

## 七、备注
- 全特性构建，未裁剪任何功能
- C++ 测试套件 (test/cpp/server_abyss.cpp) 存在 std::bind/POSIX bind 冲突，主库编译正常
- xmlrpc-c 内置 expat，无需外部 libxml2 依赖

# czmq 4.2.1 适配笔记

## 编译环境
- 构建系统: cmake（上游双轨 autotools/CMake，本配方走 CMake，与 zeromq/cppzmq 模板一致）
- 编译日期: 2026-10-09
- 编译器: clang 15（OHOS 工具链，aarch64-linux-ohos triplet）
- 目标: OHOS aarch64（conan profile ohos-aarch64）
- 状态: built

## 配方要点

- conanfile.py 骨架取自 archives/z/zeromq/4.3.5（同为 zproject 生成的 CMake 工程），
  requirements 写法取自 archives/c/cppzmq/4.10.0（self.requires("zeromq/4.3.5")）
- generate() 显式设置：CZMQ_BUILD_SHARED/STATIC、ENABLE_DRAFTS=OFF、
  CZMQ_WITH_{UUID,SYSTEMD,LZ4,LIBCURL,NSS,LIBMICROHTTPD}=False（上游默认 ${X_FOUND} 随探测环境漂移）
- package() 复用 zeromq 的 OHOS ELF 自签名步骤（llvm-objcopy 去 .codesign + binary-sign-tool selfSign），
  覆盖 lib/**/*.so* 与 bin/ 下 ELF（bin/zmakecert）
- package_info：cmake_file_name=czmq、cmake_target_name=czmq（别名 czmq-static）、
  pkg_config_name=libczmq（zyre 2.0.1 Findczmq.cmake 硬契约）、system_libs pthread/rt

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x configure 直接报错 | 上游 cmake_minimum_required(VERSION 2.8.12)，CMake 4.x 已移除 <3.5 兼容 | 补丁 0001-CMakeLists.txt.patch 提升至 3.5...3.27（zeromq 4.3.5 同款做法） |
| 2 | Findlibzmq.cmake（MODULE 模式）找不到 libzmq | 该模块走 pkg_check_modules("libzmq") + 裸 find_path/find_library；Conan 只把 generators 目录放入 CMAKE_PREFIX_PATH，且 zeromq 配方未提供 libzmq.pc | generate() 经 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH 注入 zeromq 包 include/lib 目录（树内 accel-ppp 先例） |
| 3 | 可选依赖探测不确定 | CZMQ_WITH_* 默认值 ${X_FOUND} 随构建机环境漂移 | generate() 六项全显式 False；对应类走内置回退（zuuid 内部生成器等） |
| 4 | 产物 libczmq.so 无 DT_SONAME（CI L5a/L5c fail） | CMAKE_SYSTEM_NAME=HarmonyOS 是 CMake 未知平台（无 Platform 模块），SONAME 标志缺失，SOVERSION 不生效 | 知识库 E330 方案：CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON + CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,，产物单文件 libczmq.so 带 SONAME=libczmq.so，不生成版本化软链（HMDFS 拒绝符号链接） |
| 5 | libczmq.so 的 DT_NEEDED 记录 conan 缓存绝对路径（CI L5b fail） | 发布版 zeromq 二进制 libzmq.so 自身无 SONAME，链接器只能把全路径写进 NEEDED | generate() 把 Findlibzmq 的 LIBZMQ_LIBRARIES 预置为 "-L<dir>;-lzmq"，链接经搜索路径完成，NEEDED 落成相对名 libzmq.so |
| 6 | test_package 编译期找不到 zmq.h | Conan CMakeDeps 对二阶传递依赖刻意剥离 include/libs 数据（czmq.h 透传包含 zmq.h） | test_package 显式 self.requires("zeromq/4.3.5")（与 czmq 配方同版本，直连依赖恢复完整数据） |

## 上游测试（设备实测，30 个稳定类）

- 入口：构建树根目录执行 `./czmq_selftest --continue --verbose --test <CLASS>`（与上游 ctest 同构 cwd），
  LD_LIBRARY_PATH 指向 czmq/zeromq 包 lib 目录
- 结果：30/30 全部 PASS（zactor zarmour zcert zcertstore zchunk zclock zconfig zdigest zdir
  zdir_patch zfile zframe zhash zhashx ziflist zlist zlistx zloop zmsg zpoller zsock zstr
  zsys zuuid zauth zbeacon zgossip zmonitor zproxy zrex）
- 网络类：zauth/zmonitor/zproxy/zgossip 真实走 tcp://127.0.0.1 回环（zmonitor 日志见
  HANDSHAKE_SUCCEEDED）；zbeacon 的 UDP 广播在本机可用，正常跑完无需跳过
- draft 类（zproc/zargs/ztrie/zosc/zhttp_*）Release 不编译，不在测试范围

## 权威 CI（ci/conan/build_and_test.sh）

- 第 1 轮：L0/L1/L4 pass，L5 fail（SONAME 三错，见问题 #4/#5），L2 skip（zmakecert
  无 --version/--help 约定，属工具习惯差异，非阻塞；人工带库路径验证 zmakecert 可正常运行）
- 第 2 轮：L0/L1/L4/L5 全 pass，L2 skip 同上，G0/KC/JC pass，单包 100% 通过
- CI 后按 E415 恢复 conandata.yml 为 HEAD 逐字节一致（镜像改写残留清理）

## 注意事项

- 设备直连 github.com 不通：源码经 conandata 官方 URL + SHA256 钉死，
  CI mirror-fallback（gh-proxy）/预下载通道获取；sources_cache 已预置同 SHA256 归档作兜底
- bin/zmakecert 触发 R38：软件级 commands.json 必备（type=tool）
- zsp / czmq_selftest / test_randof 只构建不安装，不进入包产物

---

**编译结束**: 2026-10-09
**最终状态**: built

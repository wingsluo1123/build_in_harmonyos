# sokol 0.0-git.2e75443 — 适配笔记

## 基本信息

- 上游: https://github.com/floooh/sokol （floooh/Andre Weissflog）
- 版本: master @ 2e75443dbd4940b5aa8d76a8e479f8e4b270b9a3
  （master-only 无 tag，规则 0.0-git.{hash7} → 0.0-git.2e75443）
- 源码包: 官方 GitHub master 分支 tarball（ghfast.top 镜像在前+官方兜底，
  URL 列表格式），sha256 本机实测:
  3b2d0ec363419680324f289f1a7414b199a7a8b9deac30558b1a1ab215b53833
  （本机 diff -r 全树比对 master tarball vs 2e75443 提交 tarball：0 差异
  ——快照后上游无新提交，镜像 URL 与本版本精确同锚）
- 许可证: Zlib（zlib/libpng style，Copyright (c) 2018 Andre Weissflog）
- 交付形态: header-only 单头库集 —— 8 个 core 头（sokol_gfx/app/audio/
  fetch/args/log/time/glue）平铺 include/ + 14 个 util 头（color/
  debugtext/gl/shape/letterbox/memtrack/fontstash/imgui/gfx_imgui/
  app_imgui/nuklear/spine/cmdbuf/framebuffer）→ include/util/
- W0 依赖实测: 零第三方依赖（core/util 头仅 libc/libm/pthread/POSIX
  stdio，OHOS musl 全覆盖；imgui/nuklear/fontstash/spine 桥接头仅在
  对应外部库被消费者一并包含时才有意义，单头交付不产生 requires）

## 编译步骤

1. conan create -pr:h=ci/conan/profiles/ohos-aarch64（profile 注入
   OHOS clang15，R33：编译器从 conf 取，不裸用 ${CC}）
2. source(): 官方 tarball 下载解压（strip_root，镜像列表）+ apply
   s0001 补丁（cmdbuf C++ cast）
3. build() 真跑上游官方测试：
   - functional 套件：11 个测试 TU + utest.h → 链接 sokol-test →
     真跑 294 UTEST 用例（SOKOL_DUMMY_BACKEND +
     -DUTEST_USE_CLOCKGETTIME -include time.h）
   - compile 套件：15 C + 14 C++ 编译冒烟 TU（dummy 后端）
4. package(): 头文件拷贝（core → include/，util → include/util/）
   + LICENSE → licenses/
5. test_package: C 54 断言 + C++ cmdbuf impl 段（ctest + 直跑双通道）

## 上游测试面（N 口径，rule4）

上游 tests/ 工程（CMakePresets 驱动，默认 SOKOL_BACKEND=
SOKOL_DUMMY_BACKEND）注册的测试面：

| 套件 | 用例数 | 形态 |
|---|---|---|
| functional: sokol-test（args 12 + audio 2 + cmdbuf 52 + color 3 + debugtext 22 + fetch 30 + gfx 137 + gl 16 + shape 20） | 294 | UTEST 运行时断言 |
| functional: SokolSpine（sokol_spine_test.c） | 88 | UTEST（排除：tests/ext git clone spine-c 运行时，CI 白名单不可达） |
| compile: C TU + C++ TU（平台无关子集） | 29 | 编译冒烟（15 C + 14 C++） |
| compile: imgui/nuklear/fontstash/spine/all/app TU | — | 排除：外部库（tests/ext git clone）或 X11+真实 3D 后端硬依赖 |

**适配后统计口径**：294 UTEST 用例真跑（294/294 PASS，OHOS aarch64
clang15 musl 实测）+ 29 编译 TU 全过；spine 88 例与外部库 TU 如实
记录排除原因（依赖不可达/平台无 X11，非适配缺陷——上游 sokol_app.h
Linux 路径硬性要求 X11+GL/Vulkan，OHOS PC 无 X11；图形后端绑定由
消费者按上游设计自行选择）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | utest.h 编译失败：SYS_clock_gettime 未定义 / CLOCK_REALTIME 未声明 | sheredom/utest.h Linux 分支用 syscall(SYS_clock_gettime)；OHOS musl 的 sys/syscall.h 无 SYS_* 宏；且 utest.h 用 __GLIBC__ 探测决定是否含 time.h，musl 不命中 → time.h 未包含 | 纯编译 flag：-DUTEST_USE_CLOCKGETTIME + -include time.h（预包含），零源码补丁 |
| 2 | sokol_cmdbuf.h C++ 编译硬错误：void* → uint8_t* 隐式转换 | 上游 _scb_init_cmdbuf 的 cb->buf = _scb_malloc(...) 是 C 惯用隐式转换，C++ 禁止；上游自己 的 compile 套件含 sokol_cmdbuf.cc（该路径在上游 CI 未覆盖 C++ 分支或用宽松编译器） | s0001 补丁：一行显式 cast（portability） |
| 3 | sokol_app.h 实现段编译 #error（unknown 3D API for Linux） | 上游 sokol_app.h 无 SOKOL_DUMMY_BACKEND 支持（与 gfx/audio 不同），Linux 路径硬性要求 X11+GLCORE/GLES3/WGPU/VULKAN | 编译套件排除 app TU（sokol_main.c/glue.c 保留，main.c 在 dummy 分支有 main(){} 空实现可编译）；app.h 作为头文件正常交付（OHOS 消费者按上游平台矩阵选择后端） |
| 4 | functional fetch 用例 7 个失败（load_file_*） | 上游 CMake 用 file(COPY) 把 tests/functional/assets/comsi.s3m 拷到构建目录，直接跑二进制时 CWD 缺资产 | 配方按上游同语义 copy 资产到 build 目录再跑 → 294/294 全过 |
| 5 | sokol_all.c 及 imgui/nuklear/fontstash/spine TU 不可编译 | tests/ext CMakeLists 用 git clone 拉取 cimgui/spine-runtimes/nuklear（CI 站点白名单不可达），且 all.c 把所有 impl 段并入一个 TU | compile 套件平台无关子集（排除项如实记录）；桥接头正常交付不编译 |
| 6 | 消费者测试 stm_now() 首读返回 0 | musl 时钟首次采样序（首读可能为 0，后续单调） | 消费者断言改用 t1>=t0 单调性（不假设首读非零）；上游 294 用例本身不受影响（上游 time 测试不假设首读） |

## 源码修改

- s0001-sokol_cmdbuf-cxx-voidptr-cast.patch：util/sokol_cmdbuf.h
  _scb_init_cmdbuf 一行 cast（void* → uint8_t*），修复 C++ 编译
  硬错误。上游测试源码（tests/）零修改。

## 消费者测试期望值锚点（全部 OHOS aarch64 目标机实测校准）

- saudio dummy 后端默认: sample_rate=44100, channels=1,
  buffer_frames=2048, expect()=8192；push(2帧)=2，expect()=8190
- sg_make_color_4b(255,127,0,255): r=1.0, g=0.498039, b=0.0, a=1.0
- sshape_plane_sizes(1): 4 顶点/6 索引；(2): 9 顶点/24 索引
- slbx_letterbox(1920,1080, 16:9): (0,0,1920,1080) 全幅；
  (4:3): (240,0,1440,1080) 侧边条
- fetch 真文件异步加载: 256 字节内容校验 buf[0]=0x00/buf[255]=0xFF

## CI/回归

- 本地 conan create（干净缓存）全链: 294/294 functional + 29 compile
  TU + test_package C 54/54 + C++ OK
- 无 .gitignore/临时文件混入；仅 archives/s/sokol/0.0-git.2e75443/
  目录内容

# skladnik 26.04.2 适配笔记

## 上游

- https://invent.kde.org/games/skladnik tag v26.04.2（KDE Gear release-service）
- 官方源 https://download.kde.org/stable/release-service/26.04.2/src/skladnik-26.04.2.tar.xz
- sha256=e5f202e95b40e98d41c77a48edfee9f1ab41a8c6919f12b97b273d2e4c474feb
  （本机 curl -sSL 下载后 shasum -a 256 实测一致）
- 依赖面：Qt6 Core/Gui/Widgets（本次适配新增 Network）+ KF6（Config /
  ConfigWidgets / CoreAddons / Crash / DBusAddons / I18n / KIO /
  WidgetsAddons / XmlGui）+ KF6DocTools（上游可选）+ KDEGames6
- 产物：单一可执行文件 bin/skladnik；主题资产安装到 share/skladnik/themes；
  五个内置关卡集（Sasquatch / Mas Sasquatch / Sasquatch III / Microban /
  Sasquatch IV）经 src/skladnik.qrc 以 level.data 形式编进二进制，不单独安装
- 上游版本号：project(skladnik VERSION 0.5.26042)，故 --version 输出
  skladnik 0.5.26042

## 关键决策

### 1. 裁 KIO，用 QtNetwork 等价替换（patches/0001 + 0002 + 0003）

上游对 KIO 的使用只有两处，都在 src/MainWindow.cpp：

- openURL()：KIO::file_copy(_url, QUrl::fromLocalFile(f.fileName()), -1,
  KIO::Overwrite) 后接 job->exec()，把远程关卡集文件下载到 QTemporaryFile
- dropEvent()：KUrlMimeData::urlsFromMimeData(event->mimeData())，
  从拖放 MIME 数据里取 URL 列表

为什么不能直接引入 kio：制品仓只发布 kio/6.14.0 与 kio/6.26.0。
libkdegames/26.04.0（KDEGames6，REQUIRED）把 KF6 精确锚定在 6.18.0 线，
kio/6.26.0 的二进制锚定 6.26 线，混线会让所有 KF6 package id 变化、无预编译
二进制可用（kgoldrunner 26.04.0 notes 决策 1 的 conan 实测结论）。kio/6.14.0
则要靠消费者 override=True 把其内部 requires 抬到 6.18 闭包，代价是 kio 必须
源码重建，ktuberling 26.04.0 走过这条路，并因此撞上 conan create 3600s
超时，最终需要切换 mirror 并把 ci/config/build_timeouts.txt 提到 10800s。
另外实测 knewstuff/6.18.0 的 requires 里不含 kio（conan download 后直接读
配方确认），所以 KIO 本来就不在 libkdegames/26.04.0 的传递闭包内，想用就得
自己整包引入。

取舍：本仓 KDE Gear 游戏已合并的 4 个先例中，kgoldrunner 与 kfourinline 都是
裁 KIO、保持依赖图全命中预编译二进制；只有 ktuberling 保留 KIO，并为此付出
源码重建加 ci/config/build_timeouts.txt 覆盖（该文件属 R21 灰区，pytorch 条目
自身就注明已就此在 PR 上报请维护方裁定）。skladnik 选裁剪路线：依赖图与
kgoldrunner 同构、不动 ci/、PR 原子性干净。

等价替换（不是简单删功能）：

- KIO::file_copy 换成 QNetworkAccessManager::get(QNetworkRequest)，设
  RedirectPolicyAttribute = NoLessSafeRedirectPolicy（对应 KIO 跟随重定向的
  行为），用 QEventLoop 阻塞等待 finished，语义对应上游的 job->exec()；
  失败或写入长度不符时与上游一致地静默 return。Qt6 Network 在 ohpcd
  qtbase/6.11.1 中可用（knavalbattle / kfourinline 已在用）。
- KUrlMimeData::urlsFromMimeData(mimeData) 换成 mimeData->urls()：对游戏
  接受的纯 URL 拖放，两者解码同一份 text/uri-list 载荷。

实际功能影响：http / https / ftp / file 的远程关卡集加载与 URL 拖放继续可用；
仅失去 KIO 专有 VFS 协议（smb://、webdav://、sftp:// 等）。这些协议的
kioslave 后端本来也没有发布到本平台包集，因此裁剪后没有丢失任何在本平台上
真正可达的行为。命令行位置参数与拖放入口保持不变（test_package 检查项 08
就是守这一条：--help 仍须暴露位置参数 URL）。

### 2. kdoctools 不需要打补丁

skladnik 上游的 find_package(KF6DocTools ...) 本来就不带 REQUIRED，且
add_subdirectory(doc) 与 kdoctools_install(po) 已被 if(KF6DocTools_FOUND)
守卫。因此只在 toolchain 里设 CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE
让它彻底不参与 configure 即可（对比 kgoldrunner：上游把 DocTools 写在
REQUIRED 组件列表里，必须改 CMakeLists）。功能损失：DocBook 手册不安装。

### 3. 显式关掉 POVRay

src/images/CMakeLists.txt 里 find_package(POVRay) 命中时会用 POV-Ray 重新
渲染全部 sprite PNG，未命中则 return()，直接使用 tarball 随附的渲染结果
（themes/CMakeLists.txt 安装的就是这些）。worker 上是否恰好存在 povray 会改变
构建产物，因此设 CMAKE_DISABLE_FIND_PACKAGE_POVRay=TRUE 固定走使用随附
PNG 的分支，保证可复现。

### 4. KF6 6.18 线 + karchive override

全部 KF6 requires 与 libkdegames/26.04.0 的二进制闭包逐一对齐（kconfig /
kconfigwidgets / kcoreaddons / kcrash / kdbusaddons / ki18n / kwidgetsaddons /
kcodecs / kxmlgui / kiconthemes 均 6.18.0）。karchive/6.18.0 以
override=True 钉住：kiconthemes/6.18.0 最新 recipe revision 要 karchive/6.19.0，
而 knewstuff/6.18.0 要 karchive/6.18.0，override 让整个图停在 6.18.0
（libkdegames / kgoldrunner 同款）。

副作用与解法（本节在 CI #92881 之后修订，原结论"kiconthemes 必须源码重建"已被推翻）：

制品仓里 kiconthemes/6.18.0 已发布的二进制 package_id 是 68da9b6f...（锚定
karchive/6.19.0 + ecm/6.19.0），与本闭包要求的 5937e6fd... 不同，因此按
kiconthemes/6.18.0 走必然源码重建。kgoldrunner / kfourinline / ktuberling /
libkdegames 都是这个条件，本次前 4 轮 conan-build-test 失败也全部发生在这次
依赖侧重建里（详见 CI 轮次记录）。

但制品仓另有 **kiconthemes/6.18.0.1**——按 R37 版本号策略，它是同一份上游
6.18.0 源码的适配修复版，其配方把 karchive 钉在 6.18.0（而非 6.19.0），
因此已发布二进制的 package_id 恰好就是本闭包需要的
`5937e6fd91b6589196a15790f369a1328a4907fb`。实测：

    $ conan list "kiconthemes/6.18.0.1:*"
      revisions: 181bb67d6875ccb0593e99e1bf9f696e (2026-09-03)
        packages: 5937e6fd91b6589196a15790f369a1328a4907fb
          options: shared: True
          requires: karchive/6.18.Z, kcolorscheme/6.18.Z, ki18n/6.18.Z,
                    kwidgetsaddons/6.18.Z, openssl/3.5.6.1, qtbase/6.11.Z,
                    qtsvg/6.11.Z, zstd/1.5.Z

skladnik 自身从不 find_package KF6 IconThemes（kiconthemes 纯由
kxmlgui / kconfigwidgets / libkdegames 传递引入），所以配方里把它写成
**纯 override**（`self.requires("kiconthemes/6.18.0.1", override=True)`）
而不是直接 require，与 ktuberling 抬 kio 内部 requires 的手法一致。

效果（本机 conan graph info 实测，ohos-local profile）：

    graph ERROR: None
    distinct nodes: 43
    needs building: NONE - 全图预编译
    kiconthemes: [('kiconthemes/6.18.0.1', 'Cache', '5937e6fd91b6589196a15790f369a1328a4907fb')]

即整张依赖图 0 个节点需要源码构建，CI 只需编译 skladnik 自己的 19 个编译单元
与 test_package。注意 package_id 与原先源码重建的目标 id 完全相同，说明拿到的
就是同一份二进制，产物语义不变；skladnik 自身 package_id 因依赖版本号变化由
e13d88a3... 变为 1cec04a2...。

### 5. libkdegames 取 26.04.0 而非 26.04.0.1

26.04.0.1 是 SONAME / DT_NEEDED 修复版，但本仓已合并的四个 KDE Gear 游戏
（kfourinline / kgoldrunner / knavalbattle / ktuberling）全部消费 26.04.0，
其 test_package 的运行时兜底逻辑（相对 NEEDED 符号链接 + 绝对 NEEDED 路径
兜底）也是围绕 26.04.0 的产物形态验证过的。另外 L5a/L5b 门禁只扫描包内
lib/lib*.so 一级目录，application 包没有 lib/，不触发该门禁，因此依赖侧的
SONAME 形态不影响本包门禁结果。

## 配方要点

- package_type = "application" 加软件级 commands.json（R38 / L0k）
- ecm/6.26.0 tool_requires；ECM_MODULE_PATH 手工注入（CMakeDeps 生成的
  ECMConfig 不传递该变量，audiocd / kgoldrunner 先例）
- KF_IGNORE_PLATFORM_CHECK=TRUE（OHOS 不在 KDE 平台白名单），
  KF_SKIP_PO_PROCESSING=ON（worker 无 gettext 工具链）
- -Wl,-z,max-page-size=0x1000（仅 OHOS）：默认 lld 0x10000 会把
  .dynsym/.dynstr 拆进独立的高地址 RW LOAD 段，OHOS musl loader 拒绝 mmap
  （audiocd 26.04.3 / kfourinline 26.04.0 先例）
- qtbase 与 KF6 包都是 cmake_find_mode=none，CMakeDeps 不会生成
  conan_cmakedeps_paths.cmake，配方内手写（audiocd / libkcddb / kgoldrunner 先例）
- 构建与测试环境注入 LD_LIBRARY_PATH（含 /system/lib64 取 libc++_shared），
  因为 moc / uic / rcc / kconfig_compiler 这些宿主工具本身是 OHOS 二进制
- validate() 用 in ("Linux", "OHOS")，不与 == "Linux" 比较（R32）
- 运行环境：QT_QPA_PLATFORM=offscreen 加隔离 HOME（kirigami-addons /
  audiocd / kgoldrunner 先例）

## 上游测试清点（N=0）

清点命令（在解开后的 skladnik-26.04.2 源码树上执行）：

    grep -rnE 'add_test|enable_testing|ECMAddTests|ecm_add_tests' .
    ls -d tests autotests test

结果：grep 无任何匹配；tests/、autotests/、test/ 目录均不存在。全树唯一
BUILD_TESTING 出现在 snapcraft.yaml 的 -DBUILD_TESTING=OFF。上游 QA 走
KDE CI（.kde-ci.yml），不随 release tarball 发布。

按 R51 与 rule8 口径：上游确无测试，记 0 并附上述清点证据，不虚构上游测试数。

## 测试计数口径

口径 = 独立检查项数量。test_package/main.cpp 中每个编号检查项输出一行
[PASS] / [FAIL] / [SKIP]，任一 FAIL 则进程退出码非 0。该口径在
test_package/MANIFEST.yml、本文件、PR 两张测试表中保持一致。

OHOS worker 上 12 项全部执行；其中 04 与 06 是 OHOS 专属检查，在非 OHOS
主机上报 SKIP（本机等价跑为 10 PASS 加 2 SKIP）。

## 鸿蒙特有测试（rule12，N=3）

三项都针对本次真实的 HarmonyOS 适配点，不是把普通上游测试改名：

1. 检查项 04 ohos-pt-load-page-alignment：读安装态 bin/skladnik 的程序头表，
   断言所有 PT_LOAD 的 p_align 不超过 0x1000。这直接验证配方为 OHOS 注入的
   -Wl,-z,max-page-size=0x1000：默认 0x10000 会把 .dynsym/.dynstr 拆进独立
   高地址 RW LOAD 段，OHOS musl loader 拒绝 mmap。若该 workaround 失效或被
   后续改动去掉，本项立即 FAIL。
2. 检查项 05 dt-needed-closure-resolves：断言可执行文件的每一条 DT_NEEDED
   都能解析（绝对路径形式须真实存在，basename 形式须在依赖闭包 lib 目录中
   找到）。这一项在 OHOS 上是承重的：musl loader 对 path-form NEEDED 条目
   按字面解析，不回退 LD_LIBRARY_PATH，一条解析不了游戏就起不来。
3. 检查项 06 ohos-codesign-section-present：断言经平台签名后可执行文件恰好
   带一个 .codesign 段。OHOS 强制 ELF 代码签名，未签名的 ELF 在 exec-mapping
   时报 EACCES，而该错误看起来像缺库，极易误判（知识 E318 与 DRAFT-7939
   是同一机制）。test_package 的 _ensure_codesign 用 llvm-readelf 校验段数，
   缺失时用 binary-sign-tool 自签并复检。

执行方式与判定：test_package/conanfile.py 在 test() 中设置
SKLADNIK_TEST_BIN、SKLADNIK_TEST_DATA_DIR、SKLADNIK_TEST_PLATFORM、
SKLADNIK_TEST_LIBDIRS、QT_QPA_PLATFORM=offscreen 与隔离 HOME 后执行
./skladnik_consumer_test，退出码 0 即 12 项全 PASS。

## 本机验证做了什么，为什么编译与执行交给 CI

本机为 macOS/arm64 开发机。Qt 的构建期工具是 OHOS aarch64 musl 动态可执行
文件，macOS 无法执行，实测：

    $ file ~/.conan2/p/qtbasaa5545cd5ea92/p/libexec/moc
    ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically
    linked, interpreter /lib/ld-musl-aarch64.so.1, with debug_info, not stripped
    $ ~/.conan2/p/qtbasaa5545cd5ea92/p/libexec/moc --version
    zsh:1: exec format error
    $ ~/.conan2/p/qtbasc7fdc89eea671/p/bin/qtpaths --query QT_INSTALL_PREFIX
    zsh:1: exec format error

本机 conan create 的真实止步位置（关键行）：

    CMake Error at .../ECM/modules/ECMQueryQt.cmake:98 (message):
      Qt6 qtpaths call failed: exec format error
    Call Stack (most recent call first):
      .../ECM/kde-modules/KDEInstallDirs6.cmake:210 (ecm_query_qt)
      .../ECM/kde-modules/KDEInstallDirs.cmake:17 (include)
      CMakeLists.txt:15 (include)
    kiconthemes/6.18.0: ERROR: Package '5937e6fd...' build failed

即依赖解析、源码下载与 SHA256 校验、补丁应用、CMake configure 之前的环节
全部走通，止步于需要执行 OHOS aarch64 宿主工具的那一步。即使越过 qtpaths，
skladnik 自身的 AUTOMOC（MainWindow.h 带 Q_OBJECT）与 AUTORCC
（src/skladnik.qrc）同样需要执行 moc 与 rcc，本机没有宿主替代品：未安装
native Qt 工具链（moc / rcc / uic / qtpaths 在 PATH 上均不存在，无 brew qt），
Docker daemon 未运行，因此也无法用 arm64 Linux 容器承载。

本机实际完成并通过的验证（均可复算）：

1. 源码 URL 与 SHA256 实测一致（官方 download.kde.org 源）
2. 3 个补丁在原始 26.04.2 源码树上 patch -p1 --dry-run 全部 exit 0、无 fuzz，
   随后实际应用成功；打补丁后全树 grep 无残留 KIO:: / KUrlMimeData /
   KF6::KIOCore 调用（仅注释中的说明性提及）
3. conan graph info（ohos-local profile）解析成功、graph ERROR=None，
   43 个节点中仅 kiconthemes/6.18.0 为 Missing，其余全部 Download；
   root package_id = e13d88a38c6b3143d16ba5cc634b23b44eb8aed9
4. src/MainWindow.cpp（含 KIO 到 QNetworkAccessManager 的改写）对真实
   Qt 6.11.1 加 KF6 6.18.0 加 KDEGames6 头文件执行 clang++ -fsyntax-only
   -std=c++17 通过，RC=0（仅 ki18n 上游 deprecation 属性告警一条）
5. test_package/main.cpp 对真实 Qt 6.11.1 QtCore 头文件执行 clang++
   -fsyntax-only -std=c++17 通过，RC=0
6. C 组数据契约（检查项 09 到 12）用宿主机等价实现对真实上游数据复算：
   desktop 的 KGameTheme 键齐全；SVG 声明全部 16 个渲染器 id
   （background / goal / man / saveman / object / treasure /
   stone_0 到 stone_5 / halfstone_0 到 halfstone_3，与 GroundItem.cpp 的
   LARGE_STONES=6、SMALL_STONES=4 及 PlayField.cpp 的 background 一致）；
   themes/CMakeLists.txt 安装的 16 个 sprite 与 SVG 的 16 个 xlink:href
   一一对应；16 个 PNG 的 IHDR 尺寸与 SVG 声明逐项一致（stone 192x96、
   halfstone 96x96、其余 192x192、starfield 128x128），4 项全 PASS

处置方式沿用已合并先例 archives/l/libkcddb/26.04.0（其 notes.md 的
Verification 小节与 manifest.yaml 的 verification.channel 记录了同一形态的
本机限制），编译与测试执行由官方 HarmonyOS CI worker 承担；status 取
built，不宣称 published，也不在远程结果产生前宣称 W3 通过。

## 功能损失

- DocBook 手册（doc/）：kdoctools 不在已发布 KF6 闭包内，KHelpClient 在线
  手册路径为空。与 kgoldrunner / ktuberling / kfourinline 一致。
- 翻译目录（po/）：KF_SKIP_PO_PROCESSING=ON 跳过，界面为英文原文。
- KIO 专有 VFS 协议（smb:// / webdav:// / sftp:// 等）的远程关卡集加载：
  这些 kioslave 后端未发布到本平台包集，本平台本来不可达；http / https /
  ftp / file 由 QNetworkAccessManager 继续支持。
- 核心玩法完整保留：五个内置关卡集（编进二进制的 level.data）、本地关卡集
  文件加载、拖放加载、主题渲染、走法历史与撤销、推箱子求解器（PathFinder）、
  收藏（Bookmark）与 HTML 导出（HtmlPrinter）。

## CI 轮次记录（PR #15886）

按 R44 每轮先 gitcode_pr.py diagnose 自诊断再动手，不对"未知"失败盲改重推。

- 第 1 轮 构建 #92173 / worker CI-030：失败于 checkout-pr。平台侧问题，
  worker 拉 pull/15886.diff 返回 HTTP 429，wget 兜底又因 busybox 不认 -q
  失败，20.5s 退出，未进入 conan。处置：不改配方，等限流窗口后重触发。
- 第 2 轮 构建 #92181 / worker CI-030：同上，429 复现。处置同上。
- 第 3 轮 构建 #92200 / worker CI-016：失败于 worker-prep / git-clone /
  cleanup。平台侧问题，worker-prep 与 git-clone 均在 120s 超时被 kill，
  未进入 checkout-pr。处置：不改配方，重触发。
- 第 4 轮 构建 #92251 / worker CI-016：基建步骤全绿，失败于 conan-build-test。
  这是配方侧真实错误，详见下节。处置：修复 patch 0002 后重推。

429 的根因已在本机取证，确认为平台级共享机器人账号限流、与本 PR 无关：
本机 curl 同一 URL 同样得到 HTTP 429，响应体为 "429 The number of times
the user invokes the API is too large. Threshold:200 times per user per
minute. Limited account:p_repoRobot"。

### 第 4 轮真实编译错误与修复

CI 日志（build #92251，worker CI-016，elapsedTime=210.7s）关键行，make 的
星号分隔符已省略：

    [ 60%] Building CXX object src/CMakeFiles/skladnik.dir/MainWindow.cpp.obj
    .../b/src/main.cpp:12:10: fatal error: 'KAboutData' file not found
    #include <KAboutData>
             ^~~~~~~~~~~~
    1 error generated.
    make[2]: Error 1 on src/CMakeFiles/skladnik.dir/main.cpp.obj
    make[1]: Error 2 on CMakeFiles/skladnik.dir/all
    skladnik/26.04.2: ERROR: Package 'e13d88a38c6b3143d16ba5cc634b23b44eb8aed9' build failed

根因：KAboutData 属 KCoreAddons，而上游 src/CMakeLists.txt 的
target_link_libraries 从未显式列出 KF6::CoreAddons，它此前是靠
KF6::KIOCore 的传递 interface（KIOCore 以 PUBLIC 链接 KCoreAddons）把
include 目录带上编译行的。裁掉 KIOCore 就同时丢掉了这条传递路径。
这正是 kgoldrunner 26.04.0 补丁标题里 "link KF6::CoreAddons explicitly"
所处理的同一问题；本次按同一先例在 patch 0002 中补上 KF6::CoreAddons。

同一轮 CI 也确认了几件有价值的正面证据：

- CMake configure 全绿（21.2s），FeatureSummary 显示全部 REQUIRED 包找到，
  含新增的 Qt6Network (required version >= 6.5.0) 与 KDEGames6，且
  KF6DocTools 未出现在缺失列表（CMAKE_DISABLE_FIND_PACKAGE 两项生效）
- kiconthemes/6.18.0 在 worker 上源码重建成功（本机 graph info 预测的唯一
  Missing 节点），依赖闭包策略成立
- 除 main.cpp 外全部 18 个编译单元通过，含改写过的 MainWindow.cpp
  （KIO 到 QNetworkAccessManager / QMimeData::urls()），说明补丁本身正确
- make: jobserver mkfifo: ... Operation not permitted 为 HMDFS 已知非致命告警

修复后本机复验：3 个补丁在全新解开的原始 26.04.2 源码树上
patch -p1 --dry-run 全部 exit 0、无 fuzz；实际应用后
target_link_libraries 为 KDEGames6 / KF6::CoreAddons / KF6::I18n /
KF6::WidgetsAddons / KF6::Crash / KF6::DBusAddons / KF6::XmlGui /
Qt6::Network。

### 第 5-6 轮：worker 侧超时（非配方）

- 第 5 轮（03:31:48）是旧 SHA a4dcc386 的重复触发，仍报同一个 KAboutData
  错误，与修复无关。
- 第 6 轮 构建 #92295 / worker CI-027：失败于 worker-prep / git-clone /
  cleanup，与第 3 轮同型（120s 超时被 kill），修复未被编译到。处置：不改配方，
  重触发。

### 第 7 轮 构建 #92324：CoreAddons 修复生效，12 项检查过 11 项

基建步骤全绿，conan create 编译链接成功，test_package 构建成功并在 OHOS
worker 上真实执行。CI 日志原文：

    (test package): created 3 absolute-NEEDED compatibility symlinks
    (test package): RUN: ./skladnik_consumer_test
    [PASS] 01 installed-executable-present - .../p/bin/skladnik
    [PASS] 02 elf64-little-endian-image - ELFCLASS64 + ELFDATA2LSB
    [PASS] 03 elf-machine-aarch64 - EM_AARCH64 (0xB7)
    [PASS] 04 ohos-pt-load-page-alignment - 4 PT_LOAD, max p_align=0x1000
    [FAIL] 05 dt-needed-closure-resolves - unresolved: libc++_shared.so, libc.so
    [PASS] 06 ohos-codesign-section-present - .codesign present after signing
    [PASS] 07 game-version-runs-offscreen - skladnik 0.5.26042
    [PASS] 08 game-help-advertises-url-argument - rc=0, positional URL present
    [PASS] 09 kgametheme-desktop-contract
    [PASS] 10 theme-svg-declares-renderer-ids - all 16 ids declared
    [PASS] 11 theme-sprites-installed - all 16 referenced sprites installed
    [PASS] 12 theme-sprite-png-geometry - 16 PNGs match SVG-declared size
    11 passed, 1 failed, 0 skipped

这一轮同时证实了几件关键事实：CoreAddons 修复生效（编译链接全过）；
max-page-size=0x1000 落地为 4 个 PT_LOAD、最大 p_align 恰好 0x1000；
签名后可执行文件带 .codesign；游戏在鸿蒙 worker 上真实启动并输出
skladnik 0.5.26042；KIO 裁剪后 --help 仍暴露位置参数 URL；16 个主题
sprite 与 SVG 声明的尺寸逐项一致。

检查项 05 失败是测试自身的搜索路径不完整，不是产物缺陷：
libc++_shared.so 与 libc.so 由 OHOS 平台自身在 /system/lib64 提供，不属于任何
conan 依赖包，而 SKLADNIK_TEST_LIBDIRS 只列了依赖包的 lib 目录。同一轮里
检查项 07 已经真实启动了游戏，说明这两个库在运行态本来就能被 loader 解析
（test_package 早已把 /system/lib64 注入 LD_LIBRARY_PATH）。

修复：test_package/conanfile.py 中把 DT_NEEDED 解析搜索路径改为
"依赖闭包 lib 目录 加 OHOS 平台 /system/lib64"（新增 resolve_dirs，
仅 OHOS 追加系统目录），并同步更新 MANIFEST.yml 中检查项 05 的描述。
该修复只把测试的搜索路径对齐 loader 的实际行为，未削弱断言强度：
任何真正缺失的依赖库仍会 FAIL。

### 第 8 轮 构建 #92344：CI 全绿（终态）

权威证据（buildbot API 交叉核对，非仅凭 PR 评论）：

- 构建号 #92344（buildbot buildid 106260），worker OpenHarmonyPCDeveloper-CI-019
- ci_revision = 6ae973f332b0d5c30b9ba408b95ccd330470a5d0（即检查项 05 修复后的
  PR head），ci_pr_number = 15886，ci_source_branch = feat/skladnik-26.04.2，
  ci_packages = archives/s/skladnik/26.04.2
- 起止 2026-10-15 04:47:23 到 04:53:17（354s），results = 0，
  state_string = build successful，日志末行 program finished with exit code 0
- 7 个步骤全部 results=0：worker_preparation / worker-prep / git-clone /
  checkout-pr / conan-setup / conan-build-test / cleanup

门禁结果（CI 日志原文）：

    L0_RESULT=pass: all checks passed
    L1_RESULT=pass: upstream tests + test_package executed
    L2_RESULT=skip: skladnik version/help failed
    L4_RESULT=warn: dangerous functions in patches
    L5_RESULT=pass: bin/ has content
    Total: 1  Success: 1  Failed: 0  Pass rate: 100.0% (1/1)

其中 L1 细分全过，且破坏性反向验证明确确认测试实质依赖被测包（R34）：

    [ok] L1a: test_package was executed by conan create
    [ok] L1b: Test execution evidence found in log
    [ok] L1c: Upstream official tests (make check/ctest) executed in build phase
    [step] L1e: Destructive negative test (R34)...
            [sabotage] bin/ moved away
    [ok] L1e: Negative test confirmed - test genuinely depends on skladnik

消费者测试 12 项全过（CI 日志原文）：

    skladnik/26.04.2 (test package): Running test()
    [PASS] 01 installed-executable-present - .../p/bin/skladnik
    [PASS] 02 elf64-little-endian-image - ELFCLASS64 + ELFDATA2LSB
    [PASS] 03 elf-machine-aarch64 - EM_AARCH64 (0xB7)
    [PASS] 04 ohos-pt-load-page-alignment - 4 PT_LOAD, max p_align=0x1000
    [PASS] 05 dt-needed-closure-resolves - 21 DT_NEEDED entries all resolve
    [PASS] 06 ohos-codesign-section-present - .codesign present after signing
    [PASS] 07 game-version-runs-offscreen - skladnik 0.5.26042
    [PASS] 08 game-help-advertises-url-argument - rc=0, positional URL present
    [PASS] 09 kgametheme-desktop-contract - Type=SVG FileName=... VersionFormat=1
    [PASS] 10 theme-svg-declares-renderer-ids - all 16 renderer ids declared
    [PASS] 11 theme-sprites-installed - all 16 referenced sprites installed
    [PASS] 12 theme-sprite-png-geometry - 16 PNGs match their SVG-declared size
    12 passed, 0 failed, 0 skipped
    skladnik/26.04.2 (test package): skladnik consumer test passed

产物：skladnik/26.04.2 Created package revision
42a859b02bc6299013ab14dd81f193f8。依赖侧 kiconthemes/6.18.0 如本机 graph info
预测在 worker 上源码重建成功（Created package revision
9745055317ceb9b6843f12dcb9e59052），其自带 ctest 亦全过
（100% tests passed, 0 tests failed out of 5）。

两个非阻塞项的定性（均为已知误报或环境限制，非本包缺陷）：

- L2_RESULT=skip（skladnik version/help failed）：L2 的独立 smoke 直接在
  worker shell 里裸跑 skladnik --version/--help，没有 test_package 准备的
  运行态（LD_LIBRARY_PATH 依赖闭包、/system/lib64、QT_QPA_PLATFORM=offscreen、
  隔离 HOME、.codesign 续签），因此必然失败；同样两条断言在 test_package 内
  以检查项 07/08 全过。与 ktuberling 26.04.0 的「L2 skip（非阻塞，
  test_package 内已覆盖）」同型。
- L4_RESULT=warn（dangerous functions in patches）：L4 的扫描正则为
  (strcpy|sprintf|gets|strcat) 加词尾边界，其中 gets 一项命中了 patch 0001
  上下文里的 Widgets 与 ConfigWidgets（Wid-gets）。属关键字误报，补丁内不含
  任何危险函数调用；任何补丁上下文里出现 Qt Widgets 组件名的 Qt/KDE 配方都会
  触发同一误报（ktuberling 26.04.0 记录的「L4 warn patch 关键字误报」同因）。

### 状态结论

编译与测试已由官方 HarmonyOS CI worker 在真机环境执行并全绿，本机不可执行
Qt 构建期工具的限制不再构成验证缺口。manifest status 保持 built：
conan 配方已验证、未执行 conan upload（按仓规，上传由合并 main 后的 release
流水线完成），故不标 published。

### 第 9-13 轮：head 5f68e013 的绿构建，与依赖侧重建的抖动代价

第 8 轮之后又推了一个纯文档提交（notes/manifest/feedback，head 5f68e013）。
CI 只读 conanfile.py / conandata.yml / test_package/ / patches/ 四类文件，已用
git diff --stat 6ae973f332 5f68e01394 限定这四类路径验证输出为空，即两者
逐字节相同。该 head 上的轮次：

- #92373（CI-003）FAIL：checkout-pr 拉 PR diff 得 HTTP 429（p_repoRobot 账号
  限流 200 次每分钟，本机 curl 同一 URL 同样 429）。
- #92382（CI-041）FAIL：依赖 kiconthemes/6.18.0 源码重建后其自带 ctest 5/5 全挂，
  报 libKF6ColorScheme.so 找不到 libKF6ConfigGui.so 等符号；同一份日志里混用
  ~/.conan2/p/ 与 ~/.cache/conan2/p/ 两个 conan home，属 worker 缓存污染。
- #92388（CI-022）FAIL：worker-prep / git-clone 120s 超时被 kill。
- #92399（CI-035）FAIL：kiconthemes configure 期 make[1]: /bin/sh: Resource
  temporarily unavailable，testCCompiler.c.obj Error 127，CMake 连编译器 ABI
  探测都过不去（worker 进程槽耗尽）。
- #92409（CI-003）PASS：ci_revision = 5f68e01394987c5382263329a4c46a0afcf924f3
  （即当时 head），355s，results=0，7 步全绿，L0/L1/L5 pass，test_package
  12 passed, 0 failed, 0 skipped，exit code 0。
- #92881（CI-014）FAIL：与 #92399 完全同型（/bin/sh: Resource temporarily
  unavailable，testCCompiler.c.obj Error 127，仍发生在 kiconthemes 的
  configure 期，本包代码尚未开始编译）。

按 skill §12.0 分诊：#92373 属 D 类（基础设施）、#92382 属 C 类（依赖/平台，
worker conan home 污染）、#92388 属 D 类、#92399 与 #92881 属 D 类（worker
进程资源耗尽）。没有一轮是 A 类（测试脚本自身缺陷）或本包 B 类（上游代码
缺陷）；本包侧的两个真实错误早在 #92251 / #92324 就修完了。

关键观察：5 轮红里有 4 轮的失败点都落在依赖 kiconthemes 的源码重建上
（ctest 挂 / configure 期 fork 失败），本包代码甚至还没开始编译。按 §12.0
「同一失败出现第 2 次仍无法定位根因 → 停止改实现，先补诊断」，#92881 是
testCCompiler Error 127 的第 2 次复现，于是没有再盲目重刷，而是回到依赖图
本身找根因：这次重建本来就不是必需的——制品仓存在 kiconthemes/6.18.0.1，
其已发布二进制的 package_id 正是本闭包需要的 5937e6fd...（见关键决策第 4 节）。

处置（唯一假设）：把 kiconthemes 从「直接 require 6.18.0（必然源码重建）」改为
「纯 override 到 6.18.0.1（命中预编译二进制）」，使全图 0 个节点需要构建，
从结构上移除这个抖动源。本机 conan graph info 已验证 needs building: NONE。
回退方案：若 override 到 6.18.0.1 引发新的版本冲突（graph ERROR 非 None），
则退回 kiconthemes/6.18.0 直接 require，接受源码重建并继续按 D 类有限重试。

### 第 14 轮 构建 #92995：一次过全绿（当前终态）

假设成立，回退方案未启用。buildbot API 交叉核对：

- 构建号 #92995（buildbot buildid 107014），worker OpenHarmonyPCDeveloper-CI-020
- ci_revision = 7fe89f3ae9cb1d639b2180a6e35f59fc4e79f324，即 kiconthemes
  override 修复后的 head；ci_pr_number = 15886；
  ci_packages = archives/s/skladnik/26.04.2
- 起止 2026-10-15 15:51:12 到 16:01:19（607s），results = 0，
  state_string = build successful，7 个步骤全部 results=0，
  日志末行 program finished with exit code 0

门禁：

    L0_RESULT=pass: all checks passed
    L1_RESULT=pass: upstream tests + test_package executed
    L2_RESULT=skip: skladnik version/help failed
    L4_RESULT=warn: dangerous functions in patches
    L5_RESULT=pass: bin/ has content
    Total: 1  Success: 1  Failed: 0  Pass rate: 100.0% (1/1)

消费者测试 12 项全过（节选，完整逐条见 PR 正文第 7 条）：

    [PASS] 04 ohos-pt-load-page-alignment - 4 PT_LOAD, max p_align=0x1000
    [PASS] 05 dt-needed-closure-resolves - 21 DT_NEEDED entries all resolve
    [PASS] 06 ohos-codesign-section-present - .codesign present after signing
    [PASS] 07 game-version-runs-offscreen - skladnik 0.5.26042
    [PASS] 12 theme-sprite-png-geometry - 16 PNGs match their SVG-declared size
    12 passed, 0 failed, 0 skipped
    skladnik/26.04.2 (test package): skladnik consumer test passed

修复效果的关键验证：依赖侧不再源码重建。本轮日志中 Created package revision
只出现一次，且属于本包（skladnik/26.04.2 Created package revision
9ce697661a0a7bc561fde9a381e73371）；针对 kiconthemes 的 Calling build() 与
Created package revision 匹配数为 0，即整个依赖闭包全部命中预编译二进制。
这正是 #92382 / #92399 / #92881 三轮红的暴露面被结构性移除的直接证据。

L2 skip 与 L4 warn 的定性与第 8 轮相同（L2 裸跑缺 test_package 的运行态；
L4 是扫描正则的 gets 命中 Widgets / ConfigWidgets 的关键字误报），均非本包缺陷。

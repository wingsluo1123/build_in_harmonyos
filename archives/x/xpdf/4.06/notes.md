# xpdf 4.06 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 库 / 版本 | xpdf / 4.06 |
| 上游 URL | https://dl.xpdfreader.com/xpdf-4.06.tar.gz （软件本体，非镜像/fork） |
| sha256 | `1c38f527c46caee0f712386d42a885b96a31ed9ce11904e872559859894d137e`（999317 字节，Mac 侧实测） |
| 上游发布日期 | 2025-11-14（当前主线） |
| 许可 | GPL（xpdf 是 Glyph & Cog 的商业授权产品，此处为免费版本） |
| 构建系统 | CMake ≥3.10（`CMakeLists.txt` → `cmake-config.txt` → goo/fofi/splash/xpdf/xpdf-qt） |
| 语言 | 纯 C++（实测 `.cc` 102 / `.h` 106 / `.c` **1**，唯一 `.c` 是 `goo/parseargs.c`） |
| 难度定级 | **B**（需 CMake 选项裁剪 + 平台系统名纠正 + 真实 CLI 消费者测试，见下） |

## 依赖（拓扑序，已在制品仓核对）

```
zlib/1.3.1.1  →  libpng/1.6.58  →  freetype/2.14.3
                libtiff/4.7.2（zlib/jpeg/zstd… 二级依赖制品仓已有）
                lcms2/2.19
                fontconfig/2.18.1.1（→ freetype/2.14.3 + expat/2.8.2.1）
```
全部为制品仓已发布版本（registry 全量翻页 7497 行核对，见本卡评论）。
**Qt5 未列入 requires**：`qt5/5.15.19` 虽已发布，但它的用途是 GUI（见「降级边界」）。

## 交付面：只交 CLI 工具，不交 GUI

上游 `cmake-config.txt` 的探测结果决定构建哪些目标（实测）：

| 条件 | 影响 |
|---|---|
| 找不到 FreeType | 不建 pdftoppm / pdftopng / pdftohtml |
| 找不到 libpng | 不建 pdftopng / pdftohtml |
| 找不到 Qt4/5/6 | **不建 xpdf（GUI）** |
| 无多线程 或 无异常 | **不建 xpdf（GUI）** |

**降级边界（必须写明）**：本包**不交付 Qt GUI `xpdf` 可执行文件**。理由不是"平台没有 Qt"
——`qt5/5.15.19` 已在制品仓发布；而是 OHOS 上**没有 QPA 平台插件**（无 X11/Wayland），
GUI 即使链接成功也无法创建窗口。`archives/q/qt5/5.15.19/notes.md` 自身也记录
"仅核心库可用"、Qt 测试因运行时符号解析问题无法运行。

**保留功能全部有真实调用测试**：CLI 工具是本包的主体交付面，test_package 对
pdftotext / pdfinfo / pdffonts / pdfimages / pdfdetach 五个产物做真实调用
（17 项断言，实测 17/17，见 test_package/MANIFEST.yml），**不存在空壳**。

因为是 `package_type = "application"` 的 CLI 包，按 R38/PF8 补软件级
`archives/x/xpdf/commands.json`（`type=tool`，`ref=xpdf/4.06`）。

## 配方关键点

1. **`os=OHOS` 系统名纠正（带守卫）**：conan 把 `os=OHOS` 映射成
   `CMAKE_SYSTEM_NAME=HarmonyOS`，但 cmake 只装了 `Modules/Platform/OHOS.cmake`。
   名字对不上时 **cmake 不报错**，只打一句 "System is unknown to cmake" 就继续，
   于是 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空 → 链接缺 `-Wl,-soname,`，
   `CMAKE_SYSTEM_PROCESSOR` 留 `unknown` → 上游按它分支的 SIMD/汇编选择走错支。
   故设 `generic_system.cmake_system_name=OHOS` + `cmake_system_processor=aarch64`。
   **必须带 `if self.settings.os == "OHOS"` 守卫**：无条件设会在 os=Linux profile 上
   把 cmake 正确的平台识别顶掉（opencascade 7.9.3 MR 评审实撞）。
   本仓 205 处已合入配方用同一写法（eckit/ompl/ecbuild/orocos-kdl/taocpp-tuple/elk…）。

2. **`source()` 的 url 归一化**：CI 会把 conandata 的 `url` 改写成 `[镜像, 官方]` 列表，
   直接 `url.startswith(...)`/`urlparse(url)` 在 CI 会 `AttributeError`，而设备本地
   （字符串形态）全绿——这是"CI 独红、本地复现不了"的一类。入口先做
   `candidates = list(url) if isinstance(url, list) else [url]`，之后只用 `candidates[0]`。

3. **依赖 include/libdir 注入**：上游用裸库名链接（`-lfreetype`/`-lfontconfig`），
   没有 `-L` 会 `unable to find library`；只注入**搜索路径**与 `-I`，不追加 `-l`
   （追加会破坏上游链接分离，hwloc/poppler 实证）。freetype 需要两个 include 根
   （`ft2build.h` 与 `freetype/freetype.h`），全量注入可覆盖两种风格。

4. **C++ 标准**：上游 `cmake-config.txt` 硬编码 `set(CMAKE_CXX_STANDARD 11)`，
   而 OHOS profile 是 `cppstd=17`；显式传 11 让构建停在上游真正测过的语言级别，
   避免静默继承 profile 值。

5. **代码签名**：`package()` 后对 `bin/` 下 ELF 逐个 `llvm-objcopy --remove-section
   .codesign` + `binary-sign-tool sign -selfSign 1`。签名是内容哈希，**链接后再改字节即失效**；
   复制不破坏签名。方法内 `if self.settings.os != "OHOS": return` 守卫，
   否则在非 OHOS profile 上工具不存在会让 package 阶段整个崩掉。

## 上游测试面（R51 清点，实测非估算）

`find xpdf-4.06 -type d -name 'test*'` → **空**。全树无 ctest/pytest/gtest 注册，
xpdf 是 Glyph & Cog 的发布 tarball，**不随源码分发测试套件**。
故：上游自带测试用例数 = **0**（附清点证据），不存在"能跑未跑"的缺口。
声明的 17 项全部是本包新增的**消费者用例**。

## 被真实构建/检视/CI 纠正的多处错误（保留记录）

为避免后续复用踩坑，test_package/MANIFEST.yml 同步记录：

1. **`pdfimages -png` 在 xpdf 中不存在** —— 打印 usage 并以 **rc=99** 退出
   （`-png` 是 poppler 的选项）。xpdf 的 `pdfimages` 默认写 PPM。
   若照搬 poppler 经验写 `-png`，断言会"通过"（`|| true` 吞掉 rc）但实际零产出。
2. **无图像页面 `pdfimages` rc=0 但一个文件都不写** —— 空跑即"成功"，纯退出码断言会漏。
   故夹具改为内嵌真实 2x2 DeviceRGB FlateDecode 图像 XObject，
   并对 PPM 头（P6）、2x2 尺寸、像素载荷逐项断言。
3. **`[ -f "$WORK/detach.txt" ]` 断言恒真**（AI 检视 f43c32aa 于 2026-10-08 抓出，
   2026-10-09 修复）—— shell 在执行命令**之前**就因 `>` 重定向创建/截断目标文件，
   于是工具未安装（rc=127）、崩溃、零输出都判 PASS。实测对照：旧断言在 PATH 无
   pdfdetach 时 15/15 PASS（rc=0），新断言同环境 14/17（3 项 FAIL，rc=1）。
   修法 = `-n "$PDFDETACH"` 守卫 + stdout/stderr 分流 + `-s` 非空 + grep 上游确定串
   （`pdfdetach.cc:146-148`：`<n> embedded files` / `N: <name>`），并给夹具内嵌
   1 个真实附件（`/Names /EmbeddedFiles` 名字树）以支撑 `-save` 抽取 roundtrip 断言。

4. **`fontconfig/2.18.1` 的绝对路径 DT_NEEDED 让消费者 CLI 在 CI 加载期全线失败**（平台 CI #89064
   `conan-build-test` 暴露，2026-10-13 修复）——依赖包 `fontconfig/2.18.1` 的已发布
   `libfontconfig.so.1` 记录了**绝对路径** `DT_NEEDED`：`readelf -d` 实测为
   `NEEDED /…/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so`。成因是 `expat/2.8.2` 的 `.so`
   **无 SONAME**，链接器遇到无 SONAME 的被链库时把**绝对路径**写进 DT_NEEDED（见
   `archives/f/fontconfig/2.18.1.1/notes.md`）。OHOS/musl 加载器对含 `/` 的 NEEDED 按**字面路径**
   解析，`LD_LIBRARY_PATH` 无法覆盖；CI worker 的活跃 conan home 是 `~/.cache/conan2`，而绝对路径
   `~/.conan2/p/expat…` 处只有一份陈旧 expat → `Error loading shared library …` + 一串
   `XML_* symbol not found`，pdftotext/pdfinfo/pdffonts/pdfimages/pdfdetach 全部 rc≠0，
   test_package 14 项断言挂 11（passed: 3）。**设备本地不复现**（本地 conan home 恰为 `~/.conan2`，
   绝对路径处就是匹配的 expat）——属"CI 独红、本地复现不了"一类，非 test_package 的
   `LD_LIBRARY_PATH`/conanrun 构造问题（绝对 NEEDED 与 LD_LIBRARY_PATH 无关）。
   修法 = 依赖升到 `fontconfig/2.18.1.1`（改用 `expat/2.8.2.1` 重新链接，`readelf -d` 得到
   可重定位 `NEEDED libexpat.so.1`）。不跳过测试、不删断言。
   证据：`archives/f/fontconfig/2.18.1.1/notes.md`；本机 `readelf -d` 对照（2.18.1 绝对路径 vs
   2.18.1.1 `libexpat.so.1`）；CI 日志行 651–683。

## 编译状态

- **Mac 侧**（仅用于验证断言口径，**非交付构建**）：cmake 4.3.2 + Homebrew freetype2/libpng/zlib，
  5 个 CLI 目标构建成功，消费者测试 **17/17 通过**（2026-10-09 复跑，同版本 4.06 源码）。
  这证明源码与测试脚本本身自洽。
- **设备侧 `conan create`：已执行并通过（2026-10-08，阻塞解除后）**：
  设备通道恢复（registry 可达、7 个依赖二进制包下载成功、源码 tarball 由 conan
  正常下载），CI 同源脚本 `ci/conan/build_and_test.sh`（`CI_PACKAGES=archives/x/xpdf/4.06`）
  全绿：G0/KC/JC/L0（含 L0k commands.json type=tool）pass；9 个 CLI 产物全部编出
  （pdftotext/pdfinfo/pdffonts/pdfimages/pdfdetach/pdftops/pdftoppm/pdftopng/pdftohtml，
  逐个 binary-sign-tool 自签名成功）；test_package 通过；
  L1（含 L1e 破坏性反证）/L4/L5 pass，L2 为非阻塞性 skip（xpdf 系工具无
  --version/--help 长选项，-v 已覆盖）；Pass rate 100.0%。
- **设备侧复跑（2026-10-09，pdfdetach 断言改写后）**：同一 CI 同源脚本再次全绿 ——
  `BUILD_AND_TEST_RC=0`、G0（540 条图谱）/L0/L1/L4/L5 pass、L2 非阻塞 skip、
  **test_package 17/17**、`Pass rate 100.0% (1/1)`、`All packages built and tested
  successfully`；日志 `scratch/xpdf_create2_run.log`。
- 旧阻塞记录（MTU/TLS 黑洞）已失效，保留仅作历史：此前设备 `ping -s 1400` 100% 丢包、
  `conan list -r=ohpcd` 报 `SSLEOFError`，属外部阻塞非配方缺陷。

## 后续建议

- GUI `xpdf` 若要交付，需要先解决 QPA 平台插件（OHOS 无 X11/Wayland），
  属难度 C 的平台适配深度，不建议与 CLI 交付混在一个 PR。
- `pdftoppm/pdftopng/pdftohtml` 依赖 splash+libpng，理论可随 freetype/libpng 一起建出；
  设备侧首次构建（2026-10-08）已确认：9 个 CLI 目标**全部落地**（含 pdftoppm/pdftopng/pdftohtml）。

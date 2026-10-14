# unar 1.10.8 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile.linux，Objective-C 2.0 / GNUstep GNU runtime）
- 编译日期: 2026-10-08
- 编译器: clang/clang++（llvm-ar 归档）
- 状态: built（本地 W3 验证通过，待 CI）

## 编译步骤

```bash
# 1. 依赖（conan 制品仓，均已发布）
gnustep-base/1.31.1  wavpack/5.9.0  zlib/1.3.1.1  bzip2/1.0.8.2  icu/76.1

# 2. 应用 4 个补丁（patches/，见 conandata.yml）
# 3. 构建 libtzguard.so（conanfile.py build() 内联源码）
clang -shared -fPIC -O2 tzguard.c -o libtzguard.so

# 4. 主构建（conanfile.py 注入全部参数）
make -f Makefile.linux -j1 \
  OBJCC=clang CC=clang CXX=clang++ AR=llvm-ar \
  GCC_OPTS="-O2 -Wno-import -Wno-multichar -g -D_FILE_OFFSET_BITS=64 -isystem <gnustep-base>/Library/Headers" \
  GNUSTEP_OPTS="-DGNUSTEP -DGNU_RUNTIME=1 -fgnu-runtime -fexceptions -fconstant-string-class=NSConstantString" \
  CFLAGS="<依赖 include 集>" CXXFLAGS="<同>" OBJCFLAGS="<同>" \
  LDFLAGS="<依赖 lib 集> -L<build_folder>" \
  LIBS="-Wl,--no-whole-archive -ltzguard -lgnustep-base -lz -lbz2 -lwavpack -licuuc -licudata -lobjc -lm"
```

关键点：`-ltzguard` 必须位于 LIBS 首位（首个 DT_NEEDED，constructor 先于
libgnustep-base.so 的加载期时区解析执行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译失败：`getpass` 未声明（GNUSTEP 分支） | musl libc 无 getpass()（glibc 专有） | 补丁 0001：GNUSTEP 分支下提供交互式读取桩（仿非 GNUSTEP 分支的 fgets 回退，含 ECHO 关闭/恢复） |
| 2 | 编译失败：`REG_STARTEND` 未定义（XADRegex.m） | musl regex.h 无 GNU 扩展 REG_STARTEND | 补丁 0002：`#define REG_STARTEND 0`（musl 的 regexec 本就以 (rstart,rend) 解释 pmatch[0]，0 为等价 no-op） |
| 3 | tar.gz 嵌套档案静默失败：lsar 只显示 `Gzip/test.tar`、unar 把 tar 当普通文件解出 | XADRegex 把未 NUL 终止的 NSData bytes 直接传给 regexec()：musl 用 strlen 定界 → 越界读相邻堆字节 → `\.(tar\|...)$` 的 `$` 锚点失配。glibc 堆布局下碰巧读到近邻 NUL 而可用 | 补丁 0002：regexec 前拷贝到 NUL 终止缓冲区。实证：musl 原生 regexec 对 "test.tar" 匹配 OK；XADGzipParser 的扩展名识别（XADIsArchiveKey）依赖该正则 |
| 4 | 运行崩溃（zip 列表/解压）：`NSInvalidArgumentException: GSPlaceholderString-initWithString: given nil string` | 时区根因链：OHOS 无 TZ 环境变量 + 无 /etc/localtime + 无 /usr/lib/zoneinfo（/etc/zoneinfo 是 OHOS 自有格式，gnustep 读不懂）→ gnustep-base 的时区解析拿到 nil C 字符串 → 抛异常（GNUstep 的 stringWithUTF8String:nil 是主动 raise，非 Apple 式返回 nil）。zip 的 MSDOS 日期 → NSCalendarDate dateWithYear:... → 必崩 | 补丁 0003/0004：main() 入口 `if(!getenv("TZ") && 无 /etc/localtime && 无 /usr/lib/zoneinfo) setenv("TZ","UTC",0)`（#ifdef GNUSTEP 内，无平台宏） |
| 5 | 即使 main() 内 setenv(TZ=UTC)，嵌套档案路径仍异常 | gnustep-base 在**库加载期**（DT_INIT，早于 main）执行 getenv("TZ") 一次并固化结果（LD_PRELOAD 拦截实证：全进程仅 1 次调用）；main 内设置太迟 | libtzguard.so：constructor(101) 内做同样的 TZ 兜底；以 `-ltzguard` 首位链接保证加载顺序（NEEDED 顺序实证）。LD_PRELOAD 同逻辑验证可行后转为正式交付物 |
| 6 | `lsar -l` 长格式日期列显示 `(null)` | NSDateFormatter stringFromDate: 在 OHOS 返回 nil（与 TZ 无关：tzguard 生效、TZ=UTC 已设时仍如此；疑似 locale 数据相关，GNUstep 内部） | 已知限制，仅影响 `-l` 长格式日期显示，核心功能（列表/解压）不受影响，不阻塞 |
| 7 | conan create 报 `../UniversalDetector/UniversalDetector.h file not found` | XADMaster 的 GitHub tarball **不含** UniversalDetector（上游 README 要求两仓库并列 clone；XADString.m 硬引用 `../UniversalDetector/`，Makefile.linux 链接 `../UniversalDetector/libUniversalDetector.a`） | 配方 source() 双源获取：XADMaster v1.10.8 tarball（保留顶层目录不 strip）+ 官方 `MacPaw/universal-detector` tag 1.1 tarball，后者重命名为 `UniversalDetector/` 置于 XADMaster 源目录的父级（与上游开发目录布局一致；tag 1.1 与本地实测源码逐字节一致） |
| 8 | conan test 运行期 `Error loading shared library libobjc.so`（及潜在 libz.so） | Conan 2 图解析：`package_type="application"` 包对静态库依赖推断 `run=False` → 这些依赖在 test_package 图中被 BINARY_SKIP → 其 package_folder=None → 依赖自身 package_info 的 None 守卫静默跳过 lib 目录 → 消费者 LD_LIBRARY_PATH 缺 libobjc2/lib、zlib/lib（libgnustep-base.so 运行期 NEEDED libz.so/libobjc.so/libcurl.so） | 配方对运行时 .so 提供者显式 `run=True` 直接依赖（`zlib/1.3.1.1`、`libobjc2/2.2.1`）保证不进入 skip 集；package_info 汇总运行时搜索路径（自身 lib/ + gnustep Library/Libraries + zlib + curl + wavpack + libobjc2），并带 None 守卫防其他上下文崩溃 |
| 9 | conan test 报 `zip extraction missing file` | 测试预期错误（非产品缺陷）：unar 对扁平条目档案**平铺**解压到 -o 目录（`out/hello.txt`），不建档案基名子目录；嵌套档案（tar.gz）子目录前缀来自 tar 内部条目结构 | 修正 test.sh 预期为平铺路径 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-getpass-ohos-stub.patch | CommandLineCommon.m | GNUSTEP 分支 getpass 桩（musl 无此符号） |
| 0002-xadregex-musl-compat.patch | XADRegex.m | REG_STARTEND 回退定义 + regexec NUL 终止拷贝 |
| 0003-unar-default-tz-utc.patch | unar.m | main 入口 TZ=UTC 兜底（#ifdef GNUSTEP 内） |
| 0004-lsar-default-tz-utc.patch | lsar.m | 同上（lsar） |

另：`libtzguard.so` 源码内联于 conanfile.py（TZGUARD_SOURCE 常量），build() 时
生成并编译——非源码树文件，故不走 patches/。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| gnustep-base | 1.31.1 | Foundation/GNUstep 运行时（传递: libobjc2/2.2.1, libffi/3.5.2, curl/8.15.0） |
| wavpack | 5.9.0 | WavPack 音频解压缩支持（XADWinZipWavPackHandle） |
| zlib | 1.3.1.1 | 头文件 + 静态链接（本生态为 libz.a，二进制无 libz NEEDED；版本对齐 curl/8.15.0 的传递约束） |
| bzip2 | 1.0.8.2 | 仅头文件（CSBzip2Handle.h 需 bzlib.h；解压走 XADMaster 自带 BWT 算法） |
| icu | 76.1 | 头文件 + 静态链接（XADStringICU 编码转换，libicuuc.a/libicudata.a） |
| libobjc2 | 2.2.1（直接依赖，run=True） | Objective-C 运行时（libobjc.so）：unar/lsar 与 libgnustep-base.so 均 NEEDED；显式 run=True 保证 test 图不 skip（见问题 8） |
| universal-detector | 1.1（源码内置） | 字符集探测库（非 conan 包）：官方仓库 MacPaw/universal-detector，tarball 不含、由配方 source() 第二源获取并布局为 XADMaster 源目录的兄弟目录 |

## 验证结果

```bash
# 本地功能矩阵（干净环境：无 TZ 环境变量、无 LD_PRELOAD；6/6 通过）
lsar  test.tar.gz          # -> "Tar in Gzip" + a.txt/subdir/subdir/b.txt   OK
unar  -f -o out test.tar.gz # -> 解出 test/a.txt + test/subdir/b.txt        OK
lsar  pytest.zip           # -> Zip + a.txt + subdir/b.txt                  OK
unar  -f -o out pytest.zip  # -> 解出 pytest/a.txt + pytest/subdir/b.txt    OK
lsar  utf8flag.zip         # -> 中文文件名 测试文件.txt（UTF-8 flag 路径）  OK
unar  --version / lsar --version                                OK

# 根因验证探针（OHOS 本机）
[NSString stringWithUTF8String:nil]   # -> 抛 NSInvalidArgumentException（设计行为）
NSCalendarDate dateWithYear:...       # -> 无 TZ 时抛异常；TZ=UTC 时正常
TZ=Asia/Shanghai（无 zoneinfo 库）    # -> 仍抛异常（需标准 IANA 布局）
LD_PRELOAD 拦截 getenv("TZ")          # -> 全进程仅 1 次调用（加载期）
```

上游测试：无（tests/ 目录 0 个、Makefile.linux 无 check/test 目标、
.github/workflows 仅构建 + CodeQL——清点证据见 test_package/MANIFEST.yml）。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/unar | 解包 CLI |
| bin/lsar | 归档列表 CLI |
| lib/libtzguard.so | 加载期 TZ 兜底（须先于 libgnustep-base.so 加载） |
| licenses/LICENSE | LGPL-2.1 |

## 注意事项

1. **libtzguard.so 的链接顺序是正确性前提**：`-ltzguard` 必须在 LIBS 首位，
   否则 constructor 晚于 gnustep-base 加载期解析执行，时区兜底失效。
   验证手段：`llvm-readobj -d unar | grep NEEDED | head -1` 应为 libtzguard.so。
2. **已知限制**：`lsar -l` 长格式日期列显示 `(null)`（NSDateFormatter 在
   OHOS 返回 nil，仅显示层）；XADArchive.m:1114 的 dateWithCalendarFormat
   路径（XADMaster C API 消费者使用，CLI 不经过）存在同类时区风险，未触及。
3. GBK 等非 UTF-8 文件名 zip 的编码转换路径未专项验证（musl iconv 后端，
   上游 XADString 固定编码启发式），如 CI/后续使用发现问题再跟进。
4. 上游版本字符串不一致：tag 为 v1.10.8，但 unar.m:30 / lsar.m:31 硬编码
   `VERSION_STRING @"v1.10.7"`（上游未随 tag 更新），`unar --version` 输出
   v1.10.7。属上游外观问题，按最小改动原则不打补丁；conan 包版本 1.10.8
   与源码 sha256（conandata.yml）为版本真值。
---

**编译结束**: 2026-10-08 23:49
**最终状态**: built

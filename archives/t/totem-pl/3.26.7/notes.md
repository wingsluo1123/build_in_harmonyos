# totem-pl 3.26.7 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-10-16
- 编译器: clang/clang++（OHOS NDK clang 15.0.4）
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0, arch=armv8, Release, libc++）
- 状态: built

## 编译步骤

1. 源码核验：官方 GNOME 2026-04 重发版（meson 构建），SHA256 与上游
   download.gnome.org 发布的 .sha256sum 一致（conandata.yml 已固定）。
2. 配方构建：
   ```bash
   conan create archives/t/totem-pl/3.26.7 \
     -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
   ```
3. 配方 generate() 关键注入（详见 conanfile.py 注释）：
   - `introspection=false`（CI 无 GI 工具链）
   - ar/as/strip/nm/ranlib 绝对路径钉扎（CI worker 导出的 llvm-* 环境变量名不在
     PATH，同 gstreamer 1.28.3 模式）
   - 向生成的 glib-2.0.pc 注入 `glib_mkenums`/`glib_genmarshal` 变量
     （PkgConfigDeps 生成的 .pc 缺这两个下划线变量，meson gnome 模块按名查找）
   - C 链接行追加 `-lc++`（uchardet 静态 C++ 档案拖入 C++ 运行时符号）
   - uchardet 头文件子目录 `include/uchardet` 加入 include 路径
4. package() 调用 `_verify_shared_lib_integrity()`（见问题 #5，知识 DRAFT-15202）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | glib 依赖选型 | ohpcd 的 glib/2.88.3.x binary 钉 zlib/1.3.2，与 libarchive→zlib/1.3.1.1 冲突 | 选 glib/2.84.0.2（binary 精确匹配 zlib override 图）+ `transitive_headers/transitive_libs=True`（公共头暴露 glib 类型、.so DT_NEEDED glib 家族） |
| 2 | meson gnome 模块找不到 mkenums | PkgConfigDeps 生成的 glib-2.0.pc 缺下划线变量 `glib_mkenums`/`glib_genmarshal` | generate() 向生成的 .pc 注入两变量（glib 包 bindir 已含工具） |
| 3 | `uchardet.h` 找不到 | uchardet/0.0.7 配方 exposedirs=`["include"]`，头实际在 `include/uchardet/uchardet.h` | 配方内加 `-I<uchardet>/include/uchardet`（不改他人配方） |
| 4 | 链接 `__gxx_personality_v0` 等未定义 | uchardet 静态 C++ 档案链入 C 共享库拖 C++ 运行时符号；clang 15 C 无 `-static-libc++` | C 链接行追加 `-lc++` |
| 5 | dlopen EACCES（test_package 运行期） | meson install rpath fixup in-place 重写 .so，hmdfs 上 ELF 损坏（306B 差、.dynstr 区 0x58 填充） | package() sha256 校验（包 vs 构建树）+ `shutil.copy2` 重拷；DRAFT-15202 |
| 6 | MIME 探测全 octet-stream（消费者用例） | OHOS 无 /usr/share/mime（shared-mime-info）数据库 | 消费者用例内嵌最小 globs（46 行 totem 扩展集）+ `g_content_type_set_mime_dirs` 注入；DRAFT-15201 |
| 7 | 上游测试二进制启动即 abort（Signal 6） | 容器 uid 20020090 不在 /etc/passwd，main 的 check_http()→g_get_user_name()→getpwuid_r 失败 FATAL | 纯 C LD_PRELOAD getpwuid_r 拦截器；DRAFT-15203 |
| 8 | videosite 5 用例 rc=127 | shim3 同时注入 glib 符号，videosite 派生 /bin/sh 子进程继承 LD_PRELOAD 后 relocation 错误死亡 | shim4（仅 getpwuid_r，nm -D 验证无 glib 符号），5 用例全转绿 |
| 9 | 消费者用例断言 API 报错 | 该 glib 包头 `g_remove` 隐式声明；`g_assertion_message` 需 5 参 | 清理用 POSIX unlink/rmdir，断言失败用 `g_error` |

## 源码修改

- **未修改上游源码**（patches/ 为空），全部适配在 conanfile.py 配方内。
- 临时测试补丁（**不入 PR**）：R51 逐用例执行时，在**构建树**（本地 conan cache
  build 目录，非仓库源码）的 tests/parser.c、tests/podcast.c 的 g_test 注册处加
  `R51_FILTER` 环境变量门（每用例独立进程，防 g_assert abort 杀死整组）；执行完毕
  已用 .r51bak 还原原始文件。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.2 | `transitive_headers/transitive_libs=True` |
| libxml2 | 2.15.3.1 | |
| libarchive | 3.8.7 | |
| uchardet | 0.0.7 | 静态 C++ 档案 |
| libgcrypt | 1.12.2 | |
| zlib | 1.3.1.1 | `override=True`（消解 glib→1.3.2 / libarchive→1.3.1.1 冲突） |

## 验证结果

```text
conan create（r11，2026-10-15）: PASS
  consumer test OK: entries=2 first=.../first.mp4 second=.../second.mp4
  日志: /storage/Users/currentUser/tmp/builds/totem-pl/conan-create-r11.log
```

## 上游测试（R51 三步法，2026-10-16 实测）

### 1. 清点
- tests/meson.build：parser（parser.c+utils.c，44 用例）/
  podcast（podcast.c+utils.c，28 用例）/ disc（disc.c，2 用例）= 共 74 个。
- `404_error` 注册行在上游源码中被注释（parser.c:1124），非活跃用例。
- disc 的 main 有上游门控：仅 `g_get_user_name()=="hadess"`（作者机）时注册 2 个
  g_test 用例，其余用户直接 `return 0`（0 用例，rc=0）；位置参数模式
  `./disc <device>` 可直跑 test_disc。

### 2. 执行环境（OHOS 真机 aarch64）
- 逐用例进程隔离：`R51_FILTER` 门补丁（仅构建树）
- `XDG_DATA_HOME` 最小 MIME 库：globs（50 行）+ magic（v1 二进制：
  `MIME-Magic\0\n` 头 + `[100:application/xspf+xml]` + `>0=<2字节长度><值>+600`）
  + subclasses（`application/x-php text/plain`）
- `LD_PRELOAD`：纯 C getpwuid_r shim（无 glib 符号）
- HOME 指向可写目录

### 3. 结果

| 套件 | 总数 | 通过 | 失败 | 通过率 |
|------|------|------|------|--------|
| parser | 44 | 43 | 1 | 97.7% |
| podcast | 28 | 25 | 3 | 89.3% |
| disc | 2 | 0（上游门控，0 例执行） | 0 | — |
| **合计（执行口径 72）** | 72 | **68** | **4** | **94.4%** |

日志：`/storage/Users/currentUser/tmp/ohpc-t/final-run.txt`（74 行，逐用例
rc + TAP 行；单用例日志 finallog-*.log）。

### 4. 失败用例根因归类（均与适配无关）

| 用例 | 根因 |
|------|------|
| `/parser/resolution` | glib 2.84 `g_file_resolve_relative_path` 对 base 含 query 时把 query 与相对路径拼接（非替换）：实际 `...288629.asx?actionpage=3&id=288629&locale?s=1000`；上游测试与 glib 版本行为耦合 |
| `/parser/compressed_content_encoding` | 抓取 https://escapepod.org/feed/（2011 年代外部站点）：OHOS GFile 层无 http 后端（探针：g_file_read 对全部 http/https URL 返回 NULL） |
| `/parser/parsing/itms_link` | https://itunes.apple.com（现 301 跳转）：totem `is_itms_feed` 特判路径需抓取页面，无 http GFile 后端 |
| `/parser/xml_is_text_plain` | http://leoville.tv（301→twit.tv 站点腐化）+ `check_http()` 未初始化变量 bug（tests/utils.c:265）使测试未按注释意图自跳过 |

disc 2 例不计入通过率分母：上游 main 按作者用户名门控，任意他机实际执行 0 例
（rc=0）；位置参数模式实测 /dev/dvd 与不存在路径均 rc=0（仅 "No media in drive"
消息，无断言失败）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libtotem-plparser.so.18.3.6 | 391,744 B | 主共享库 |
| lib/libtotem-plparser-mini.so.18.3.6 | 43,520 B | mini 变体（精简源集 + -DTOTEM_PL_PARSER_MINI） |
| include/totem-pl-parser/1/plparser/*.h | 5 个 | 公共头（parser/playlist/mini/builtins/features） |
| lib/pkgconfig/{totem-plparser,totem-plparser-mini}.pc | 2 个 | pkg-config 下游兼容（pkg_config_name） |
| bin/totem-pl-parser | — | 上游安装的 CLI 工具（库包，PF8 判定非 CLI 包，无需 commands.json） |

## 注意事项

- 包名/slug = `totem-pl`；下游兼容靠 components 的 `pkg_config_name`
  （totem-plparser/mini）。
- 适配路径：**B（知识库扩展）+ 依赖项**（grilo 0.3.19 依赖 totem-plparser）。
- 知识草稿：`knowledge/drafts/DRAFT-15201/15202/15203`（kv+md 成对）。
- PR 白名单：`archives/t/totem-pl/**` + `knowledge/drafts/DRAFT-1520[123]-*.{kv,md}`。
- 消费者用例要点：`entry-parsed` 信号第 2 参 uri 即条目位置（非
  `metadata["location"]`）；OHOS 下需注入最小 globs 使 MIME 行为确定。
---

**编译结束**: 2026-10-16 16:04
**最终状态**: built

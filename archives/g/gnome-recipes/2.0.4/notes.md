# gnome-recipes 2.0.4 适配笔记

> 上游 GNOME Recipes（GTK3 菜谱管理应用），语言 C。
> 归档名/分支名 `gnome-recipes`，上游仓 gitlab.gnome.org/GNOME/gnome-recipes。

## 编译环境
- 构建系统: meson（+ 内置 libgd subproject，随 tarball 发布，无需下载）
- 编译日期: 2026-10-14
- 编译器: clang (OHOS aarch64)
- 状态: 真机收官——conan-verify 八门禁 G0–G4 全 PASS（L2/L4/L5 无 cache 路径按设备常态跳过），上游 5 个测试程序 / 9 个用例与消费者 test_package 11 校验点全过。

## 适配决策

### 1. 路线：librest (rest-0.7) → libsoup 2.4（patch 0001）
上游 `src/gr-shopping-list-exporter.c` 用 librest 发 Todoist 购物清单请求；
制品仓只有 librest/0.10.2——它是 rest-1.0 API 世代（pkg_config_name
rest-1.0、链接 libsoup3），提供不了 rest-0.7.pc；且 libsoup2 与 libsoup3
同进程符号冲突不被支持，消费它会把 soup3 拖进 gtk3/libsoup-2.4 进程。实际用法全部是「固定 URL 的 x-www-form-urlencoded POST」，
无 OAuth2 逻辑（oauth2-proxy.h 头文件虽在，实际调用全在 RestProxy 层），
因此直接以 libsoup 2.4 重建 5 处调用簇：

| 调用簇 | 方法 | 同步性 |
|---|---|---|
| remove_items | POST TODOIST_URL | async |
| get_project_data | POST .../projects/get_data | async |
| export_shopping_list_to_todoist | POST TODOIST_URL | async |
| add_project_id | POST TODOIST_URL | sync |
| get_project_id | POST TODOIST_URL | sync |

语义保持：`sync_token` 缺省字面量 `'*'`；`exporter->sync_token` 有意指向
未释放的 json 对象（后续请求复用，故保留 object 不 unref 的原设计）；
回调更名后仍为同名函数。辅助层 `get_soup_session / form_add_param /
form_post_message` 统一表单构造；async 用 `soup_session_queue_message`
（不自持 msg 引用），sync 用 `soup_session_send_message` + `msg->status_code`。
上游 meson.build 只需删 `dependency('rest-0.7')` 一行；编译器与头文件
本文件仅此一处 rest 引用，全树 grep 确认（flatpak json 不参与构建）。

### 2. glib/zlib 统一到 2.84.0.1.1 + 1.3.1.1（override 向下）
两代生态精确互斥：gtk/3.24.43 栈（gtk/atk/gdk-pixbuf/pango/gspell/
libsoup 等全部已发二进制）pin glib/2.84.0.x + zlib/1.3.1.1；libgoa/3.58.1
（上游 pin glib/2.88.3）、json-glib、gnome-autoar 属 2.88.3/1.3.2 世代，
而该世代制品仓尚无 GTK3 栈二进制。向上统一（2.88.3）会把 13 个已发
二进制全部作废、触发整栈源码构建；向下统一则保留全栈二进制，仅
libgoa 一个节点重编。Conan 2 允许根 override 覆盖依赖的硬 pin（实测
Overrides 表：glib/2.88.3 → glib/2.84.0.1.1，无冲突无告警），故
`requires("glib/2.84.0.1.1", override=True, options={"shared": True})`
+ `requires("zlib/1.3.1.1", override=True)`，trio 换成 2.84 世代对应版本：
json-glib/1.10.6.1、gnome-autoar/0.4.5（gnome-autoar-0.pc 不变）。
pkg-config 闭包对齐 activity-log 0.9.7 先例：pcre2/10.45、libffi/3.4.4、
graphite2/1.3.14、xz/5.6.2（harfbuzz/libtiff 的公开 Requires）。

### 3. 缺 .pc 别名合成（gio-unix-2.0 / gmodule-export-2.0）
glib 配方只导出 glib-2.0/gobject-2.0/gmodule-2.0/gthread-2.0/gio-2.0
组件；上游依赖的 gio-unix-2.0（gr-image-viewer.c 用
\<gio/gunixoutputstream.h\>、gr-mail.c 用 GUnixFDList）与
gmodule-export-2.0（仅链接期、源码无 g_module 调用）由配方 generate()
从最接近组件 .pc 合成别名（evince 同款机制扩展），上游 meson 保持原样。

### 4. 其余工具链缺件补丁
- 0002 appdata：msgfmt --xml 需要 itstool ITS 规则（OHOS 无）→ 直接
  install_data 安装未翻译 appdata（evince 0003 先例）。
- 0003 安装后脚本：gtk-update-icon-cache / update-desktop-database 在
  OHOS 不存在（原脚本 FileNotFoundError）→ 摘除这两个调用；
  glib-compile-schemas 改为 shutil.which 守卫（配方另有
  `_compile_schemas()` 用 staged 工具在 package 阶段直接编译，双保险）。
- 0004 help/：gnome.yelp 需要 itstool + yelp-tools → 移除 `subdir('help')`。
- 0006 安装后脚本调用：真机 meson install 直接拒执脚本本体（`FAILED:
  install script ... could not be run` → `Error 127`）——OHOS 禁脚本直
  执行，脚本作为 meson install script 的**执行方式**本身即不可用，与
  脚本内容无关；直接摘除
  `meson.add_install_script('meson_post_install.py')`。schema 编译由配方
  `_compile_schemas()` 承担（0003 的守卫因此成为防御性调整——脚本仍留在
  树内，但不再被调用）。

### 5. glib 组件命名跨世代归一（运行期改写 cpp_info.requires）
glib 两代适配配方连 cpp_info 组件命名都不一致：2.84.x 世代为带后缀名
（glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0/gthread-2.0），2.88.3 世代
改名成裸名（glib/gobject/gio/gmodule/gthread）。按 2.88 世代写的消费者
（libgoa/3.58.1：`cpp_info.requires = ["glib::glib", "glib::gio"]`）在
glib 向下统一后会让 PkgConfigDeps 直接中止（"Component 'glib::gio' not
found in 'glib' package requirement"；json-glib/1.10.6.1 与
gnome-autoar/0.4.5 的现行修订本身是带后缀引用，不受影响）。generate()
在 PkgConfigDeps 之前对依赖图的组件引用做双向 -2.0 归一——依赖对象在
generate() 中是活引用，改写对生成器可见（最小探针实验验证：libgoa 的
goa-1.0.pc 随即生成出正确的 `Requires: glib-2.0 gio-2.0`）。

### 6. locale 测量项能力探测（patch 0005）
上游 `gr-convert-units.c`（3 处）与 `gr-recipe-formatter.c`（1 处）用
`#ifdef LC_MEASUREMENT` 守卫 `nl_langinfo(_NL_MEASUREMENT_MEASUREMENT)`。
OHOS libc 定义 `LC_MEASUREMENT` 类别却不提供 glibc 专有的
`_NL_MEASUREMENT_MEASUREMENT` 列表项 → 守卫通过而符号不存在，直接编译失败
（use of undeclared identifier）。patch 0005 在 `meson.build` 增加
`cc.links` 编译探测（`HAVE__NL_MEASUREMENT_MEASUREMENT`；该标识是枚举成员
而非宏，无法直接 `#ifdef`），并以其守卫上述四处分支：glibc 上探测为真、
行为与上游一致（locale 单位正常生效）；缺该扩展的 libc（OHOS）上探测为假、
落入原有的 metric/celsius 默认分支，编译通过。无平台宏，纯能力探测。

### 7. glib python 工具 staging：runpy wrapper（修正 evince 世系隐性缺陷）
evince 48.4 世系的 `_stage_glib_tool` 对 python 脚本先裸拷贝再"尝试"写
sh-wrapper，但 `_wrap_python_tool` 里 `if os.path.isfile(wrapper): return`
的早退使 wrapper 永远不会被写出（拷贝路径==wrapper 路径）——evince 构建
从不调用 gdbus-codegen，该分支在平台内从未被走到。gnome-recipes 实际调
用它（data 与 shopping-list 的 D-Bus 代码生成），真机撞上：裸拷贝落在
`<build>/.glib-tools/`，而 gdbus-codegen 自带引导逻辑按 `__file__` 逐级
上溯找 `share/glib-2.0/codegen`——staged 副本的上级是 `<build>/`，于是
去找 `<build>/codegen` 报 `ModuleNotFoundError: No module named
'codegen'`。修正：python 工具一律写"解释器绝对路径 shebang + `runpy.
run_path(原包脚本)`"的 wrapper（原脚本 __file__ 保持在 glib 包 bin/，
`bin → ../share/glib-2.0` 引导分支自愈）。该形态与平台内 atk/2.38.0.1.1
的 `_create_python_tool_wrapper` 相同，且解释器绝对路径 shebang 在真机
可 exec（真机实测 /bin/sh、/usr/bin/env 作 shebang 反而不可）。

### 8. 依赖包 soname 名称物化（symlink(2) EPERM 补偿）
真机文件系统全盘拒绝 symlink(2)（`ln -s` → Permission denied）。meson
install 的共享库正常落盘为「一个实体 + 两个 soname 链接名
（libX.so.<major> / libX.so）」，链接器仅经无版本名解析 -lX；本图内
源码重编的节点（libgoa 因 glib 向下统一而重编）因此只落实体
`libgoa-1.0.so.0.0.0`，消费者随即 `ld.lld: error: unable to find
library -lgoa-1.0`（conanmanifest 证实 package() 当时即无这两个名字，
非事后被删）。制品仓下载包在同盘不显病：归档中的符号链接条目在解包落地
时被物化为同名实体拷贝，这正是该盘上依赖包的既有形态。配方 generate()
在构建前扫描全部 host 依赖包的 libdir，对命中
`^lib.+\.so\.\d+(\.\d+)*$` 的实体物化缺失的 `libX.so.<major>` /
`libX.so`（实体拷贝；幂等——名字齐全或有 symlink 的宿主上零动作）。真机
已实证「人工物化 → 原失败链接点（[97/125] tools/recipe-extract）通过」，
配方机制的真机复验见验证结果。

### 9. 运行期 libarchive：图内共享库须前置在 LD_LIBRARY_PATH（系统同名库是减配版）
binary 链接闭包经 gnome-autoar 登记 `libarchive.so.13`（autoar 静态、
其压缩过滤器调用随静态对象写进主程序），链接期由本图制品仓的
libarchive/3.8.7 满足；但真机 `gnome-recipes --help` 启动即死于
`Error relocating ...: archive_write_add_filter_gzip: symbol not found`
（约 15 个 gzip/bzip2/xz/lzip/grzip 等过滤器入口），退出码 127。逐层
定位：可见目录无 libarchive 制品（conan 缓存目录名是「名前缀+hash」，
`*archive*` 通配永远打不中，实际目录 `p/libara07f23a76465c`）；系统
libarchive.so.13 存在但为减配构建（基础归档 API 全在、过滤器入口全缺）。
本图 libarchive 包的 .so 经 `llvm-readelf` 核对过滤器符号齐全；消费侧
run 环境（conanrun）不含其 libdir，加载器于是落回系统同名库。实测
「LD_LIBRARY_PATH 前置本图 libarchive libdir → 同一个二进制 --help 正常
输出（rc=0）」，定位闭环。

机制补钉（多轮真机实测，conan 2.29.1）：传递依赖被 conan 的
`Skipped binaries` 判定排除出运行闭包——被 skip 时 `package_folder` 为
None，配方 `package_info()` 里 `if libarchive.package_folder:` 的守卫型
runenv 发布**静默失效**（实测：被测包自身 package_info 确实执行——无条件
PATH 前置落在 conanrunenv 的 export PATH 行、profile `os=OHOS`——但
libarchive 仍留 Skipped 列表、conanrunenv 无其目录、test 依旧 rc=127）。
仅"配方侧访问 package_folder"不足以把 Skip 转 Cache；唯一实测有效杠杆 =
图根侧消费者显式声明（test_package `requirements()` 直接
`self.requires("libarchive/3.8.7")`，与 gnome-autoar 的 pin 同版、去重
无冲突）：`Skip → Cache`、包即时安装、`package_folder` 可用，此时**两个
通道同时落实**——配方侧 runenv 发布（package_info() 把该包 libdir 以最高
优先级前置进 runenv_info 的 LD_LIBRARY_PATH，路径随消费端缓存解析、无
绝对路径烙进产物）+ test() 侧枚举注入（host 依赖逐包 lib/lib64，组件化
包 cpp_info 可能为空故不读 cpp_info，经脚本第 3 参数前置进
LD_LIBRARY_PATH）。真机结果：`libarchive/3.8.7 - Cache`、`Already
installed! (17 of 34)`、conanrunenv 出现其 libdir、冒烟测试
`gnome-recipes package smoke test: OK`（rc=0）。现象谱系与修法排序见知识
库 E669（lnav 0.13.2）及草稿 DRAFT-2670-…-run-closure-skip-unskip-lever
（本任务增量实证）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游依赖 rest-0.7 | 制品仓 librest/0.10.2 属 rest-1.0/libsoup3 世代，不提供 rest-0.7.pc；soup2+soup3 不可同进程 | patch 0001：以 libsoup 2.4 重建 5 处调用簇，删 meson 一行 |
| 2 | glib 2.84.0.x 与 2.88.3 精确 pin 互斥 | gtk 栈与 goa/json-glib/autoar 分属两代；2.88.3 世代尚无 GTK3 栈二进制 | override 向下统一 2.84.0.1.1 + zlib/1.3.1.1；libgoa 单节点重编 |
| 3 | gio-unix-2.0.pc / gmodule-export-2.0.pc 不存在 | glib 配方无这两个组件 | generate() 合成别名（只补缺不覆盖） |
| 4 | msgfmt --xml 报缺 ITS 规则 | OHOS 无 itstool ITS | patch 0002 安装未翻译 appdata |
| 5 | meson_post_install.py 调系统工具 | gtk-update-icon-cache / update-desktop-database 不存在 | patch 0003 + 配方 _compile_schemas() 兜底 |
| 6 | help/ 构建需要 itstool | OHOS 无 itstool/yelp-tools | patch 0004 移除 subdir('help') |
| 7 | PkgConfigDeps: Component 'glib::gio' not found | libgoa/3.58.1 按 glib/2.88.3 世代裸组件名（glib/gio）引用；2.84 世代组件名为 glib-2.0/gio-2.0 | generate() 在 PkgConfigDeps 前运行期双向归一依赖 cpp_info.requires |
| 8 | gdbus-codegen 报 ModuleNotFoundError: codegen | staging 裸拷贝使脚本按 __file__ 上溯找 codegen 模块时落在 <build>/codegen；evince 世系的 sh-wrapper 因早退缺陷从未写出 | python 工具改写"解释器绝对路径 shebang + runpy 原包脚本"wrapper（atk 2.38.0.1.1 同构） |
| 9 | use of undeclared identifier '_NL_MEASUREMENT_MEASUREMENT' | 上游以 `#ifdef LC_MEASUREMENT` 守卫 glibc 专有列表项；OHOS libc 有类别无该项；该标识是枚举成员非宏，不能直接 `#ifdef` | patch 0005：meson `cc.links` 编译探测（`HAVE__NL_MEASUREMENT_MEASUREMENT`）守卫四处分支（glibc 上探测为真、行为与上游一致；能力探测，无平台宏） |
| 10 | `FAILED: install script ... could not be run`（Error 127） | OHOS 禁脚本直执行；meson install script 的执行方式本身不可用 | patch 0006：摘除 `meson.add_install_script()` 调用；schema 编译由配方 `_compile_schemas()` 完成 |
| 11 | `ld.lld: error: unable to find library -lgoa-1.0` | 真机 fs 禁 symlink(2) → 源码重编的 libgoa 只有实体 `libgoa-1.0.so.0.0.0`，缺 `libgoa-1.0.so` / `.so.0` 名 | generate() `_materialize_dep_sonames()`：对 host 依赖 libdir 以实体拷贝物化缺失 soname 名（幂等） |
| 12 | 启动即 `archive_write_add_filter_gzip: symbol not found`（rc=127） | 图内链接的 libarchive 不在消费侧 run 环境（传递依赖被 Skipped，package_folder=None → 守卫型 runenv 发布静默失效）；系统同名库是缺过滤器入口的减配构建 | test_package 显式 `requires("libarchive/3.8.7")`（un-skip 杠杆）→ 配方 package_info() 前置其 libdir 进 runenv 的 LD_LIBRARY_PATH + test() 枚举 host 依赖 libdir 经脚本参数注入（双通道） |

## 本地预检
- patch_ng（conan 同款解析器）strip=0 链式应用 0001–0006：全过；
- 0001–0005 应用结果与编写树逐字节一致（meson.build / exporter.c /
  data/meson.build / meson_post_install.py）；0006 由链尾（0005 后）状态
  直接生成并做往返验证（应用后 meson.build 与目标内容逐字节一致）；
- 未移植函数段与上游逐字节一致（仅 8 个函数为移植面）。

## 源码修改（6 个补丁，涉及 6 个文件）
- patches/0001-shopping-list-export-via-libsoup.patch（meson.build 1 行 +
  exporter.c 移植：替换 rest API 为 libsoup，其余函数逐字节保持）
- patches/0002-appdata-no-its-merge.patch（data/meson.build）
- patches/0003-post-install-no-system-tools.patch（meson_post_install.py）
- patches/0004-disable-help-build.patch（meson.build 移除 help 子目录）
- patches/0005-locale-measurement-capability-guard.patch（gr-convert-units.c
  ×3 + gr-recipe-formatter.c ×1：守卫改探测 _NL_MEASUREMENT_MEASUREMENT）
- patches/0006-disable-post-install-script.patch（meson.build 移除
  `meson.add_install_script('meson_post_install.py')`）

## 验证结果
- 真机 conan-verify（conan 2.29.1，profile ohos-aarch64）：G0/G1/G2/G3/G4 全 PASS，
  L2/L4/L5 无 cache 路径按设备常态跳过；Verdict PASS（报告随档 reports/）。
- conan create（G2）：meson+ninja 全量构建 [125/125] 链接 src/gnome-recipes；
  34 包依赖全部 Cache/已装（含 libarchive/3.8.7——显式声明后进入运行闭包）；
  test_package："gnome-recipes package smoke test: OK"（11 校验点 + runnable --help 冒烟）。
- 上游测试（meson test --print-errorlogs）：Ok 5 / Fail 0，MESON_TEST_RC=0；
  含 g_test 用例 9 个（strv 2 + ids/unit/number 各 1 + ingredients 数据驱动 4）。
- 编译器：clang 15.0.4（aarch64-unknown-linux-ohos，/data/service/hnp/bin/clang）。
- 报告：reports/conan-create.log + reports/conan-verify-report.md。

## 交付物
| 文件 | 说明 |
|------|------|
| archives/g/gnome-recipes/2.0.4/conanfile.py | Conan v2 配方（evince 版 GLib 工具链机制） |
| archives/g/gnome-recipes/2.0.4/conandata.yml | 源码 url + sha256 + 补丁登记 |
| archives/g/gnome-recipes/2.0.4/patches/*.patch | 六个适配补丁 |
| archives/g/gnome-recipes/2.0.4/test_package/ | 消费者测试（shell 冒烟 + MANIFEST.yml） |
| archives/g/gnome-recipes/2.0.4/manifest.yaml | 版本级 manifest |
| archives/g/gnome-recipes/{commands.json,manifest.yaml,README.md} | 软件级平台文件 |

## 注意事项
- libgoa 的 Todoist token 获取依赖 org.gnome.ControlCenter D-Bus 服务，
  无该服务的环境仅"添加账户"路径不可用；导出主路径（已存账户）不受影响。
- 上游 2.0.4 tarball 自带 subprojects/libgd（非 wrap 下载），
  wrap_mode=nodownload 足够。

# GnuPG 不可重定位安装、套接字临时目录与 Qt 临时文件让 Libkleo 测试误失败

> 本草稿配对 libkleo/26.04.3。id 保持 DRAFT-13785-libkleo-26.04.3-ctest-agent-boundary。

## 与正式条目的边界

按 origin/main tip `1262b4ac24a3244f254c3e8163fa35d04b48f7fb` 重测，`knowledge/graph/E###.kv` 共 542 条。

| 检索词 | 正式图谱命中 |
|---|---|
| `gpgconf.ctl` | 0 |
| `QTemporaryFile` | 0 |
| `O_TMPFILE` | 0 |
| `QT_QPA_PLATFORM_PLUGIN_PATH` | 0 |
| `gpg-agent` | 0 |
| `AF_UNIX` | E024、E461 |

SONAME 与相对路径 `DT_NEEDED` 不另立新机制。E207、E274、E330、E383、E537 已经覆盖「CMake 在 OHOS 上留下空 SONAME、链接器把相对路径写进 DT_NEEDED、需要补 SONAME 与 `.so.N` 别名」。本配方只按这些条目处理 `libKPim6Libkleo.so.6`。

E024 建议把 `AF_UNIX` 改成 TCP。E461 记录 HMDFS 与 `/tmp` 拒绝文件套接字，并建议抽象命名空间。GnuPG 的 `gpg-agent` 使用文件系统套接字，配方不改它的协议。本机探测的增量是：`/storage` 上 `bind` 返回 `EPERM`，应用私有目录 `/data/storage/el2/base` 可以绑定。测试只把 `TMPDIR` 放到探测成功的目录。

E002 是把 `TMPDIR` 指到可写目录。E272 拦截的是 libc `tmpfile()` 忽略 `TMPDIR`。本题的临时文件失败是另一面：缓存盘允许 `O_TMPFILE`，但 `linkat` 赋名失败，`QTemporaryFile::fileName()` 为空，`Kleo::classify()` 返回 0。

## 触发场景

libkleo 26.04.3 的 `autotests/` 注册 16 个 CTest。设备上曾出现三类假失败：

- `keyresolvercoretest`、`expirycheckertest`：GnuPG 组件仍指向 `/bin/gpg-agent`，且默认临时目录不能绑定 `AF_UNIX`。
- `classifytest`：临时文件没有名字，分类结果为 0。
- 四个对话框测试：`QT_QPA_PLATFORM_PLUGIN_PATH` 被每个依赖的空 `plugins/platforms` 盖住，`offscreen` 插件找不到，进程 `SIGABRT`。

`tests/` 另有 8 个 `ecm_mark_as_test` 程序未注册到 CTest。其中加载失败来自相对路径 `DT_NEEDED`（`../bin/libKPim6Libkleo.so`），按 E383 写 SONAME 后消失。这 8 个程序不是 CTest 的 16 项。

## 原因与配方修法

1. `gnupg/2.5.22` 的 prefix 是 `/`，装进 Conan 缓存后 `gpgconf` 仍找 `/bin/gpg-agent`。`/bin` 不可写。`gpg-agent` 在包的 `bin`，`keyboxd` 和 `scdaemon` 在 `libexec`。每个组件用 `/proc/self/exe` 的真实路径去掉文件名再去掉一层目录，然后读 `<根>/bin/gpgconf.ctl`。符号链接会解析回包内文件，所以配方把 `bin` 和 `libexec` 复制到本次构建目录 `gnupg-prefix`，只在私有 `bin` 写 `gpgconf.ctl`，`rootdir` 指向这个私有前缀。不改 gnupg 包，也不写 `~/.cache/conan2`。`.enable` 为真会让整份文件被忽略，所以不要写它。
2. `/storage` 上 `AF_UNIX` `bind` 返回 `EPERM`。`/data/storage/el2/base` 可以绑定套接字，也支持 `O_TMPFILE`。上游测试把 `GNUPGHOME` 放在 `QDir::tempPath()`。OHOS 上把 `TMPDIR`、`TEMP`、`TMP` 设到这个可绑定目录。
3. 同一目录上 `O_TMPFILE` 打开成功，但 `linkat` 赋名失败，Qt 拿到空文件名。测试进程 `LD_PRELOAD=ohos_notmpfile.so`，只在 `(flags & O_TMPFILE) == O_TMPFILE` 时返回 `EOPNOTSUPP`。OHOS 的 `open64`/`openat64` 是宏，不能再定义这两个函数。该库不进入安装包。
4. Qt 把 `QT_QPA_PLATFORM_PLUGIN_PATH` 当作平台插件搜索列表，不是附加路径。只把它设成 qtbase 的 `plugins/platforms`。`QT_PLUGIN_PATH` 仅在目录真实存在时前置。`QT_QPA_PLATFORM=offscreen`。
5. GpgME 默认引擎是 gnupg 包里的绝对路径，不看 `PATH`。`conanbuild.sh` 还会把包内 `bin` 插到 `PATH` 前面。配方把私有 `bin` 写进 `LIBKLEO_GNUPG_BIN`。补丁只在这个变量非空时调用 `gpgme_set_engine_info`，不搜索 `PATH`，因此未设置该变量的进程保持 GpgME 原引擎。`home_dir` 保持空，测试稍后设置的 `GNUPGHOME` 仍然有效。`test_cryptoconfig` 在构造 `QCoreApplication` 之前就读版本，`test_keyformailbox` 不创建 `QApplication`，所以不能把这件事推迟到 `Q_COREAPP_STARTUP_FUNCTION`。
6. 消费者依赖库的 `DT_NEEDED` 带有 `../../bin/`。链接农场建在 `test_package` 的 cmake 构建目录里。那是构建产物，不是配方源码，也不进入安装包。

gettext 不是失败原因。同一隔离缓存里唯一要求来自 `ki18n/6.26.0` 的 `gettext/0.22.5#acfaf59091ac169d8112c896de1c84ee`，没有第二个版本，也没有 Version ranges conflict。旧日志里的硬错误是 kconfig 缓存的 `conan_export.tgz already exists`。不要写 gettext override。

## 验证依据

设备 `CONAN_HOME=/data/storage/el2/base/cache/ch-lbk14632`。2026-10-04 同一次 `conan create` 的 `CREATE_EXIT=0`。验证时导出 `libkleo/26.04.3#54c7b75cb89277ba929dc9e708d3d674`，包 `bb1ea1271123679e5ae97eafd9152b3eddf3af6f#453efead063edfd4b1ae0afea6f9e03e`。补丁只在 `LIBKLEO_GNUPG_BIN` 非空时改引擎。

- CTest 日志原文：`100% tests passed out of 16`，`Total Test time (real) = 24.98 sec`。`keyresolvercoretest`、`expirycheckertest`、`classifytest` 均为 Passed。
- `test_cryptoconfig` 与 `test_keyformailbox` 退出码 0。
- `test_keyselectiondialog`、`test_keygen`、`test_keylister`、`test_auditlog`、`test_keyselectioncombo`、`test_keyresolver` 已加载 `libKPim6Libkleo.so.6`，停在上游 `QDialog::exec` 或 `QApplication::exec`。没有 `Error loading shared library`，没有自动断言。这 6 个交互样例不计为通过，也不计为失败。
- test_package 输出原文：`PASS: libkleo DN consumer API`。`conan create` 退出码 0。包含路径是 `#include <Libkleo/Dn>`，安装头是 `Libkleo/Dn`，不是 `Libkleo/DN`。

## 适用边界

只适用于 libkleo 26.04.3 在 HarmonyOS PC 上的这次运行时组合。后续版本要重新核对 GnuPG prefix、套接字目录和 Qt 临时文件行为。

禁止用 `ctest --exclude-regex` 排除 `keyresolvercoretest` 或 `expirycheckertest` 再写成通过。禁止把 6 个停在事件循环的程序写成通过。禁止在设备上手工拷贝运行库冒充配方修复。

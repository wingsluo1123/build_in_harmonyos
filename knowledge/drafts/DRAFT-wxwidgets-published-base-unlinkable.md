# 制品仓 wxWidgets 3.2.10 的 base 库链不上，wx-config 指向别人的缓存

VeraCrypt 1.26.24 的控制台构建（`NOGUI=1`）只需要 wx base。制品仓 `wxwidgets/3.2.10` 的 OHOS 二进制（包 id `c868bb4eb4b071d47d1da7da95758ac826396cc0`）不能直接拿来链接。

## 现象

1. `bin/wx-config` 是指向构建机 `~/.cache/conan2/p/b/wxwid...` 的符号链接。在另一台机器或另一个 `CONAN_HOME` 里，make 报 `wx-config: No such file or directory`，接着 `wx/wx.h` 找不到。
2. 就算改用包内 `lib/wx/config/base-unicode-static-3.2`，脚本里的头文件和库路径仍是那台构建机的绝对路径，`--libs` 还带有 `-lZLIB::ZLIB`。
3. 直接链接 `libwx_baseu-3.2.a` 时，lld 报 `wxMutex::Lock`、`wxThread::GetCurrentId`、`wxAppConsole`、`wxStackWalker` 未定义。这些目标文件没有打进归档。
4. 按 `wxUSE_GUI=OFF`、`wxUSE_THREADS=ON`、关闭 socket/net 在本机重编 base 之后，只剩 `libiconv`、`libiconv_open`、`libiconv_close`。musl 没有 `pthread_cancel` / `pthread_setcancelstate`，需要在最终链接里补一个空实现。

## 做法

消费者自己编一份 wx base，用一个小的 `wx-config` 包装脚本把 include 和 `.a` 指到这份前缀，并链上制品仓里的 `zlib`、`expat`、`libiconv`。不要把 `WX_CONFIG` 指到制品仓包的 `bin/wx-config`。

## 反证

在知识库 `knowledge/graph` 与 `knowledge/doc` 里按 `wx-config`、`wxMutex`、`wxStackWalker` 检索，没有已入库条目描述这条「制品仓 base 归档缺线程对象 + wx-config 外机绝对路径」的因果链。wx 配方笔记写过线程源文件要打开，但已发布的二进制仍然缺这些符号。

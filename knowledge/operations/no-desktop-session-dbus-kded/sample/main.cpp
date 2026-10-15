/*
   样例：无桌面会话双分支结构的最小载体（kwrited 6.7.2 的去业务化复刻）

   编译形态由 CMake 的 BUILD_AS_EXECUTABLE 决定（见 CMakeLists.txt），而该选项又由
   KF6Pty 包导出的 KPty_HAVE_UTEMPTER 联动 —— 与 kwrited 上游完全同构。

   可执行分支下本文件会真开一次 pty（KF6::Pty 在 OHOS 上可用：openpty/forkpty 由 libc
   提供），以此证明「形态切换后的产物确实能链接并调用依赖」。
*/
// KF6Pty 导出的 include 目录是 <prefix>/include/KF6/KPty，因此包含名不带 KPty/ 前缀
// （上游 kwrited 同样直接 #include <KPtyDevice> / <kpty.h>）。
#include <kpty.h>

#include <QCoreApplication>
#include <QDebug>
#include <QString>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

#ifdef SAMPLE_PLUGIN_BRANCH
    qInfo() << "branch=session-plugin (KDED) — 该形态在 OHOS 上无装载路径";
    return 0;
#else
    KPty pty;
    const bool opened = pty.open();
    qInfo().noquote() << QStringLiteral("branch=executable pty_open=%1 tty=%2")
                             .arg(opened ? QStringLiteral("true") : QStringLiteral("false"),
                                  pty.ttyName());
    return 0;
#endif
}

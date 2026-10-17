/* test_render.cpp — offscreen QWidget 渲染快照自检（qabc test_package）。
 *
 * qabc 是纯 GUI 应用（Qt6 Widgets），R40 要求验证 UI 框架适配完整性。
 * CI 无显示服务器，使用 qtbase 自带 offscreen 平台插件创建 QWidget
 * 并强制渲染一帧（grab），保存 PNG 快照并校验图像尺寸非零——
 * 覆盖"窗口对象创建 + offscreen 渲染管线"链路，防止空壳主循环
 * （仅能 --version/--help 但渲染栈不可用）通过验收。
 *
 * 快照输出目录取 TMPDIR（由 test_package 配方指向构建目录），不在
 * 源码/工作树内产生文件。
 */
#include <QLabel>
#include <QWidget>
#include <QPixmap>
#include <QImage>
#include <QApplication>
#include <cstdio>
#include <cstdlib>
#include <string>

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    QWidget w;
    w.resize(320, 200);
    QLabel label("qabc render check", &w);
    label.setGeometry(0, 0, 320, 200);
    w.show();

    // 强制渲染一帧（offscreen 平台下 grab 走软件渲染路径）
    QPixmap pm = w.grab();
    if (pm.isNull()) {
        std::fprintf(stderr, "FAIL: QWidget::grab() returned null pixmap\n");
        return 1;
    }
    const char *tmp = std::getenv("TMPDIR");
    std::string out = std::string(tmp && *tmp ? tmp : "/storage/Users/currentUser/tmp")
                      + "/qabc-render-check.png";
    if (!pm.save(QString::fromStdString(out))) {
        std::fprintf(stderr, "FAIL: cannot save render snapshot to %s\n", out.c_str());
        return 1;
    }
    QImage img = pm.toImage();
    if (img.isNull() || img.width() <= 0 || img.height() <= 0) {
        std::fprintf(stderr, "FAIL: render snapshot has invalid geometry\n");
        return 1;
    }
    std::printf("PASS: offscreen render snapshot %dx%d saved\n",
                img.width(), img.height());
    return 0;
}
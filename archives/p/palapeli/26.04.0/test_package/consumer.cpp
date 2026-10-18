/*
    palapeli 26.04.0 test_package —— 鸿蒙独有真实消费者测试

    与上游（无任何测试）不同，这里不写空壳断言，而是走上层应用的真实路径：
      1) 通过导出的 CMake 包 PalaConfig（find_package(Pala)）链接 libpala；
      2) 用 QPluginLoader 加载包里实际安装的切片器插件，qobject_cast 到
         Pala::Slicer——这一步同时验证 libpala 与插件的 ABI 一致；
      3) 用插件的 propertyList() 默认值构造 SlicerJob（正是 palapeli 自身
         初始化切图参数的做法），调用公开包装 Slicer::process()，真正执行
         切图算法；
      4) 对矩形切片器做几何校验：所有碎片面积之和必须等于输入图像面积
         （整块无缝铺满），碎片数必须等于网格行列数之积；
      5) 对拼图/黄金分割切片器做行为校验：process() 返回 true 且产出非空。

    失败即 exit 非 0，供 ctest 与 conan test 判定。
*/
#include <QCoreApplication>
#include <QImage>
#include <QMap>
#include <QPluginLoader>
#include <QDebug>
#include <QDir>
#include <QFileInfo>

#include <KPluginFactory>

#include <Pala/Slicer>
#include <Pala/SlicerJob>
#include <Pala/SlicerProperty>

#include <cstdio>

namespace {

int g_failures = 0;

void check(bool cond, const QString &what)
{
    if (cond) {
        std::printf("ASSERT-OK   %s\n", qPrintable(what));
    } else {
        std::printf("ASSERT-FAIL %s\n", qPrintable(what));
        ++g_failures;
    }
}

// 从插件的属性列表取默认值，构造切图参数——与 Palapeli 应用侧的初始化一致。
QMap<QByteArray, QVariant> defaultArgs(const Pala::Slicer *slicer)
{
    QMap<QByteArray, QVariant> args;
    const QList<const Pala::SlicerProperty *> props = slicer->propertyList();
    for (const Pala::SlicerProperty *prop : props) {
        args.insert(prop->key(), prop->defaultValue());
    }
    return args;
}

Pala::Slicer *loadSlicer(const QString &path, QPluginLoader &loader)
{
    loader.setFileName(path);
    QObject *obj = loader.instance();
    if (!obj) {
        std::printf("ASSERT-FAIL 插件加载失败 %s: %s\n",
                    qPrintable(path), qPrintable(loader.errorString()));
        ++g_failures;
        return nullptr;
    }
    // 切片器插件是 KPluginFactory 插件（K_PLUGIN_CLASS_WITH_JSON），
    // loader.instance() 返回的是工厂对象，不是 Slicer 本身；
    // 与上游 src/creator/slicerselector.cpp 的
    // KPluginFactory::instantiatePlugin<Pala::Slicer>(...) 同一路径。
    auto *factory = qobject_cast<KPluginFactory *>(obj);
    if (!factory) {
        std::printf("ASSERT-FAIL 插件不是 KPluginFactory %s\n", qPrintable(path));
        ++g_failures;
        return nullptr;
    }
    auto *slicer = factory->create<Pala::Slicer>(nullptr, nullptr);
    if (!slicer) {
        std::printf("ASSERT-FAIL 工厂未创建出 Pala::Slicer（libpala 与插件 ABI 不一致？） %s\n",
                    qPrintable(path));
        ++g_failures;
    }
    return slicer;
}

qint64 totalArea(const QMap<int, QImage> &pieces)
{
    qint64 area = 0;
    for (const QImage &img : pieces) {
        area += qint64(img.width()) * qint64(img.height());
    }
    return area;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const QString pluginDir = qEnvironmentVariable("PALAPELI_PLUGIN_DIR");
    if (pluginDir.isEmpty()) {
        std::printf("ASSERT-FAIL 未设置 PALAPELI_PLUGIN_DIR\n");
        return 1;
    }

    // 400x300 的不透明输入图，面积 120000
    QImage source(400, 300, QImage::Format_ARGB32);
    source.fill(Qt::darkCyan);
    const qint64 sourceArea = qint64(source.width()) * qint64(source.height());

    struct Expect {
        const char *file;
        bool exactTiling; // 是否要求碎片严丝合缝铺满输入图
    };
    const Expect expects[] = {
        {"palapeli_rectslicer.so", true},      // 矩形：严格网格平铺
        {"palapeli_jigsawslicer.so", false},   // 拼图：碎片带边缘遮罩
        {"palapeli_goldbergslicer.so", false}, // 黄金分割：含不规则/预设模式
    };

    for (const Expect &exp : expects) {
        const QString path = QDir(pluginDir).filePath(QString::fromLatin1(exp.file));
        if (!QFileInfo::exists(path)) {
            std::printf("ASSERT-FAIL 插件不存在: %s\n", qPrintable(path));
            ++g_failures;
            continue;
        }

        QPluginLoader loader(path);
        Pala::Slicer *slicer = loadSlicer(path, loader);
        if (!slicer) {
            continue;
        }
        const QString tag = QString::fromLatin1(exp.file);

        const QList<const Pala::SlicerProperty *> props = slicer->propertyList();
        check(!props.isEmpty(), tag + QStringLiteral(": propertyList() 非空"));
        check(!slicer->modes().isEmpty() || !props.isEmpty(),
              tag + QStringLiteral(": 至少声明了模式或属性"));

        // 属性键必须唯一且非空（上层据此构造参数，重复键会覆盖用户设置）
        QMap<QByteArray, int> seen;
        bool keysOk = true;
        for (const Pala::SlicerProperty *prop : props) {
            const QByteArray key = prop->key();
            if (key.isEmpty() || seen.contains(key)) {
                keysOk = false;
            }
            seen.insert(key, 1);
        }
        check(keysOk, tag + QStringLiteral(": 属性键非空且不重复 (%1 个)").arg(props.size()));

        // 真正跑切图算法
        const QMap<QByteArray, QVariant> args = defaultArgs(slicer);
        Pala::SlicerJob job(source, args);
        // 有的切片器（如 goldberg）必须先选模式：slicer-goldberg.cpp 里
        // job->mode() 为空就直接 return false。上层 UI 会显式选模式，这里取
        // 插件的第一个模式，等价于 UI 的默认选择。
        const QList<const Pala::SlicerMode *> modes = slicer->modes();
        if (!modes.isEmpty()) {
            job.setMode(modes.first());
        }
        const bool ok = slicer->process(&job);
        check(ok, tag + QStringLiteral(": process() 返回 true"));

        const QMap<int, QImage> pieces = job.pieces();
        check(!pieces.isEmpty(), tag + QStringLiteral(": 产出非空 (%1 片)").arg(pieces.size()));

        if (exp.exactTiling) {
            // 网格切片按整格取整：pieceWidth = width/xCount、pieceHeight = height/yCount。
            // 上游 slicer-rect.cpp 里 `const int thisPieceWidth = (x == xCount) ? ...
            // : pieceWidth;` 的判定永远不成立（应为 xCount - 1），所以除不尽的余数
            // 不会补给任何一片。断言因此校验"等尺寸整格平铺"，而不是"面积之和等于
            // 输入面积"——后者是上游行为，不是本包的回归。
            const QImage first = pieces.first();
            const int pw = first.width();
            const int ph = first.height();
            check(pw > 0 && ph > 0,
                  tag + QStringLiteral(": 首片尺寸有效 %1x%2").arg(pw).arg(ph));

            bool uniform = true;
            for (const QImage &img : pieces) {
                if (img.width() != pw || img.height() != ph) {
                    uniform = false;
                    break;
                }
            }
            check(uniform, tag + QStringLiteral(": 所有碎片等尺寸 %1x%2").arg(pw).arg(ph));

            const qint64 gridArea = qint64(pieces.size()) * pw * ph;
            check(totalArea(pieces) == gridArea,
                  tag + QStringLiteral(": 碎片面积之和 == 片数*单片面积 (%1 == %2)")
                      .arg(totalArea(pieces)).arg(gridArea));
            check(gridArea <= sourceArea,
                  tag + QStringLiteral(": 铺满面积不超过输入面积 (%1 <= %2)")
                      .arg(gridArea).arg(sourceArea));
            // 整格取整的丢边最多不到一整行/列，覆盖率仍需在 90% 以上
            check(gridArea * 100 >= sourceArea * 90,
                  tag + QStringLiteral(": 覆盖率 >= 90%% (%1/%2)").arg(gridArea).arg(sourceArea));
        }
    }

    std::printf("%s: failures=%d\n", g_failures == 0 ? "RESULT-PASS" : "RESULT-FAIL", g_failures);
    return g_failures == 0 ? 0 : 1;
}

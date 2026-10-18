// Consumer end-to-end test for the analitza/26.04.0 HarmonyOS PC package.
//
// Exercises the public API of the four shipped libraries the way kalgebra
// consumes them (R34: real API usage, no stubs):
//   - libAnalitza       : Expression parser + Analyzer evaluation
//   - libAnalitzaPlot   : PlotsFactory -> PlaneCurve (2D) / Surface (3D),
//                         PlotsModel and the Plotter3DES export path
//   - libAnalitzaGui    : VariablesModel over a real Analitza::Variables map
//   - libAnalitzaWidgets: PlotsView2D and ExpressionEdit construct and run
//                         against the packaged widgets library
// The 3D case is a full end-to-end pipeline: expression -> plot item ->
// marching-cubes geometry -> X3D document written through the packaged
// Export3D implementation (the same path the upstream export3dplotdemo
// CTest cases drive).
#include <analitza/analyzer.h>
#include <analitza/expression.h>
#include <analitza/value.h>
#include <analitza_version.h>

#include <analitzaplot/functiongraph.h>
#include <analitzaplot/planecurve.h>
#include <analitzaplot/plotsfactory.h>
#include <analitzaplot/plotsmodel.h>
#include <analitzaplot/plotter3d_es.h>
#include <analitzaplot/surface.h>

#include <analitzagui/variablesmodel.h>
#include <analitzagui/expressionedit.h>
#include <analitzagui/plotsview2d.h>

#include <QApplication>
#include <QColor>
#include <QDir>
#include <QFile>
#include <QImage>
#include <QModelIndex>
#include <QPointF>
#include <QRectF>
#include <QSharedPointer>
#include <QString>
#include <QStringList>
#include <QVector>
#include <QVector3D>

#include <cmath>
#include <cstdio>

using namespace Analitza;

static int g_passed = 0;
static int g_failed = 0;

static void report(const char *name, bool ok, const QByteArray &debug = QByteArray())
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s\n", name);
        if (!debug.isEmpty()) {
            std::printf("--- debug artifact ---\n%s\n--- end debug artifact ---\n",
                        debug.constData());
        }
    }
}

// The GL scene is unavailable in this Qt build (the OHOS qtbase line ships
// without Qt6OpenGL), so the renderer entry points stay empty and only the
// model/export half of Plotter3DES is driven - exactly like the upstream
// export3dplotdemo example.
class ExportPlotter3D : public Plotter3DES
{
public:
    explicit ExportPlotter3D(PlotsModel *model) : Plotter3DES(model) {}

    int currentPlot() const override { return -1; }
    void renderGL() override {}
    void modelChanged() override {}
    QImage grabImage() override { return QImage(); }
};

int main(int argc, char **argv)
{
    // AnalitzaWidgets hosts QWidget views, so the consumer runs a full
    // QApplication (QT_QPA_PLATFORM=offscreen on the device).
    QApplication app(argc, argv);

    // 1) Version binding: the packaged header reports the upstream
    //    ANALITZA_VERSION (9.0.0); the package version is the release
    //    number 26.04.0.
    report("version header reports 9.0.0",
           QString::fromLatin1(ANALITZA_VERSION_STRING) == QStringLiteral("9.0.0"),
           QByteArray(ANALITZA_VERSION_STRING));

    // 2) Expression parser + Analyzer evaluation (libAnalitza).
    {
        Expression expression(QStringLiteral("2+3*4"));
        Analyzer analyzer;
        analyzer.setExpression(expression);
        const double value = analyzer.evaluate().toReal().value();
        report("Analyzer evaluates 2+3*4 to 14",
               expression.isCorrect() && analyzer.isCorrect()
                   && std::fabs(value - 14.0) < 1e-9);
    }

    // 3) A second evaluation path with a power operator.
    {
        Expression expression(QStringLiteral("2^10"));
        Analyzer analyzer;
        analyzer.setExpression(expression);
        const double value = analyzer.evaluate().toReal().value();
        report("Analyzer evaluates 2^10 to 1024",
               analyzer.isCorrect() && std::fabs(value - 1024.0) < 1e-9);
    }

    // 4) 2D plot pipeline: PlotsFactory -> PlaneCurve geometry.
    {
        const Expression expression(QStringLiteral("x^2"));
        PlotBuilder builder =
            PlotsFactory::self()->requestPlot(expression, Analitza::Dim2D);
        FunctionGraph *item =
            builder.canDraw() ? builder.create(QColor(Qt::green), QStringLiteral("x^2"))
                              : nullptr;
        PlaneCurve *curve = dynamic_cast<PlaneCurve *>(item);
        QVector<QPointF> points;
        if (curve) {
            curve->update(QRectF(-2.0, -2.0, 4.0, 4.0));
            points = curve->points();
        }
        report("2D plot factory produces a PlaneCurve with sampled points",
               builder.canDraw() && curve && points.size() > 10);
        delete item;
    }

    // 5) 3D plot pipeline: Surface geometry computed by the marching-cubes
    //    backend through PlotsModel, then exported to X3D.
    {
        PlotsModel model;
        const Expression expression(QStringLiteral("sin x*sin y"));
        PlotBuilder builder =
            PlotsFactory::self()->requestPlot(expression, Analitza::Dim3D);
        FunctionGraph *item =
            builder.canDraw() ? builder.create(QColor(Qt::blue), QStringLiteral("sin x*sin y"))
                              : nullptr;
        if (item) {
            model.addPlot(item);
        }

        ExportPlotter3D plotter(&model);
        plotter.updatePlots(QModelIndex(), 0, model.rowCount() - 1);

        QVector<QVector3D> vertices;
        if (model.rowCount() > 0) {
            const QModelIndex index = model.index(0, 0);
            PlotItem *plot =
                index.data(PlotsModel::PlotRole).value<PlotItem *>();
            if (Surface *surface = dynamic_cast<Surface *>(plot)) {
                vertices = surface->vertices();
            }
        }
        report("3D plot model computes Surface vertices",
               builder.canDraw() && model.rowCount() == 1
                   && vertices.size() > 100);

        const QString path =
            QDir::current().absoluteFilePath(QStringLiteral("analitza-consumer-export.x3d"));
        QFile::remove(path);
        plotter.exportSurfaces(path);

        QFile exported(path);
        QByteArray document;
        if (exported.open(QIODevice::ReadOnly)) {
            document = exported.readAll();
            exported.close();
        }
        QFile::remove(path);

        report("Plotter3DES writes a valid X3D document",
               document.contains("<?xml")
                   && document.contains("<!DOCTYPE X3D")
                   && document.contains("<IndexedFaceSet")
                   && document.contains("<Coordinate point="),
               document.left(400));

        // 6) The save()/filters() capability path advertises X3D export on
        //    this build (PNG stays available; PDF depends on PrintSupport,
        //    which is intentionally not required here).
        const QStringList filters = plotter.filters();
        report("Plotter3DES filters advertise PNG and X3D export",
               filters.filter(QStringLiteral("*.png")).size() == 1
                   && filters.filter(QStringLiteral("*.x3d")).size() == 1);
    }

    // 7) AnalitzaGui: a VariablesModel over a real Analitza::Variables map
    //    lists the inserted variable with its evaluated value. Variables()
    //    already carries the builtin constants (true/false/pi/e/euler/i),
    //    so the lookup scans the model rows instead of assuming index 0.
    {
        auto variables = QSharedPointer<Variables>::create();
        VariablesModel model(variables);
        model.insertVariable(QStringLiteral("x"), Expression(QStringLiteral("42")));
        bool foundName = false;
        bool foundValue = false;
        QByteArray rows;
        for (int row = 0; row < model.rowCount(QModelIndex()); ++row) {
            const QString name =
                model.data(model.index(row, 0), Qt::DisplayRole).toString();
            const QString value =
                model.data(model.index(row, 1), Qt::DisplayRole).toString();
            rows += (name + QLatin1Char('=') + value + QLatin1Char('\n')).toUtf8();
            if (name == QStringLiteral("x")) {
                foundName = true;
                foundValue = value == QStringLiteral("42");
            }
        }
        report("VariablesModel exposes an inserted variable",
               foundName && foundValue, rows);
    }

    // 8) AnalitzaWidgets: the packaged QWidget view and line edit construct
    //    and keep their state (QApplication runs offscreen on the device).
    {
        PlotsView2D view;
        report("PlotsView2D constructs with the packaged AnalitzaWidgets",
               view.sizeHint().width() > 0);
    }
    {
        ExpressionEdit edit;
        edit.setText(QStringLiteral("sin x*sin y"));
        report("ExpressionEdit round-trips its text",
               edit.text() == QStringLiteral("sin x*sin y"));
    }

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}

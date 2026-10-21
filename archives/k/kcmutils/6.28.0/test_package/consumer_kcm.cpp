// Minimal KCM plugin built by the consumer test: a real KCMUtils plugin
// loaded through KCModuleLoader and embedded in a KCMultiDialog page.
#include <KPluginFactory>
#include <KPluginMetaData>
#include <kcmodule.h>

#include <QLabel>

class ConsumerKcm : public KCModule
{
public:
    ConsumerKcm(QObject *parent, const KPluginMetaData &data)
        : KCModule(parent, data)
    {
        new QLabel(QStringLiteral("kcmutils consumer test module"), widget());
    }

    void load() override
    {
        setNeedsSave(false);
    }
};

K_PLUGIN_CLASS_WITH_JSON(ConsumerKcm, "consumer_kcm.json")

#include "consumer_kcm.moc"

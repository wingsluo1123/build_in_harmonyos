/* mlite 兼容层实现：MDConfItem（ini 配置读取，替代 dconf） */
#include "MDConfItem"

#include <QFile>
#include <QTextStream>

MDConfItem::MDConfItem(const QString &key)
    : m_key(key)
{
}

QVariant MDConfItem::value() const
{
    const QByteArray path = qgetenv("MD_CONF_FILE");
    if (path.isEmpty())
        return QVariant(); // 未配置：等价于 dconf 键不存在

    QFile file(QString::fromLocal8Bit(path));
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
        return QVariant();

    QTextStream in(&file);
    QString group;
    while (!in.atEnd()) {
        QString line = in.readLine();
        if (line.isEmpty() || line.startsWith(QLatin1Char('#')))
            continue;
        if (line.startsWith(QLatin1Char('[')) && line.endsWith(QLatin1Char(']'))) {
            group = line.mid(1, line.size() - 2).trimmed();
            continue;
        }
        int eq = line.indexOf(QLatin1Char('='));
        if (eq <= 0)
            continue;
        QString key = line.left(eq).trimmed();
        // 拼接出的键必须带前导 '/'：上游 contentaction.cpp 以
        // MDConfItem("/desktop/sailfish/application_desktop_paths") 构造
        // （见上游 contentaction.cpp:75-76，键形态亦见 data/locks/
        // application_desktop_paths.txt）。ini 的 [group] 解析结果不含前导 '/'，
        // 若此处不补，fullKey 恒不等于 m_key → value() 恒返回空 →
        // application_desktop_paths 白名单塌缩为"无限制"（**静默 fail-open**，
        // 与白名单的限制意图相反）。故统一补前导 '/'，并对 m_key 做同样规整，
        // 使带/不带前导 '/' 的调用方都能命中。
        QString fullKey = group.isEmpty() ? key : group + QLatin1Char('/') + key;
        if (!fullKey.startsWith(QLatin1Char('/')))
            fullKey.prepend(QLatin1Char('/'));
        QString wanted = m_key;
        if (!wanted.startsWith(QLatin1Char('/')))
            wanted.prepend(QLatin1Char('/'));
        if (fullKey != wanted)
            continue;

        QString raw = line.mid(eq + 1).trimmed();
        // 必须**无条件**返回 QStringList：上游（及本仓 mlite 兼容层）以
        // QVariant::toStringList() 消费多值键。QVariant(QString) 的 toStringList()
        // 返回**空表**而非"单元素表"，若此处按单值返回 QString，则
        // application_desktop_paths 配成**单条**白名单时会得到空列表 →
        // 白名单塌缩为无限制（静默 fail-open，与"限制"意图相反）。
        // 按 ';' 切分对单值同样成立（无分隔符时 split 返回单元素表）。
        QStringList parts;
        const QStringList split = raw.split(QLatin1Char(';'));
        for (const QString &part : split) {
            const QString trimmed = part.trimmed();
            if (!trimmed.isEmpty())
                parts << trimmed;
        }
        return QVariant(parts);
    }
    return QVariant();
}

/* mlite 兼容层实现：MDesktopEntry（Desktop Entry 解析） */
#include "MDesktopEntry"

#include <QFile>
#include <QLocale>
#include <QTextStream>

namespace {

QString decodeEscapes(const QString &raw)
{
    QString out;
    out.reserve(raw.size());
    for (int i = 0; i < raw.size(); ++i) {
        QChar c = raw.at(i);
        if (c == QLatin1Char('\\') && i + 1 < raw.size()) {
            QChar n = raw.at(i + 1);
            ++i;
            if (n == QLatin1Char('s'))
                out += QLatin1Char(' ');
            else if (n == QLatin1Char('n'))
                out += QLatin1Char('\n');
            else if (n == QLatin1Char('t'))
                out += QLatin1Char('\t');
            else if (n == QLatin1Char('\\'))
                out += QLatin1Char('\\');
            else
                out += n;
        } else {
            out += c;
        }
    }
    return out;
}

} // namespace

MDesktopEntry::MDesktopEntry(const QString &fileName)
    : m_fileName(fileName)
    , m_valid(false)
{
    QFile file(fileName);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
        return;

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
        QString value = line.mid(eq + 1).trimmed();
        m_entries.insert(group + QLatin1Char('/') + key, decodeEscapes(value));
    }
    // freedesktop Desktop Entry 规范：必须存在 [Desktop Entry] 组
    m_valid = m_entries.contains(QLatin1String("Desktop Entry/Type"))
              || m_entries.contains(QLatin1String("Desktop Entry/Name"));
}

bool MDesktopEntry::contains(const QString &key) const
{
    return m_entries.contains(key);
}

QString MDesktopEntry::value(const QString &key) const
{
    return m_entries.value(key);
}

QString MDesktopEntry::name() const
{
    // mlite 走 MeeGo 翻译目录；兼容层按 Name[<locale>] / Name 兜底
    QString lang = QLocale::system().name(); // e.g. zh_CN
    QString localized = value(QLatin1String("Desktop Entry/Name[") + lang + QLatin1Char(']'));
    if (!localized.isEmpty())
        return localized;
    int underscore = lang.indexOf(QLatin1Char('_'));
    if (underscore > 0) {
        localized = value(QLatin1String("Desktop Entry/Name[")
                          + lang.left(underscore) + QLatin1Char(']'));
        if (!localized.isEmpty())
            return localized;
    }
    return value(QLatin1String("Desktop Entry/Name"));
}

QString MDesktopEntry::icon() const
{
    return value(QLatin1String("Desktop Entry/Icon"));
}

QString MDesktopEntry::type() const
{
    return value(QLatin1String("Desktop Entry/Type"));
}

QString MDesktopEntry::url() const
{
    return value(QLatin1String("Desktop Entry/URL"));
}

bool MDesktopEntry::terminal() const
{
    return value(QLatin1String("Desktop Entry/Terminal")).toLower()
           == QLatin1String("true");
}

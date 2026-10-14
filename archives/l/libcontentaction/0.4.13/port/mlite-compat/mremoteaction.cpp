/* mlite 兼容层实现：MRemoteAction（QtDBus 直连会话总线，替代 mapplauncherd） */
#include "MRemoteAction"

#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusPendingCall>

MRemoteAction::MRemoteAction(const QString &service,
                             const QString &path,
                             const QString &interface,
                             const QString &method,
                             const QVariantList &arguments)
    : m_service(service)
    , m_path(path)
    , m_interface(interface)
    , m_method(method)
    , m_arguments(arguments)
{
}

void MRemoteAction::trigger() const
{
    QDBusMessage msg = QDBusMessage::createMethodCall(
        m_service, m_path, m_interface, m_method);
    msg.setArguments(m_arguments);
    QDBusConnection::sessionBus().asyncCall(msg);
}

void MRemoteAction::triggerAndWait() const
{
    QDBusMessage msg = QDBusMessage::createMethodCall(
        m_service, m_path, m_interface, m_method);
    msg.setArguments(m_arguments);
    QDBusConnection::sessionBus().call(msg);
}

/* dbus-probe.cpp —— guest 侧 D-Bus 会话总线可达性探针
 *
 * 用途：被 port/run_py_case.sh 用作 **执行环境预检**（见该脚本 DBus 分支）。
 * 退出码：0 = 会话总线可连接；非 0 = 不可连接（调用方据此 SKIP 77）。
 *
 * ★为什么需要它（本机 ohos-aarch64-run 实测，可复现）★
 * 宿主侧 python3-dbus / dbus-daemon 齐备、总线地址也已正确导出到 guest，
 * 但 guest（aarch64 目标，经 qemu-user + OHOS musl 运行根执行）连上 unix socket 后
 * 在 D-Bus SASL 认证阶段被拒：
 *     AUTH EXTERNAL  -> REJECTED EXTERNAL
 *     ANONYMOUS 总线 -> REJECTED ANONYMOUS
 * 结果 QDBusConnection::sessionBus().isConnected() 恒为 false
 * （lastError: "Not connected to D-Bus server"）。
 * 这会让 lca-tool 的 X-Maemo-Method 触发**静默 no-op（RC=0）**，
 * 假服务收不到调用，用例只能在超时后 FAIL —— 失败现象完全指不到真实原因。
 *
 * 本探针走的就是被测库同一条路径（libQt6DBus），因此它的结论对用例有代表性。
 */
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusError>
#include <QDebug>
#include <QString>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const QDBusConnection bus = QDBusConnection::sessionBus();
    const bool ok = bus.isConnected();
    if (!ok) {
        qWarning() << "dbus-probe: session bus NOT connected:"
                   << bus.lastError().message();
    }
    return ok ? 0 : 1;
}

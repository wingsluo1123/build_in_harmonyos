// solid 6.14.0 consumer test (R34: exercises real API).
// Verifies Solid::Device::listFromType works (returns a list, possibly empty
// in a headless environment, which still proves linking and API usability).
#include <Solid/Device>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const QList<Solid::Device> devices =
        Solid::Device::listFromType(Solid::DeviceInterface::Block);
    std::printf("PASS: Solid::Device::listFromType OK (count=%d)\n",
                devices.count());
    return 0;
}

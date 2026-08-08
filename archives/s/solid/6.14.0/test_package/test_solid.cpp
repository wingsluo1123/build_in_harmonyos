// test_solid.cpp — Verify KF6Solid library links correctly
#include <Solid/Device>
#include <Solid/DeviceInterface>
#include <cstdio>

int main() {
    // Verify KF6Solid library is linkable and Solid API is callable
    auto devices = Solid::Device::listFromType(Solid::DeviceInterface::Processor);
    printf("solid test: KF6Solid linked and functional, found %d processors\n", (int)devices.size());
    return 0;
}

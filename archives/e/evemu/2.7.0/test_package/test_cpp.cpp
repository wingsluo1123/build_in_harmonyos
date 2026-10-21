// C++ consumer probe — mirrors upstream test/test-cxx-compile.cpp:
// proves <evemu.h> is a clean C++ include and libevemu links from C++.
#include <evemu.h>

extern "C" int evemu_cpp_probe(void);

int evemu_cpp_probe(void) {
    struct evemu_device *dev = evemu_new("evemu-cxx-consumer");
    if (!dev)
        return 1;
    evemu_delete(dev);
    return 0;
}

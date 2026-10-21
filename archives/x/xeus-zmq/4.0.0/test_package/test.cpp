#include <cassert>
#include <iostream>
#include <memory>

#include <xeus-zmq/xeus-zmq.hpp>
#include <xeus-zmq/xzmq_context.hpp>

int main() {
    // 1. Version macros exposed by the installed headers.
    std::cout << "xeus-zmq version: "
              << XEUS_ZMQ_VERSION_MAJOR << "."
              << XEUS_ZMQ_VERSION_MINOR << "."
              << XEUS_ZMQ_VERSION_PATCH << std::endl;
    assert(XEUS_ZMQ_VERSION_MAJOR == 4);
    assert(XEUS_ZMQ_VERSION_MINOR == 0);
    assert(XEUS_ZMQ_VERSION_PATCH == 0);

    // 2. Binary (SOVERSION) macros must match the installed libxeus-zmq.so.8.
    assert(XEUS_ZMQ_BINARY_CURRENT == 8);
    assert(XEUS_ZMQ_BINARY_REVISION == 0);
    assert(XEUS_ZMQ_BINARY_AGE == 0);

    // 3. Real API call: build the ZeroMQ-backed xeus context.
    std::unique_ptr<xeus::xcontext> ctx = xeus::make_zmq_context();
    assert(ctx != nullptr);

    std::cout << "xeus-zmq test passed" << std::endl;
    return 0;
}

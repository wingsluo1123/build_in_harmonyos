#include <libzmf/libzmf.h>
#include <librevenge-stream/RVNGStreamImplementation.h>

int main(void) {
    // Substantive dependency (R34): exercise the public ZMF document API,
    // not just default-construct. isSupported() + Type/Kind enums form
    // the primary public surface a consumer links against.
    static const unsigned char empty[1] = {0};
    librevenge::RVNGStringStream input(empty, 0);  // owned empty stream
    libzmf::ZMFDocument::Type type = libzmf::ZMFDocument::TYPE_UNKNOWN;
    libzmf::ZMFDocument::Kind kind = libzmf::ZMFDocument::KIND_UNKNOWN;
    (void)libzmf::ZMFDocument::isSupported(&input, &type, &kind);
    return 0;
}

#include <libzmf/libzmf.h>
#include <librevenge-stream/RVNGStreamImplementation.h>

#include <cassert>
#include <cstdio>

int main(void) {
    // Substantive dependency (R34): exercise the public ZMF document API,
    // not just default-construct. isSupported() + Type/Kind enums form
    // the primary public surface a consumer links against.
    static const unsigned char empty[1] = {0};
    librevenge::RVNGStringStream input(empty, 0);  // owned empty stream
    libzmf::ZMFDocument::Type type = libzmf::ZMFDocument::TYPE_UNKNOWN;
    libzmf::ZMFDocument::Kind kind = libzmf::ZMFDocument::KIND_UNKNOWN;
    // isSupported() returns false for an empty stream (not a valid ZMF file).
    // Asserting the negative path verifies the API was actually called and
    // the libzmf symbols linked correctly (P3: test too weak).
    bool supported = libzmf::ZMFDocument::isSupported(&input, &type, &kind);
    assert(!supported);
    assert(type == libzmf::ZMFDocument::TYPE_UNKNOWN);
    assert(kind == libzmf::ZMFDocument::KIND_UNKNOWN);
    printf("libzmf::ZMFDocument::isSupported test OK: supported=%d type=%d kind=%d\n",
           static_cast<int>(supported), static_cast<int>(type), static_cast<int>(kind));
    return 0;
}

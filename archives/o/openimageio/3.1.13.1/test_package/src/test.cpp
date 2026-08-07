// Test that OpenImageIO headers and libraries are usable.
// This test includes OIIO's imageio header and creates an ImageSpec,
// which exercises the OIIO API and links against the OIIO libraries.
#include <OpenImageIO/imageio.h>
#include <iostream>

int main() {
    // Verify OIIO library is linked by using the API
    std::cout << "OpenImageIO version: " << OIIO_VERSION_STRING << std::endl;

    // Create an ImageSpec to exercise the API
    OIIO::ImageSpec spec(64, 64, 3, OIIO::TypeDesc::UINT8);
    if (spec.width != 64 || spec.height != 64 || spec.nchannels != 3) {
        std::cerr << "ImageSpec values mismatch" << std::endl;
        return 1;
    }

    std::cout << "ImageSpec: " << spec.width << "x" << spec.height
              << "x" << spec.nchannels << std::endl;
    std::cout << "OIIO test passed" << std::endl;
    return 0;
}

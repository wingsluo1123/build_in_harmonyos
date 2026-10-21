#include <clipper/core/cell.h>
#include <clipper/clipper.h>

#include <cstdlib>
#include <iostream>

int main() {
    std::cout << "=== clipper 2.1.20201109 consumer test ===" << std::endl;

    // Test 1: Cell construction (null constructor)
    clipper::Cell cell;
    std::cout << "Cell is_null: " << cell.is_null() << std::endl;

    // Test 2: Coord_orth operations
    clipper::Coord_orth a(1.0, 2.0, 3.0);
    clipper::Coord_orth b(4.0, 5.0, 6.0);
    clipper::Coord_orth c = a + b;
    std::cout << "Coord sum: (" << c[0] << "," << c[1] << "," << c[2] << ")" << std::endl;

    std::cout << "=== clipper consumer test PASSED ===" << std::endl;
    return EXIT_SUCCESS;
}

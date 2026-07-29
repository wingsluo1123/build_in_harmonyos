#include <CGAL/version.h>

#include <iostream>

int main() {
    if (CGAL_VERSION_NR != 1060111000) {
        std::cerr << "Unexpected CGAL version: " << CGAL_VERSION_STR << '\n';
        return 1;
    }

    std::cout << "CGAL version: " << CGAL_VERSION_STR << '\n';
    return 0;
}

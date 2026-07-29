# CGAL

CGAL is a C++ library of computational geometry algorithms and data
structures. Version 6.1.1 is packaged from the official library-only release
archive as an architecture-independent header package.

## Conan usage

```cmake
find_package(CGAL CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE CGAL::CGAL)
```

The package itself has no build-time dependency. Consumers selecting CGAL
algorithms that use Boost, GMP, MPFR, Eigen, or Qt must provide the relevant
dependencies.

## References

- Homepage: https://www.cgal.org/
- Source: https://github.com/CGAL/cgal
- Documentation: https://doc.cgal.org/latest/Manual/index.html

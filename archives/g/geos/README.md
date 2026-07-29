# GEOS

GEOS is a C++ library for performing operations on two-dimensional vector geometries. It provides the geometry engine used by projects such as PostGIS, QGIS, and Shapely.

## Features

- OGC Simple Features geometry model and predicates
- Spatial operations such as intersection, union, buffer, and distance
- Stable C API and an advanced C++ API
- `geosop` command-line utility for inspecting and processing geometries

## OpenHarmony adaptation

GEOS 3.12.1 uses its upstream CMake build without source patches. The Conan recipe builds static libraries by default, exports the upstream CMake target names, runs the registered upstream CTest suite, and packages `geosop` and `geos-config`.

## Dependencies

GEOS has no required third-party library dependencies. Consumers of the static C API also link the packaged C++ library and the platform C++ runtime.

## References

- https://libgeos.org/
- https://github.com/libgeos/geos

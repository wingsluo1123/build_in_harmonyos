# libmygpo-qt

`libmygpo-qt/1.1.0` provides the shared Qt5 gpodder.net API client, depending on `qt5-qtbase/5.15.2.2`.
Conan consumers use `find_package(Mygpo-qt5 CONFIG REQUIRED)` and target `mygpo-qt5`.

Both upstream QtTest programs are built and executed, followed by an installed-library C++ consumer.
The tests run offline; no live gpodder.net account or service is required.

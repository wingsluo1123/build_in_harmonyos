# skladnik

skladnik is the KDE Sokoban ("warehouse keeper") game: the player pushes
stones across a level until every stone sits on a goal field, moving through
the five built-in collections (Sasquatch, Mas Sasquatch, Sasquatch III,
Microban, Sasquatch IV) that ship embedded in the binary as a Qt resource.
It is the maintained continuation of ksokoban.

## Features

- Qt6 Widgets / QGraphicsView board rendering through the KDEGames6
  KGameRenderer SVG theme engine (themes/skladnik_classic.svg plus 16
  sprite PNGs installed under share/skladnik/themes).
- Move history with undo/redo, a built-in Sokoban solver (PathFinder) for
  hints and auto-solve, level bookmarks, and HTML export of a solved level.
- External level collections loaded from a local file, from a remote URL, or
  by drag and drop.
- KDBusService single-instance activation, KXmlGui menus/toolbars and the
  standard KDE shortcut configuration dialog.

## OHOS adaptation

- KIO is trimmed. Upstream touches it in exactly two places in
  src/MainWindow.cpp: KIO::file_copy to download a remote level collection
  into a temporary file, and KUrlMimeData::urlsFromMimeData to read the URLs
  of a drop payload. They are replaced by QNetworkAccessManager (with
  NoLessSafeRedirectPolicy, blocking on a nested QEventLoop exactly like the
  upstream job->exec()) and QMimeData::urls(), so http/https/ftp/file
  collection URLs and URL drops keep working. Only KIO-proprietary VFS
  schemes (smb://, webdav://, ...) are lost, and their kioslave backends are
  not published for this platform anyway. KIO cannot simply be added because
  of version-line incompatibility: kio is published at 6.14.0/6.26.0 while
  libkdegames (a REQUIRED dependency) pins the KF6 6.18.0 line, and mixing
  lines changes every KF6 package id so no prebuilt binary matches.
- The DocBook handbook is skipped. Upstream already treats KF6DocTools as
  optional, so the recipe only sets
  CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE; no patch is needed.
- POV-Ray is disabled via CMAKE_DISABLE_FIND_PACKAGE_POVRay=TRUE so the build
  always uses the sprite PNGs shipped in the tarball instead of regenerating
  them when a povray binary happens to be present.
- KF_IGNORE_PLATFORM_CHECK=TRUE bypasses the KDE platform allowlist and
  KF_SKIP_PO_PROCESSING=ON skips translation catalog generation.
- The executable is linked with -Wl,-z,max-page-size=0x1000 on OHOS: the
  default lld page size splits .dynsym/.dynstr into a separate high-address
  RW LOAD segment that the OHOS musl loader refuses to mmap.
- qtbase and the KF6 packages are published with cmake_find_mode=none, so the
  recipe writes conan_cmakedeps_paths.cmake by hand and injects
  ECM_MODULE_PATH.
- The Qt/KF host tools (moc, uic, rcc, kconfig_compiler) are themselves OHOS
  binaries, so the build and test environments put every dependency lib dir
  plus /system/lib64 on LD_LIBRARY_PATH. At run time the game needs
  QT_QPA_PLATFORM=offscreen and an isolated HOME for headless verification,
  and the executable must carry a valid .codesign section or OHOS refuses to
  exec-map it.

Known limitations: no DocBook handbook, no translated catalogs, and no
KIO-proprietary VFS schemes for remote collections. Core gameplay is complete.

## Dependencies

Build and runtime, all resolved from the ohpcd artifact registry:
qtbase/6.11.1 (Qt6 Core/Gui/Widgets/Network), the KF6 6.18.0 line (kconfig,
kconfigwidgets, kcoreaddons, kcrash, kdbusaddons, ki18n, kwidgetsaddons,
kcodecs, kxmlgui), karchive/6.18.0 pinned with override=True for closure
consistency, kiconthemes/6.18.0.1 pinned with override=True (6.18.0.1 is the
adaptation-fix release whose published binary matches this karchive/6.18.0
closure, so the whole graph stays prebuilt and CI rebuilds no dependency from
source), and libkdegames/26.04.0 (KDEGames6). Build tool: ecm/6.26.0.

## Products

- bin/skladnik (the game)
- share/skladnik/themes/ (theme desktop file, SVG and 16 sprite PNGs)
- share/icons/hicolor/*/apps/skladnik.png
- share/applications/org.kde.skladnik.desktop
- share/metainfo/org.kde.skladnik.metainfo.xml

## References

- Upstream: https://invent.kde.org/games/skladnik
- Release tarball: https://download.kde.org/stable/release-service/26.04.2/src/skladnik-26.04.2.tar.xz
- App page: https://apps.kde.org/skladnik

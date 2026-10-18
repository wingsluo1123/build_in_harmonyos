/* config.h — hand-written for HarmonyOS PC (OHOS aarch64) Conan build.
 * Equivalent to upstream autotools-generated config.h with optional
 * features (dbus/exif/udisks/old-actions/menu-cache-children) disabled.
 */
#ifndef FM_CONFIG_H
#define FM_CONFIG_H

#define GETTEXT_PACKAGE "libfm"
#define PACKAGE "libfm"
#define PACKAGE_NAME "libfm"
#define PACKAGE_STRING "libfm 1.4.0"
#define PACKAGE_TARNAME "libfm"
#define PACKAGE_VERSION "1.4.0"
#define VERSION "1.4.0"

/* Install paths (OHOS PC hnp layout) */
#define PACKAGE_MODULES_DIR "/data/service/hnp/lib/libfm/modules"
#define PACKAGE_DATA_DIR "/data/service/hnp/share/libfm"
#define PACKAGE_LOCALE_DIR "/data/service/hnp/share/locale"

/* Platform features */
#define HAVE_MMAP 1
#define USE_TRASH 1

/* Disabled optional features: ENABLE_DBUS / ENABLE_NLS / USE_EXIF /
 * USE_UDISKS / HAVE_OLD_ACTIONS / HAVE_MENU_CACHE_DIR_LIST_CHILDREN */

#endif /* FM_CONFIG_H */

# GNOME Recipes

GNOME Recipes is a GTK3 desktop application for finding, cooking and sharing
recipes, backed by the recipe databases shipped with the release.

## OHOS adaptation

- The Todoist shopping-list export is ported from librest (rest-0.7) to
  direct libsoup 2.4 form-encoded POSTs; the registry's librest/0.10.2 is
  the rest-1.0/libsoup3 generation (no rest-0.7.pc, and libsoup2+libsoup3
  cannot coexist in one process).  Upstream's meson.build only loses the
  rest-0.7 dependency line.
- The graph is unified DOWN on the glib/2.84.0.1.1 + zlib/1.3.1.1
  generation with a root override: every published GTK3-stack binary was
  built against that generation, while libgoa/json-glib/gnome-autoar pin
  glib/2.88.3 / zlib/1.3.2 — a generation with no GTK3 binaries yet.
  Unifying up would orphan all 13 published binaries and force a full
  source rebuild of the stack; unifying down keeps them all and leaves
  libgoa/3.58.1 as the sole source build (rebuilt against glib/2.84.0.1.1).
- Appdata translations are shipped untranslated and the help/ subdirectory
  is disabled, because msgfmt ITS rules, itstool and yelp-tools are not
  available in the target environment.
- The desktop post-install hooks (icon cache, desktop database) are skipped;
  the GSettings schema is compiled into the package at packaging time with
  the staged glib-compile-schemas.

## Dependencies

| Dependency | Purpose |
|---|---|
| gtk/3.24.43 | GTK 3 desktop UI |
| glib/2.84.0.1.1 | GLib, GObject, GIO (unified umbrella) |
| libsoup/2.74.3-r1 | Todoist form POSTs for the shopping-list export |
| libgoa/3.58.1 | GNOME Online Accounts (Todoist token retrieval; rebuilt from source against glib/2.84.0.1.1) |
| json-glib/1.10.6.1 | Todoist payload parsing |
| gnome-autoar/0.4.5 | Recipe archive export/import |
| gspell/1.14.4 | Spell checking in the recipe editor |
| libcanberra/0.30 | UI sounds |

## Reference

- Upstream: https://gitlab.gnome.org/GNOME/gnome-recipes
- Source release: https://download.gnome.org/sources/gnome-recipes/2.0/gnome-recipes-2.0.4.tar.xz

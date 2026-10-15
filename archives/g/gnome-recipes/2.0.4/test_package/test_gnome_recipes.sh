#!/bin/sh
set -eu

package=$1
run_binary=$2
# Colon-separated dependency lib dirs computed in conanfile.py's test()
# (runtime closure of the graph's shared libraries, e.g. libarchive).
ld_dirs=${3:-}

if [ -n "$ld_dirs" ]; then
    LD_LIBRARY_PATH="$ld_dirs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export LD_LIBRARY_PATH
fi

binary="$package/bin/gnome-recipes"
desktop="$package/share/applications/org.gnome.Recipes.desktop"
appdata="$package/share/metainfo/org.gnome.Recipes.appdata.xml"
schema="$package/share/glib-2.0/schemas/org.gnome.Recipes.gschema.xml"
compiled_schema="$package/share/glib-2.0/schemas/gschemas.compiled"
icon="$package/share/icons/hicolor/512x512/apps/org.gnome.Recipes.png"
recipes_db="$package/share/gnome-recipes/recipes.db"
chefs_db="$package/share/gnome-recipes/chefs.db"

test -x "$binary"
test -s "$desktop"
test -s "$appdata"
test -s "$schema"
test -s "$compiled_schema"
test -s "$icon"
test -s "$recipes_db"
test -s "$chefs_db"
grep -q '^Type=Application$' "$desktop"
grep -q '^Exec=gnome-recipes %f$' "$desktop"
grep -q 'org.gnome.Recipes' "$appdata"

if [ "$run_binary" = 1 ]; then
    "$binary" --help >/dev/null 2>&1
fi

echo "gnome-recipes package smoke test: OK"

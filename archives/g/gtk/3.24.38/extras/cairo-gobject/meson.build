# Standalone meson.build for the vendored cairo-gobject 1.18.4 library.
#
# The published cairo/1.18.4 conan package intentionally disables the glib
# glue library (cairo-gobject), but GTK+ 3.24.38's meson build hard-requires
# `dependency('cairo-gobject')` and links the cairo_*_get_type() symbols.
#
# Upstream layout: cairo-1.18.4/util/cairo-gobject/{cairo-gobject-enums.c,
# cairo-gobject-structs.c,cairo-gobject.h}.  We vendor those three verbatim
# files plus this minimal build file and a stub config.h, and build the tiny
# glue library inside the gtk recipe before configuring gtk itself.
#
# cairo-gobject only depends on cairo + glib/gobject headers; all of those are
# provided by the conan dependency .pc files in the generators folder.
project('cairo-gobject', 'c', version: '1.18.4',
  default_options: ['buildtype=release', 'warning_level=0'])

cairo_dep = dependency('cairo')
glib_dep = dependency('glib-2.0')
gobject_dep = dependency('gobject-2.0')

cairo_gobject_sources = [
  'cairo-gobject-enums.c',
  'cairo-gobject-structs.c',
]

libcairogobject = library('cairo-gobject', cairo_gobject_sources,
  include_directories: include_directories('.'),
  dependencies: [glib_dep, gobject_dep, cairo_dep],
  # cairo 制品包未启用 glib 胶水库，cairo-features.h 没有定义
  # CAIRO_HAS_GOBJECT_FUNCTIONS；此处显式声明，模拟 glib 启用的 cairo。
  c_args: ['-DCAIRO_COMPILATION', '-DCAIRO_HAS_GOBJECT_FUNCTIONS=1'],
  soversion: '2',
  version: '2.11804.4',
  install: false,
)

cairogobject_dep = declare_dependency(link_with: libcairogobject,
  include_directories: include_directories('.'),
  dependencies: cairo_dep)

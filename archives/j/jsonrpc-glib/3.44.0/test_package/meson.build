project('test-jsonrpc-glib', 'c')

gio_dep = dependency('gio-2.0')
json_glib_dep = dependency('json-glib-1.0')
jsonrpc_glib_dep = dependency('jsonrpc-glib-1.0')

executable('test_package', 'src/main.c',
  dependencies: [jsonrpc_glib_dep, json_glib_dep, gio_dep],
)

project('test_libxmlb', 'c',
  meson_version : '>=0.60.0',
  default_options : ['c_std=c99'],
)

xmlb = dependency('xmlb')
cc = meson.get_compiler('c')
dl = cc.find_library('dl', required : false)

test_libxmlb = executable(
  'test_libxmlb',
  sources : ['test_libxmlb.c'],
  dependencies : [xmlb],
)

test_ohos_runtime = executable(
  'test_ohos_runtime',
  sources : ['test_ohos_runtime.c'],
  dependencies : [xmlb, dl],
)

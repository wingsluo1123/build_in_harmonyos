project('test_wfutils', 'cpp', default_options: ['cpp_std=c++17'])

wfutils_dep = dependency('wf-utils')
test_wfutils = executable('test_wfutils', 'test.cpp', dependencies: wfutils_dep)
test('test_wfutils', test_wfutils)

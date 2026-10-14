project('libadwaita-1-test', 'c',
  version: '1.0',
  default_options: ['warning_level=2'])

libadwaita_dep = dependency('libadwaita-1')

exe = executable('libadwaita-1-test',
  sources: ['main.c'],
  dependencies: [libadwaita_dep],
  install: false)

test('libadwaita-1-test', exe)

# HarmonyOS-specific end-to-end consumer use case (赛事 rule12): a real
# consumer program that initializes libadwaita with the Broadway display
# backend, creates actual controls, sets properties, drives the GTK main
# loop and asserts observable behavior. Built as an independent executable
# target; executed under gtk4-broadwayd (see conanfile.py test() / PR body).
e2e = executable('libadwaita-1-e2e-consumer',
  sources: ['consumer_main.c'],
  dependencies: [libadwaita_dep],
  install: false)

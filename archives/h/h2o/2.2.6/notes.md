# H2O 2.2.6

The upstream project defines test execution as its custom CMake `check` target.
The recipe builds that target after the normal build; it is not replaced with a
consumer-only smoke test. MRuby is disabled because it needs host Ruby and
Bison during the target build. The selected H2O core, event-loop, picotls and
Perl test path remain upstream code.

# H2O 2.2.6

The upstream project defines test execution as its custom CMake `check` target.
The recipe runs that target after the normal build whenever the target is
runnable; cross builds require separate target-side test evidence. It is not
replaced with a consumer-only smoke test. Perl is a declared build tool because
the target invokes `prove`. MRuby is disabled because it needs host Ruby and
Bison during the target build. The selected H2O core, event-loop, picotls and
Perl test path remain upstream code.

# Perl 5.42.2 upstream compatibility scope

The Conan package version is `5.42.2.1`; its upstream source and runtime version are `5.42.2`.

A prior full `make test_harness_notty` run on OHOS executed 2,908 test programs and reported 2,864 passing programs (98.49%). Remaining failures were concentrated in platform semantics not required by the build-tool consumers of this package:

- hard-link and symbolic-link creation on the worker filesystem;
- chmod, `-w`, and actual-writeability differences;
- process-name, signal, termios, locale, and timezone behavior;
- SysV IPC blocked at runtime;
- Unix-domain socket path limits;
- direct execution of temporary shell scripts.

The recipe addresses build-blocking behavior without claiming full upstream-suite conformance:

- link operations used by the build are implemented through a copy wrapper;
- package installation uses actual create/unlink write probes;
- unsupported SysV IPC is excluded;
- broken `prctl` process-name handling is disabled;
- scripts are invoked through an explicit shell;
- build temporary files stay under the build directory.

The `5.42.2.1` compatibility revision specifically closes the native-module failure observed in CI build #33233. Perl executables and XS shared objects are signed before installation, final package artifacts are checked for `.codesign`, and the Conan consumer test actually loads `Fcntl` and `POSIX`.

The full upstream suite is intentionally not represented as passing. Acceptance is limited to a correctly packaged Perl build tool and its tested core/XS runtime paths required by downstream configure and script workloads.

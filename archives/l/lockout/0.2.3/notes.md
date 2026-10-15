# lockout 0.2.3 adaptation notes

`lockout` is a single Perl script.  The recipe rewrites its `#!/usr/bin/perl -w`
shebang to the Perl interpreter found on the build target and runs `perl -c`
before installation.

The installed command is tested only through `lockout status` and the usage
path.  The test does not invoke `lockout lock`, `lockout unlock`, `usermod`,
`passwd`, or any administrator hook.

#!/usr/bin/env python3
"""test_package for dma 0.14 — consumer assertions driving the shipped CLI.

dma is a pure CLI/MTA (package_type=application): it ships no library and no
headers, so the consumer test drives the installed `dma` binary the way a
mail(1)/sendmail(8) frontend would invoke it.

Both assertions run entirely inside the argument-parsing stage, upstream of
`parse_conf(CONF_PATH "/dma.conf")` at dma.c:606 — verified against the v0.14
tag by reading the control flow:

    dma.c:458  set_username()          (util.c:224 — reads uid/login only)
    dma.c:464  root-privilege drop     (skipped: uid is not 0)
    dma.c:503  getopt() loop
    dma.c:551  case 'q': doqueue = 1   (optstring `...O:q:r:...` — q takes an argument)
    dma.c:573  case ':': missing-argument path, optopt == 'q' -> doqueue = 1
    dma.c:581  default: fprintf(stderr, "invalid argument: `-%c'\\n", optopt)
    dma.c:582  exit(EX_USAGE)                       <-- assertion 1 fires here
    dma.c:585  argc -= optind   (musl getopt missing-arg path leaves optind == argc+1)
    dma.c:588  if (argc != 0 && (showq || doqueue))
    dma.c:590  errx(EX_USAGE, "sending mail and queue operations are mutually exclusive")
                                                      <-- assertion 2 fires here (observed rc=64)
    dma.c:592  if (showq + doqueue > 1)  (only when -q really consumes an operand, e.g. `dma -bp -q x`)
    dma.c:593  errx(EX_USAGE, "conflicting queue operations")   <-- NOT this assertion's path
    dma.c:595  skipopts:
    dma.c:606  parse_conf(CONF_PATH "/dma.conf")    <-- AFTER both assertions

Neither assertion reaches parse_conf, parse_authfile, load_queue, the spool,
or the delivery path, so no queue path and no real mail delivery is exercised.
Assertion 2 uses `-bp` (showq=1, dma.c:513-515) together with `-q` (doqueue=1);
because no operand follows `-q`, musl's getopt missing-argument branch advances
optind to argc+1, `argc -= optind` yields -1, and the operand guard at dma.c:588
fires first (observed: rc=64 with the message above). `-bq` would NOT work:
dma.c:516-518 maps it to queue_only, leaving showq+doqueue == 1 and both guards
untriggered.
"""
import os

from conan import ConanFile


class DmaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries — wrap with
        # bash, same pattern as the executable test_package template.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh', env="conanrun")

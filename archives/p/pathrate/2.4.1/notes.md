# Pathrate 2.4.1 on HarmonyOS PC

The recipe uses FreeBSD's official ports distfile cache for the original
`pathrate.tar.gz` (66,463 bytes). Its SHA256
`ae247a88e09bcb86ad14d8784dca5912006aa342e074078f32f5b9dc3599668b`
matches FreeBSD `benchmarks/pathrate/distinfo` and was checked on the
HarmonyOS PC before building. The official `pkg.freebsd.org` HTTPS endpoint
serves the identical archive with valid TLS verification. The four C translation units use system
POSIX sockets, pthreads and libm; there are no Conan package dependencies.

The original `config.guess` predates HarmonyOS, so the recipe compiles the
sender and receiver directly from the source groups in `makefile.in` with
Clang. The first patch corrects the sender's `getopt` result type from `char`
to `int`: on this AArch64 target plain `char` is unsigned, so `-1` could never
end the argument loop. The upstream measurement algorithm and its `-Q`
quick mode are retained.

The upstream archive has four C files and no test directory, test script,
test target or formal test case (0 upstream cases). `test_package/test.py`
defines two integration cases: installed CLI help for both programs and a
full sender/receiver UDP loopback capacity run. The latter builds
a test-only `LD_PRELOAD` shaper from `pace_udp.c` to add a 1 ms gap between
sender UDP datagrams. This supplies a controlled measurable bottleneck on
fast loopback without changing the packaged sender. It runs the installed
programs in HarmonyOS PC user storage, requests `-Q`, and asserts a positive
finite capacity interval plus successful exit. It does not claim to validate
capacity accuracy on a real remote link. The program's fixed TCP and UDP
ports 48699 and 48698 require this test to run serially.

## Independent HarmonyOS end-to-end consumer (rule12)

`ohos_consumer.c` is a separately compiled consumer of the delivered sender,
not an assertion-only addition. `run_consumer.py` launches the installed
`pathrate_snd`, then executes this independent C client without LD_PRELOAD.
The client constructs two fixed probe requests (rounds 41/42, lengths 4/8,
packet sizes 256/1024), performs ten TCP echo exchanges, configures the real
sender, receives both UDP packet trains, checks every packet/round/train ID,
acknowledges each completed train and sends GAME_OVER. The installed sender
must exit 0. The client writes an ordered report in HarmonyOS user storage;
the runner reopens it and compares every byte with a fixed independent
reference calculated as 5*256 + 9*1024 = 10,496 bytes in 14 datagrams.

Conan test() compiles this consumer and invokes its runner after the two
existing integration cases. Native Conan create on 2026-10-15 passed all
three cases, including the new complete consumer. The capacity run yielded
114–115 Mbps. Classification: upstream 0, integration 2, HarmonyOS-specific
end-to-end consumer 1, total 3. The existing Python files still contain 11
static assert statements; the C consumer uses explicit failure exits.

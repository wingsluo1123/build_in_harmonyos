# cascade-compiler g20200105.1

## Source and platform

- Upstream: `https://github.com/vmware-archive/cascade`
- Commit: `f4f7ae8bd1dd379790c0e58c286df90b8d1cdcde`
- Device: HarmonyOS aarch64
- The source test runner has 294 GoogleTest declarations. The ten 64-bit Avalon/Verilator cases use software simulators, so the recipe extends their architecture guards to include aarch64. CTest registers one `regression` target that runs all 294 GoogleTest cases.
- Regression targets use Cascade's software simulator plus software Avalon and Verilator simulation. The regression sources contain no DE10 or ULX3S test cases.

## Build dependencies

- Conan: `ncurses/6.4`, `flex/2.6.4.2`, `bison/3.8.2`, `googletest/1.18.0`, `google-benchmark/1.9.5`.
- The device profile supplies Harmonybrew Autoconf 2.73 and Perl; this pair is used to generate Verilator's `configure` script. Conan's Autoconf 2.72 binary package carries an incompatible Perl module path on this device.
- Verilator's generated `config.status` uses an owner-only temporary directory by default. On the device's `/storage` mount that denies writes to the build account, so the recipe runs `configure --no-create` and changes both temporary-directory umask branches to retain private group access before running `config.status`.
- The Conan Bison executable has non-relocatable `/share/bison` and M4 paths; the recipe points `BISON_PKGDATADIR` to the package's verified data tree and `M4` to the device's GNU M4 during native builds.
- HarmonyOS exposes `/tmp` as read-only, and pathname AF_UNIX binds on writable `/storage` return `EPERM`. Regression simulator scratch files use a configurable `CASCADE_TMP_DIR`; the remote regression runner uses a per-process abstract AF_UNIX name plus an ephemeral TCP port. Abstract AF_UNIX bind/connect works on the target.
- Verilator 4.038's `bisonpre` emits `verilog.h` for the Bison 3.8.2 output even though its generated header is `V3ParseBison.h`; the recipe corrects that include and adds the Conan Flex package's `FlexLexer.h` directory to native compile flags.
- CMake finds the Conan Flex executable but does not discover its header directory, so the recipe sets `FLEX_INCLUDE_DIR` to the verified package include directory.
- The device has no `install` utility on `PATH`, and Verilator's generated install rules call its non-executable relative `install-sh` from a child directory. The recipe invokes the packaged script through `/bin/sh` using its absolute path.
- Verilator 4.038 is built from its verified upstream source archive with `make -j2`, then packaged under `tools/verilator` so the Verilator backend is usable from the Conan run environment.

## Source adaptations

- Correct the upstream CMake library declaration and honor `BUILD_SHARED_LIBS`.
- Add CMake include and library search directories for Conan dependencies.
- Resolve the `sw_fpga` terminal library through Conan's CMakeDeps target so it links to the packaged wide-character ncurses library.
- Include the POSIX select and timeval declarations explicitly for HarmonyOS libc.
- Resolve Verilator headers using the private `VERILATOR_ROOT` rather than assuming a system install directory.
- Give remote regression tests a process-specific abstract Unix socket name and an ephemeral TCP port. The test declarations and test logic remain intact; the runner closes both listeners after the suite.
- Run CTest from its binary `test` directory so the relative `../src/libcascade.so` dependency resolves on HarmonyOS while source assets remain anchored to the executable path.
- Enable the unchanged 64-bit Avalon/Verilator software regression cases on aarch64, covering all upstream declarations on this 64-bit target.
- Remove the process-name `pkill` from Verilator shutdown. The runner waits synchronously on its own compilation child, and global process-name searches could affect another session.

## Timeout investigation

- The earlier failed CI output ended at `[ RUN      ] simple.hello_3` and the CTest timeout. That line identifies the last test started, but not the blocking call.
- `simple.hello_3` calls `run_code("regression/minimal", ...)`. The harness does not call `set_stdin()`, the `minimal` march selects software simulation rather than JIT, and the test does not reach the hardware backends that call `System::tmp_root()`. The exact test therefore does not read stdin, execute JIT, or use `CASCADE_TMP_DIR`.
- The previous Conan CMake helper command contained `-- -j20 -j2`: Conan selected 20 jobs and then appended the recipe's `-j2` argument. This did not enforce the requested two-job limit on the shared, memory-constrained device. The recipe now invokes CMake directly with `--parallel 2` in both the main build and `test_package`; the device log contains no `-j20` build command.
- The old fixed `CASCADE_TMP_DIR` was a separate cross-task isolation defect. Both test paths now derive it from their own `self.build_folder`; it protects the simulator regression suite without being the direct cause of `simple.hello_3`.
- The repaired device run passed `simple.hello_3` in 136 ms. A bounded focused run then passed that same test 500/500 times. This supports the job-count/resource-pressure diagnosis; the prohibited `-j20` control run was not repeated on the shared device.

## Verification

- The final Conan create on HarmonyOS aarch64 exited 0. CTest ran its one upstream `regression` entry (1/1); GoogleTest reported 294 tests from 16 suites, 294 passed, 0 failed, 0 skipped, in 290.063 s. The `simple` suite ran 106/106 cases in 14.232 s.
- Conan's packaged consumer test configured, built, and ran `test_cascade` successfully; the overall Conan create exit code was 0.
- Raw device evidence: `reports/device-create.log` (SHA-256 `d107d0621d695a6eb7f1369883fdddd4a164e39a801c1edb9140c1c914539299`) and `reports/diagnostic/hello3-repeat.log` (SHA-256 `9586cd6d63e508fe496751a790195147e61a820142249217eb1a3ff7a3ff6b6b`).

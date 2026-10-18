# msktutil 1.2.2 adaptation notes

- Upstream: https://github.com/msktutil/msktutil (release tag 1.2.2)
- Build system: Autotools (configure.ac / Makefile.in, dist tarball ships
  generated `configure` + `config.h.in`, no autoreconf needed)
- Deliverable: `sbin/msktutil` command-line tool + man page only — this is
  an application package (package_type = application).

## Key adaptations

1. **Source**: upstream 1.2.2 release tarball
   (`releases/download/1.2.2/msktutil-1.2.2.tar.gz`, sha256 verified in
   conandata.yml). It contains `configure`/`config.h.in`, so build()
   runs configure directly (unlike adcli whose GitLab snapshot needs
   `autoreconf -fi`).
2. **Platform triplet**: config.guess (2024 vintage) cannot identify
   HarmonyOS (uname -s = "HarmonyOS"), so configure gets an explicit
   `--build/--host=aarch64-unknown-linux-gnu` (same approach as the
   cyrus-sasl/openldap recipes).
3. **System dependencies**: MIT krb5, OpenLDAP (libldap/liblber/libcom_err)
   and Cyrus SASL headers are hard configure-time requirements but are NOT
   published to the ohpcd artifact repo; generate() provisions openldap
   2.6.7 + krb5 1.22.1 from cmd-pkgs prebuilt packages and vendors
   sasl.h/prop.h from the upstream cyrus-sasl 2.1.28 tag (same approach as
   the adcli 0.9.2 recipe; msktutil uses only SASL types, no -lsasl link).
   configure is pointed there via CPPFLAGS/LDFLAGS plus `-Wl,-rpath`.
4. **udns disabled**: `--with-udns=no` — the optional udns resolver backend
   is off; the libc/libresolv ns_initparse/res_search fallback is used, so
   libudns is not a dependency.
5. **HMDFS**: drop `umask 077` from configure so config.status can create
   its temp dir (E114/E011); `make` is serialized (`-j1`, E074 jobserver
   fifo); PWD/TMPDIR pinned to writable dirs ([shell_getcwd]/[readonly_tmp]).

## Upstream tests

Upstream 1.2.2 ships NO test suite: the release tree has no tests/test
directory, and Makefile.in defines no `check`/`TESTS` target (only
all/clean/distclean/install/dist/distcheck, where distcheck merely echoes
the version). `make check` has no rule. The audit is recorded in
test_package/MANIFEST.yml (`upstream_tests_exist: false`,
`upstream_test_total: 0`); test_package validates the packaged binary
instead (6 offline consumer checks, no Active Directory needed).

Final pass counts and current commit evidence are recorded in the PR after
all validation gates complete.

## 真机预检轮次记录

### 首轮（2026-10-14，未提交工作树）

- 按 adcli 0.9.2（同为 AD 域工具、同依赖、autotools）与 cvechecker 4
  （同为无上游测试的 autotools 工具）先例编写配方，未经过真机验证。
- 待 HMBS 后台真机预检返回 structured 结果后再按失败日志修复。

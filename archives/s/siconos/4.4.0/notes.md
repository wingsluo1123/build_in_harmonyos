# Siconos4.4.0 adaptation notes

W3 compiled the pinned official source and all38 declared patches, ran the
complete selected native suite, installed the package and executed its real
consumer tests. W3 exit0 means the explicit build acceptance policy was met;
the upstream reference result is **PARTIAL**, with original CTest exit8.

| Unit | Discovered/executed | PASS | FAIL | SKIP | Result |
|---|---:|---:|---:|---:|---|
| CTest native groups | 110/110 | 108 | 2 | 0 | 98.18% |
| Nested CppUnit methods | 234/234 | 232 | 2 | 0 | Separate denominator, not added to CTest |
| Installed consumer assertions | 29/29 | 29 | 0 | 0 | C14 + C++15, two executables |

The original111-container configuration has one empty AVI container. Its sole
case is guarded by HAS_EXTREME_POINT_ALGO; the registration now uses the same
guard and TestMain rejects empty suites.241 fixture declarations in registered
targets yield234 active methods;7 conditional methods are inactive (AVI1,
SMC2, Twisting4). No runnable case was removed.

The34 numerical collections produced **1132 individual solver records**:
`{"PASS": 949, "UNSTABLE_FAIL": 5, "UNSTABLE_PASS": 5, "XFAIL": 151, "XPASS": 22}`. XFAIL, XPASS and unstable outcomes keep
their original classifications and are not folded into ordinary PASS.
Ordinary PASS is949/1132
(83.83% of all solver records).
All stable expected-success records pass; expected-failure and unstable labels
come from the upstream collection classification. The C application requests
explicit confirmation of these units and labels; container98.18% must not be
presented as the ordinary-PASS fraction of solver records.

## Retained reference failures

| Method | Actual difference | Original tolerance | Original result | Independent evidence |
|---|---:|---:|---|---|
| `SMCTest::test_eSMC_Lsodar` | 8.313261e-11 | 7e-11 | FAIL / normal child exit1 | Same failed method on original Linux; baseline value recorded separately |
| `TwistingTest::test_ExplicitTwisting_Lsodar` | 77.41228 | 7e-11 | FAIL / normal child exit1 | Same failed method on original Linux; baseline value recorded separately |

Linux used the same archive and unchanged numerical code/golden files.
All3865 upstream files were compared;
only3 nonnumerical support files differ.
The paired Linux raw JUnit/dashboard and source integrity record are supplied.
Native C/C++/Fortran separate multiply/add rounding removes the additional
porting differences: all original ZOH integration checks pass their unchanged
reference tolerances; complete observations remain in the paired raw output.

The two original Twisting references themselves differ by78.0583 over their
long trajectory. The held-input local equation and actual control signs are
checked independently, together with both explicit-SMC trajectories. These
checks retain the original golden FAIL; they do not replace it with PASS.
The policy binds exact group names, per-group method/solver counts, finite
comparison records, actual child exit1 and normal completion. Signals,
missing output, zero cases, new failures and truncated collections block.
The reproducible negative-control script rejected all17
listed mutations; exact scenarios and output hashes are supplied separately.

The projected-gradient Armijo criterion uses the equivalent quadratic
increment `(1-mu)*g_k.dot(d) + 0.5*d.dot(M*d)` under the API's symmetric
positive-semidefinite matrix contract. This avoids cancellation between
nearly equal objective values. The original tolerance, step rules, maximum
iterations and final residual oracle remain unchanged; its original FC3D
collection must pass and is not part of the reference-failure exception.

## Installed artifact and relocation

Artifact: `siconos/4.4.0#2bd7ff49b30999e23786e7b1efdb7b43`, package ID `577bcbce8d5e0073c1cb3ad7d4e202aba17be875`,
package revision `3521862e3eb992f57da2f91b649fb515`. Native CMake consumers built
and ran while the original package and build directory were physically hidden.
C14 checks include dense BLAS/LAPACK, sparse CXSparse and actual Fortran QL0001.
C++15 checks include ownership, affine integration, sensors,2000 impact steps,
signed contact gap/penetration and IO for TIDS/Diagonal systems.
The relocated CLI directly reports4.4.0 and compiles/installs/runs the same15
C++ checks; this reexecution is not15 additional unique assertions.
All6 installed libraries have basename DT_NEEDED entries and no RPATH/RUNPATH.

## Scope and reproducibility

Components: externals/numerics/kernel/control/mechanics/io; Fortran ON.
Python bindings are OFF as an explicit native-package scope choice (the
upstream default is ON);24 Python test source files are outside this scope.
Default-off MUMPS/FCLIB/Bullet/OCE/serialization and unstable NCP variants
are not represented as executed. Eight unregistered CppUnit headers contain40
source declarations:11 optional Bullet/OCE,15 IO serialization and14 legacy
kernel declarations absent from the active upstream CMake registration.
Source-level declarations, CTest containers, methods and assertions are
different units; no whole-project/all-configuration100% claim is made.

Reproduce with the submitted recipe, an OHOS/armv8 SDK profile and published
GMP/Boost/OpenBLAS/CppUnit/Flang dependencies. `conan create ... --build='siconos/*'`
runs the complete suite and exact policy. `recipe-inputs.json` binds the input
files; source SHA256 is363238d57a32347fce5dd4924d24a0862dbbe48e3887f4b5236aa93d0be0e3e5.
The official CI may replace only the source URL with its private pre-download
cache locator. `recipe-built-inputs.json` records actual exported hashes;
`recipe-transport-binding.json` proves that reversing exactly that one locator
restores canonical metadata byte-for-byte and the archive has the same SHA256.
All other42 inputs must match exactly. This transport rewrite is not committed.

Raw upstream JUnit SHA256: `586e5c09e89f15658e6926d6864cbc76f1dee551cda568b40fc42a3075e5730b`.
Raw process dashboard SHA256: `71feffd740d0c99ef627aa3a906176d0a3d680fbf3ae81faeec1fcffdb29acf0`.
W3 full-log SHA256: `946361753410aa0b60a0bf0017328745c85278e890a3d634e9e83e3ca492177a`.

### 对话 #1

**编译结束**：依据本轮正式W3及安装工件报告。
**最终状态**：built；上游参考结果PARTIAL（108/110组、232/234方法、原CTest8），两个原始FAIL保留；尚未发布制品。

完整原始证据按固定提交及逐文件SHA保存，参见当前 `reports/evidence-index.md` / `evidence-index.json`。原始报告已移出当前diff，未删改数据或测试判定。

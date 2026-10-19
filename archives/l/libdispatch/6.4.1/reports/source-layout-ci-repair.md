# PR15756 CI91435 source-layout repair

Failure baseline HEAD: 48e4ded0c756b37f29de5ecdc101335e61f8a176.
Buildbot buildid105045, build91435, worker OpenHarmonyPCDeveloper-CI-010.
worker-prep, clone, checkout and setup passed; source() first failed at
`get(..., strip_root=True)` with IsADirectoryError './PATCHES'.

The exact official archive has a regular PATCHES file, while Conan exports
the recipe's patches/ directory to its source root. A case-insensitive worker
cannot represent those as two separate root names. Download and SHA checks
had passed. This is a recipe source-layout defect, not dependency unavailability
and not a transient network failure.

The code fix is standard `cmake_layout(self, src_folder="upstream")`.
Official URL and SHA, all upstream files, all15 source patches, build options,
37 CTest IDs and original assertions remain unchanged. CMake configure,
apply_conandata_patches and LICENSE copy follow self.source_folder naturally.

## Direct source regression

Conan2.29.1 on case-insensitive Windows, create-new private home/download cache,
verified official bytes, actual conan source; two checks passed:

- Original frozen recipe RC1, PermissionError '.\\PATCHES'; the output path is
  proven to alias the existing patches directory. Windows uses errno13 for
  this directory open, while the Harmony worker logged errno21.
- Fixed recipe RC0; upstream/PATCHES remains a file, patches/ remains a distinct
  directory with all15 patches, and upstream/CMakeLists.txt is present.

Original regression log SHA256 b07704dd2cc6df469b061c7a6970f7fc37167374207265eebe8d0a39949ddaae.
Fixed regression log SHA256 5312181ee1ae4e391bb7b97d5b688d56d06d062c6ce394cdf7351ff096781cfb.
This source-only regression does not claim target runtime PASS.

## Fresh native Conan

Run libdispatch-conan-w3-20261014-r3, endpoint10.62.210.132:2222,
boot2488bc3f-f5fe-4b70-b131-07c630c7157b, UID20020084,
unique PID31282/start163994958, baselineHEAD above, stagedtree
750e3fd045deb403800cef7217e02229d2104f8d.

Shared and static each: conan create RC0, full upstream37/37, installed
consumer1/1. Twelve phases, release/postrelease and owned-child cleanup pass.
Recipe RREV5b71ed0071d6821fb8ac732073b3db41.
Shared PID01d92cf349a0dd98ff915f4bd99a04430171517f/PREVd98bfe03ac194d0ac93099fe78ec234b.
Static PID21b17f8b2bc0e9511e276e3d57a23893067cefe5/PREVd831a44880dcf6106f64b0b962ac1d09.
Raw log SHA2569f10bf6b8e8444620bbf7b18cd08ea4ba24b206c0e38b8571dc76d32374e625c.

All tests and installed consumers execute from fresh private Conan builds;
the standard source cache only holds hash-checked official archive bytes.
New knowledge E550-draft-LD65 explains the cross-library namespace boundary.
No award/publication, current-HEAD platform CI success or new Review is claimed.
Official finish libdispatch-finish-w3-20261014-r6 completed RC0; ConanVerifier
and local CI each passed37/37 plus consumer1/1. All12 phases, release/postrelease,
W5/W2 and submit readiness pass. Finish logSHA256
be4b3d10531cbbaa7c1ce0ae8dec4b4319fc81198acaed8e2fd2fc36921e8cdc;
producer local CI logSHA256
9ccb79a4abad1365f3d1d6cdc4976455088cf5dc88eedc7cc636fb5e3d18d6c5.
The .ci-result producer artifact is copied unchanged with its exact log.
Current-HEAD platform Review and rebuild are still required.

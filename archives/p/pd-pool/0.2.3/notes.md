# pd-pool 0.2.3 HarmonyOS PC

No automated upstream suite; release ships the interactive pool-help.pd example. Consumer drives numeric and symbol keys, overwrite, directory isolation, clear, recursive counts and persistence through installed pd.

Source: https://mirrors.aliyun.com/debian/pool/main/p/pd-pool/pd-pool_0.2.3.orig.tar.xz (SHA256 `5779b5e51b66eb1f01cb27f77a003323925e763161d775f3d90cdb8ec7e45b32`).

Native validation: `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -c tools.build:jobs=1 --build=missing`.

The recipe retains upstream source code. Every command has bounded test execution. Build jobs are limited to one to fit shared CI and device resources.

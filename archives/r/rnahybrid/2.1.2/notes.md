# RNAhybrid 2.1.2 HarmonyOS PC

Build all three upstream computation programs with libm. Optional g2/gd graphics are disabled because g2 is not available in the artifact repository; no graphical output is claimed.

Version identity is the original Debian rnahybrid_2.1.2.orig.tar.gz archive (SHA256 in conandata.yml), README 2.1.2 and Makefile VERSION=2.1.2. The upstream Autoconf PACKAGE_VERSION remains the older 1.0; the recipe does not regenerate or substitute a different source release.

The sole source patch addresses existing HMDFS permission issue E011 in generated config.status: select umask 022 on HarmonyOS while retaining 077 on other systems. Legacy tentative global definitions use the compiler's supported -fcommon mode. The numerical algorithm is unchanged.

The release's install-sh explicitly supports only one source file, but the generated Automake install rule passes all three programs together and silently installs only the first. package() copies and checks the explicit inventory of all three built programs and all three man pages.

Upstream has no automated suite; the generated make check target executes zero cases. The consumer exercises official README FASTA and dinucleotide-frequency examples through the installed RNAhybrid, RNAcalibrate and RNAeffective programs (eight cases).

Every subprocess has a 120-second timeout. The recipe serializes compilation and executes make check before packaging. Full command: conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -c tools.build:jobs=1 --build=missing.

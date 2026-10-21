# SOAPsnp

SOAPsnp 1.03 calls consensus genotypes from a FASTA reference and sorted SOAP alignments.
The GPL-3.0-or-later upstream orig archive is preserved by Ubuntu's official archive.
Conan reference: `soapsnp/1.03`.
Install with the official OpenHarmony AArch64 profile and run `soapsnp --version`.
Example: `soapsnp -i reads.soap -d reference.fa -o calls.cns`.
The test package contains eight CLI integration cases and one OpenHarmony calibration-matrix consumer.
Local validation uses OHOS 7 Beta AArch64 QEMU with official OHOS6 profile metadata.
See `1.03/notes.md` for dependency, test and runtime boundaries.

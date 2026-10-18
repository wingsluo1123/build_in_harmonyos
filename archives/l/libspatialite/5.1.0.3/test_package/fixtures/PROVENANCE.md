# Original spreadsheet integration fixture

Official FreeXL archive:
https://www.gaia-gis.it/gaia-sins/freexl-2.0.0.tar.gz
SHA-256: 176705f1de58ab7c1eebbf5c6de46ab76fcd8b856508dbd28f5648f7c6e1a7f0
Member: freexl-2.0.0/tests/testdata/oocalc_simple97.xls
Fixture SHA-256: 429839277db32a934f2c01f4bf9ef6f928385610794a10173987111bb3290253

First worksheet has one header and one data row. The new consumer tests actual
load_XL and VirtualXL results rather than just compilation/macros. Original
license notices are included. No prior target test is claimed for this revision.

Transport: oocalc_simple97.xls.b64 is canonical 76-column LF Base64 of the original 6656-byte upstream XLS. The consumer decodes it only in its build directory and checks size/SHA-256 before the unchanged load_XL/VirtualXL data tests. The original bytes and license remain unchanged; encoded text is never used as XLS input.

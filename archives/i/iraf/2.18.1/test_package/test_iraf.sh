#!/usr/bin/env zsh
set -euo pipefail
testroot="$(mktemp -d "${TMPDIR:-$PWD}/iraf-consumer.XXXXXX")"
trap 'rm -rf "$testroot"' EXIT HUP INT TERM
export TMPDIR="$testroot/tmp"
mkdir -p "$TMPDIR"
export uparm="$testroot/uparm/" cache="$testroot/cache/" imdir="$testroot/imdir/"
mkdir -p "$uparm" "$cache" "$imdir"
cd "$testroot"
export PATH="$IRAF_PACKAGE/bin:$PATH"
irafcl -V < /dev/null > version.out
grep -q '2.18.1' version.out
echo 'PASS 1: installed IRAF version'

cat > basic.cl <<'EOF'
print (6 * 7)
logout
EOF
irafcl -f basic.cl < /dev/null > basic.out 2>&1
grep -qE '^[[:space:]]*42[[:space:]]*$' basic.out
echo 'PASS 2: ECL arithmetic'
cl -f basic.cl < /dev/null > classic.out 2>&1
grep -qE '^[[:space:]]*42[[:space:]]*$' classic.out
echo 'PASS 3: classic CL arithmetic'

cat > image.cl <<'EOF'
artdata
mkpattern ("source.imh", pattern="constant", ndim=2, ncols=8, nlines=8, v1=7.)
imstatistics ("source.imh", fields="npix,mean", format=no)
imcopy ("source.imh", "result.fits", verbose=no)
imstatistics ("result.fits", fields="npix,mean", format=no)
imcopy ("result.fits", "restored.imh", verbose=no)
imstatistics ("restored.imh", fields="npix,mean", format=no)
logout
EOF
irafcl -f image.cl < /dev/null > image.out 2>&1
test "$(grep -cE '^[[:space:]]*64[[:space:]]+7\.' image.out)" = 3
test -s result.fits
echo 'PASS 4: image creation and statistics'
echo 'PASS 5: FITS round trip'

cat > hello.x <<'EOF'
task hello = t_hello
procedure t_hello ()
begin
    call printf ("OHOS SPP 42\n")
end
EOF
xc hello.x
test -x hello.e
cat > spp.cl <<'EOF'
task $hello = hello.e
hello
logout
EOF
irafcl -f spp.cl < /dev/null > spp.out 2>&1
grep -qx 'OHOS SPP 42' spp.out
echo 'PASS 6: installed SPP -> Ratfor -> Fortran -> C -> AArch64 compiler chain'

cat > recover.cl <<'EOF'
reset erract = "abort notrace nobeep flpr"
iferr {
    error (17, "expected OHOS context test")
} then {
    print ("OHOS recovered")
}
print (21 * 2)
logout
EOF
irafcl -f recover.cl < /dev/null > recover.out 2>&1
grep -qE '^OHOS recovered[[:space:]]*$' recover.out
awk '/^OHOS recovered[[:space:]]*$/{seen=1} /^[[:space:]]*42[[:space:]]*$/{if(!seen)exit 1;done=1} END{if(!done)exit 1}' recover.out
echo 'PASS 7: ECL error recovery preserves the following statement'
"$CC" -O2 -I"$IRAF_PACKAGE/lib/iraf/unix/hlib/libc" "$IRAF_TEST_SOURCES/test_context.c" \
    "$IRAF_PACKAGE/lib/iraf/unix/bin.linux64/libos.a" -o context-test
./context-test
echo 'PASS 8: installed libos production declarations/macros: context status 42, 0 -> 1, and -7'
printf 'this is invalid Fortran\n' > invalid.f
if xc -c invalid.f > invalid.out 2>&1; then
    echo 'FAIL: installed compiler swallowed invalid Fortran' >&2
    exit 1
fi
echo 'PASS 9: installed compiler propagates a real F2C error'
cat > ssh-fixture <<'EOF'
#!/bin/sh
set -eu
test "$#" = 6
test "$1" = -T
test "$2" = -l
test "$3" = fixture-user
test "$4" = --
test "$5" = iraf-fixture.invalid
test "$6" = fixture-command
printf 'READY\n'
IFS= read -r value
printf 'ECHO:%s\n' "$value"
printf 'ERR\n' >&2
EOF
chmod 755 ssh-fixture
"$CC" -O2 "$IRAF_TEST_SOURCES/test_rcmd.c" \
    "$IRAF_PACKAGE/lib/iraf/unix/bin.linux64/libos.a" -o rcmd-test
KSRSH="$testroot/ssh-fixture" timeout 30 ./rcmd-test
echo 'PASS 10: SSH stream, stderr, descriptor closure, invalid input and exec errors'
xc -N -o hello_nfs.e hello.x
test -x hello_nfs.e
sed 's/hello.e/hello_nfs.e/' spp.cl > spp-nfs.cl
irafcl -f spp-nfs.cl < /dev/null > spp-nfs.out 2>&1
grep -qx 'OHOS SPP 42' spp-nfs.out
echo 'PASS 11: compiler -N uses writable scratch and copies the linked program'
printf 'print ("OHOS INIT")\n' > init.cl
export iraf="$IRAF_PACKAGE/lib/iraf/" IRAFARCH=linux64 tmp="$TMPDIR/"
"${iraf}bin.linux64/ecl.e" -i init.cl -f basic.cl < /dev/null > init.out 2>&1
grep -qx 'OHOS INIT' init.out
grep -qE '^[[:space:]]*42[[:space:]]*$' init.out
echo 'PASS 12: ECL initialization concatenation uses the VOS temporary directory'
printf 'value i\n' > scalar.cd
printf '1\n2\n' > first.dat
printf '3\n4\n' > second.dat
printf 'pixels r[64]\n' > array.cd
: > empty.dat
cat > tables.cl <<'EOF'
reset erract = "abort notrace nobeep flpr"
artdata
mkpattern ("mismatch.imh", pattern="constant", ndim=2, ncols=8, nlines=8, v1=7., pixtype="short")
nttools
tcreate ("first.tab", "scalar.cd", "first.dat")
tcreate ("second.tab", "scalar.cd", "second.dat")
tmerge ("first.tab,second.tab", "merged.tab", option="append")
tinfo ("merged.tab", ttout=no)
print ("TMERGE_ROWS ", tinfo.nrows)
tdump ("merged.tab", cdfile="", pfile="", datafile="merged.dat")
tcreate ("pixels.tab", "array.cd", "empty.dat")
tiimage ("source.imh", "pixels.tab[c:pixels]", row=1, verbose=no)
tdump ("pixels.tab", cdfile="", pfile="", datafile="pixels.dat")
iferr {
    tiimage ("mismatch.imh", "pixels.tab[c:pixels]", row=2, verbose=no)
} then {
    print ("TYPE_REJECTED")
}
tinfo ("pixels.tab", ttout=no)
print ("PIXEL_ROWS ", tinfo.nrows)
logout
EOF
irafcl -f tables.cl < /dev/null > tables.out 2>&1
grep -qE '^TMERGE_ROWS[[:space:]]+4[[:space:]]*$' tables.out
awk '{print $1}' merged.dat > merged.values
printf '1\n2\n3\n4\n' > expected.values
diff -w expected.values merged.values
echo 'PASS 13: tmerge appends all four source values'
awk '{for(i=1;i<=NF;i++){n++;if($i+0 != 7)bad++}}END{if(n!=64 || bad)exit 1}' pixels.dat
echo 'PASS 14: tiimage copies every pixel of a 2D image into a table array'
grep -qE '^TYPE_REJECTED[[:space:]]*$' tables.out
awk '/^TYPE_REJECTED[[:space:]]*$/{seen=1} /^PIXEL_ROWS[[:space:]]+1[[:space:]]*$/{if(!seen)exit 1;done=1} END{if(!done)exit 1}' tables.out
echo 'PASS 15: tiimage rejects a mismatched pixel type'
printf 'guard\n' > guarded.txt
cat > protect.cl <<'EOF'
reset erract = "abort notrace nobeep flpr"
protect ("guarded.txt")
delete ("guarded.txt", verify=no)
print ("PROTECT_PRESENT ", access ("guarded.txt"))
unprotect ("guarded.txt")
delete ("guarded.txt", verify=no)
print ("PROTECT_REMOVED ", access ("guarded.txt"))
logout
EOF
irafcl -f protect.cl < /dev/null > protect.out 2>&1
grep -q 'Attempt to delete a protected file (guarded.txt)' protect.out
grep -qE '^PROTECT_PRESENT[[:space:]]+yes[[:space:]]*$' protect.out
grep -qE '^PROTECT_REMOVED[[:space:]]+no[[:space:]]*$' protect.out
echo 'PASS 16: protected files survive deletion until explicitly unprotected'
echo 'IRAF_CONSUMER_SCENARIOS=16/16 IRAF_CONSUMER_ASSERTIONS=33/33'

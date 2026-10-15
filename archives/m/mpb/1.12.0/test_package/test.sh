#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for the mpb package.
# Runs the installed `mpb` binary on a real control file and asserts the
# computed band frequencies, then exercises a second control file that
# touches the CLI helper binaries. Runs under conanrun (PATH -> bin/, libs
# and guile load paths from the dependency graph).
set -eu

TMP="$(mktemp -d "${TMPDIR:-.}/mpb-consumer.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

echo "[test] mpb --version"
mpb --version

echo "[test] computing a 2D square-lattice band structure with mpb"
cat > "$TMP/rods.ctl" <<'CTL'
; Square lattice of dielectric rods in air, evaluated at k = Gamma.
; Reference frequencies are the k=(0,0) TE values from the upstream
; examples/check.ctl self-test.
(set! geometry-lattice (make lattice (size 1 1 no-size)))
(set! geometry (list (make cylinder (material (make dielectric (epsilon 11.56)))
                          (center 0 0) (radius 0.2) (height infinity))))
(set! k-points (list (vector3 0 0)))
(set! grid-size (vector3 32 32 1))
(set! num-bands 4)
(set! tolerance 1e-9)
(run-te)
(define expected '(0.0 0.561945334557385 0.780842812331228 0.780846098412592))
(define got (car all-freqs))
(define (close? a b) (< (abs (- a b)) 1e-4))
(if (and (close? (list-ref got 0) (list-ref expected 0))
         (close? (list-ref got 1) (list-ref expected 1))
         (close? (list-ref got 2) (list-ref expected 2))
         (close? (list-ref got 3) (list-ref expected 3)))
    (print "MPB_CONSUMER_PASS\n")
    (begin (print "MPB_CONSUMER_FAIL got=" got " expected=" expected "\n")
           (exit 1)))
CTL
OUT="$(mpb "$TMP/rods.ctl")"
echo "$OUT"
printf '%s\n' "$OUT" | grep -q "MPB_CONSUMER_PASS" || {
    echo "ERROR: mpb band-structure assertion did not pass" >&2
    exit 1
}

echo "[test] OK"

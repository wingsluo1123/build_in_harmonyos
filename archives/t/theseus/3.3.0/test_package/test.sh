#!/data/service/hnp/bin/bash
# test_package/test.sh — real-computation test for the theseus executable.
# Data: 1s40.pdb — upstream-shipped examples/1s40.pdb (10-model NMR family of
# a telomere protein bound to ssDNA). Command: the exact demo from upstream
# examples/README: "theseus 1s40.pdb"
set -u

echo "[test] theseus 1s40.pdb (upstream demo: ML superposition of 10 models)"
out=$(theseus 1s40.pdb 2>&1); rc=$?
if [ "$rc" -ne 0 ]; then
    printf '%s\n' "$out" | tail -20
    echo "FAIL: theseus 1s40.pdb exited with $rc"
    exit 1
fi
printf '%s\n' "$out" | tail -10

# assertion 1: the ML superposition actually ran and reported its result
echo "$out" | grep -q "Maximum Likelihood <sigma>" || {
    echo "FAIL: no ML superposition result (<sigma>) in output"; exit 1; }
# assertion 2: Bayesian (Gibbs-Metropolis) statistics were produced
echo "$out" | grep -q "Marginal Log Likelihood" || {
    echo "FAIL: no Marginal Log Likelihood in output"; exit 1; }
# assertion 3: classical LS pairwise RMSD was reported
echo "$out" | grep -q "Classical LS pairwise <RMSD>" || {
    echo "FAIL: no Classical LS pairwise <RMSD> in output"; exit 1; }

# clean the files theseus writes next to the input (keep the tree pristine)
rm -f theseus_ave.pdb theseus_sup.pdb theseus_residuals.txt \
      theseus_transf.txt theseus_variances.txt \
      theseus_LS_tree.nxs theseus_ML_tree.nxs

echo "PASS: theseus ML superposition on 1s40.pdb (3/3 assertions)"

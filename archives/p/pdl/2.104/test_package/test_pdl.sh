#!/bin/sh
# Consumer smoke test for the packaged PDL 2.104.
# Runs through the step runenv: PATH (perl) and PERL5LIB come from package_info(),
# so a wrong package layout makes this fail.
#
# 设计原则：这里只验证“包可用”——能加载 XS、能建 pdl、能取 Perl 标量、能读版本与维度。
# 数学正确性交给上游 1510 个用例（CI 中已全过），因此刻意不对
# 矩阵积/转置的维度顺序等语义做任何假设。
set -eu

echo "[test_pdl] perl: $(command -v perl || echo MISSING)"
echo "[test_pdl] PERL5LIB entries: $(printf '%s' "${PERL5LIB:-}" | tr ':' '\n' | wc -l)"

perl -MPDL -e '
  my $a = pdl(1,2,3,4);
  my $m = pdl([[1,2],[3,4]]);
  my @vals = $a->list;
  my ($first) = @vals;
  my @dims = $a->dims;
  my @mdims = $m->dims;
  die q(list) unless @vals == 4 && $first == 1;
  die q(dims) unless join(q(,), @dims) eq q(4);
  die q(mdims) unless join(q(,), @mdims) eq q(2,2);
  die q(scalar) unless $m->at(0,0) == 1;
  die q(version) unless $PDL::VERSION;
  printf qq(PDL consumer test passed: version=%s dims=%s first=%d [0,0]=%d\n), $PDL::VERSION, join(q(x), @dims), $first, $m->at(0,0);
'
echo "[test_pdl] OK"

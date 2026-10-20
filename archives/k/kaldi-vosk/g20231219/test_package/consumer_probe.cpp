// SPDX-License-Identifier: Apache-2.0
#include "matrix/kaldi-matrix.h"
#include <fst/fstlib.h>
#include <cmath>

extern "C" int kaldi_vosk_consumer_probe() {
  kaldi::Matrix<double> a(2, 2), result(2, 2);
  a(0, 0) = 2; a(0, 1) = 1; a(1, 0) = 3; a(1, 1) = 4;
  result.AddMatMat(1.0, a, kaldi::kNoTrans, a, kaldi::kTrans, 0.0);
  if (std::abs(result(0, 0) - 5) > 1e-12 || std::abs(result(1, 1) - 25) > 1e-12)
    return 1;
  fst::StdVectorFst graph;
  graph.AddState(); graph.SetStart(0); graph.SetFinal(0, fst::TropicalWeight::One());
  return graph.NumStates() == 1 && graph.Start() == 0 ? 0 : 2;
}

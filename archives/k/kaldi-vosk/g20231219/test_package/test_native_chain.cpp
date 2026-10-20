// SPDX-License-Identifier: Apache-2.0
// Independent consumer of the installed Kaldi/Vosk CPU libraries.
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include <fst/matcher-fst.h>
#include "online/online-audio-source.h"
#ifdef KALDI_TEST_NGRAM
#include <fst/extensions/ngram/ngram-fst.h>
#endif
#include <fst/register.h>
#include "feat/feature-fbank.h"
#include "feat/feature-mfcc.h"
#include "feat/online-feature.h"
#include "feat/wave-reader.h"
#include "fstext/fstext-lib.h"
#include "matrix/matrix-lib.h"
#include "matrix/cblas-wrappers.h"
#include "nnet3/nnet-utils.h"
#include "online2/online-nnet3-incremental-decoding.h"

namespace {
using namespace kaldi;
int assertions = 0;
int cases = 0;

void Check(bool condition, const std::string &name) {
  ++assertions;
  if (!condition) throw std::runtime_error(name);
  std::cout << "[PASS] " << name << '\n';
}

void Begin(const std::string &name) {
  ++cases;
  std::cout << "[STEP] case " << cases << ": " << name << std::endl;
}

template <typename Real>
double IdentityError(const Matrix<Real> &matrix) {
  double error = 0;
  for (int32 r = 0; r < matrix.NumRows(); ++r)
    for (int32 c = 0; c < matrix.NumCols(); ++c)
      error = std::max(error, std::abs(double(matrix(r, c)) - (r == c ? 1 : 0)));
  return error;
}

template <typename Real>
void NumericalTests(const char *precision) {
  const double tolerance = sizeof(Real) == 4 ? 3.0e-5 : 2.0e-12;
  Begin(std::string(precision) + " CBLAS GEMM against scalar reference");
  Matrix<Real> a(3, 4), b(4, 2), product(3, 2);
  for (int32 r = 0; r < a.NumRows(); ++r)
    for (int32 c = 0; c < a.NumCols(); ++c) a(r, c) = Real(r * 3 - c + 0.25);
  for (int32 r = 0; r < b.NumRows(); ++r)
    for (int32 c = 0; c < b.NumCols(); ++c) b(r, c) = Real(r + c * 2 - 0.5);
  product.AddMatMat(1.0, a, kNoTrans, b, kNoTrans, 0.0);
  double gemm_error = 0;
  for (int32 r = 0; r < 3; ++r) {
    for (int32 c = 0; c < 2; ++c) {
      double reference = 0;
      for (int32 k = 0; k < 4; ++k) reference += double(a(r, k)) * double(b(k, c));
      gemm_error = std::max(gemm_error, std::abs(double(product(r, c)) - reference));
    }
  }
  Check(gemm_error < tolerance, "GEMM max absolute error < precision threshold");

  Begin(std::string(precision) + " LAPACK LU inverse and determinant");
  Matrix<Real> matrix(3, 3);
  const double values[9] = {4, 1, 2, 1, 3, 0, 2, 0, 5};
  for (int32 r = 0; r < 3; ++r)
    for (int32 c = 0; c < 3; ++c) matrix(r, c) = Real(values[r * 3 + c]);
  Matrix<Real> inverse(matrix), identity(3, 3);
  Real logdet = 0, sign = 0;
  inverse.Invert(&logdet, &sign);
  identity.AddMatMat(1.0, matrix, kNoTrans, inverse, kNoTrans, 0.0);
  Check(IdentityError(identity) < tolerance, "LU inverse residual");
  Check(sign == 1 && std::abs(std::exp(double(logdet)) - 43.0) < tolerance * 100,
        "LU determinant agrees with integer cofactor reference");

  Begin(std::string(precision) + " LAPACK packed symmetric inverse");
  SpMatrix<Real> symmetric(matrix), symmetric_inverse(symmetric);
  symmetric_inverse.Invert();
  Matrix<Real> dense_symmetric(symmetric), dense_inverse(symmetric_inverse);
  identity.AddMatMat(1.0, dense_symmetric, kNoTrans, dense_inverse, kNoTrans, 0.0);
  Check(IdentityError(identity) < tolerance, "SPTRF/SPTRI inverse residual");

  Begin(std::string(precision) + " LAPACK packed triangular inverse");
  TpMatrix<Real> triangular(3);
  triangular(0, 0) = 2;
  triangular(1, 0) = 1; triangular(1, 1) = 3;
  triangular(2, 0) = -1; triangular(2, 1) = 2; triangular(2, 2) = 4;
  TpMatrix<Real> triangular_inverse(triangular);
  triangular_inverse.Invert();
  Matrix<Real> dense_triangular(triangular), dense_triangular_inverse(triangular_inverse);
  identity.AddMatMat(1.0, dense_triangular, kNoTrans, dense_triangular_inverse, kNoTrans, 0.0);
  Check(IdentityError(identity) < tolerance, "TPTRI inverse residual");

  Begin(std::string(precision) + " LAPACK SVD reconstruction and orthogonality");
  Matrix<Real> u(3, 3), vt(3, 3);
  Vector<Real> singular_values(3);
  matrix.Svd(&singular_values, &u, &vt);
  Matrix<Real> us(u), reconstruction(3, 3);
  us.MulColsVec(singular_values);
  reconstruction.AddMatMat(1.0, us, kNoTrans, vt, kNoTrans, 0.0);
  reconstruction.AddMat(-1.0, matrix);
  identity.AddMatMat(1.0, u, kTrans, u, kNoTrans, 0.0);
  Check(reconstruction.FrobeniusNorm() < tolerance * 10, "GESVD reconstruction residual");
  Check(IdentityError(identity) < tolerance, "GESVD orthogonal U");

  Begin(std::string(precision) + " LAPACK singular matrix reports positive INFO");
  KaldiBlasInt rows = 2, cols = 2, stride = 2, info = 0, pivots[2] = {};
  Real singular[4] = {1, 2, 2, 4};
  clapack_Xgetrf2(&rows, &cols, singular, &stride, pivots, &info);
  Check(info > 0, "GETRF rejects rank deficient matrix");
  std::cout << "[METRIC] " << precision << " gemm_error=" << gemm_error
            << " svd_error=" << reconstruction.FrobeniusNorm() << '\n';
}

Vector<BaseFloat> Signal() {
  Vector<BaseFloat> wave(8000);
  for (int32 i = 0; i < wave.Dim(); ++i) {
    // Integer-valued deterministic PCM, independent of platform sin() rounding.
    int32 value = ((i * 137 + (i * i % 1021)) % 6001) - 3000;
    wave(i) = static_cast<BaseFloat>(value);
  }
  return wave;
}

Matrix<BaseFloat> MfccReference() {
  MfccOptions opts;
  opts.frame_opts.dither = 0;
  opts.frame_opts.snip_edges = false;
  Mfcc mfcc(opts);
  Matrix<BaseFloat> output;
  mfcc.ComputeFeatures(Signal(), 16000, 1.0, &output);
  return output;
}

void FeatureTests(const std::string &feature_output) {
  Begin("MFCC offline versus streamed PCM with reflected edge frames");
  Vector<BaseFloat> wave(Signal());
  Matrix<BaseFloat> offline(MfccReference());
  MfccOptions opts;
  opts.frame_opts.dither = 0;
  opts.frame_opts.snip_edges = false;
  OnlineMfcc online(opts);
  for (int32 offset = 0; offset < wave.Dim(); offset += 317) {
    SubVector<BaseFloat> chunk(wave, offset, std::min<int32>(317, wave.Dim() - offset));
    online.AcceptWaveform(16000, chunk);
  }
  online.InputFinished();
  Check(online.NumFramesReady() == offline.NumRows() && offline.NumRows() == 50,
        "MFCC frame count = 50");
  double error = 0;
  Vector<BaseFloat> row(online.Dim());
  for (int32 r = 0; r < offline.NumRows(); ++r) {
    online.GetFrame(r, &row);
    for (int32 c = 0; c < offline.NumCols(); ++c)
      error = std::max(error, std::abs(double(row(c) - offline(r, c))));
  }
  Check(std::isfinite(error) && error < 1.0e-4, "MFCC stream/offline max error < 1e-4");
  Check(online.IsLastFrame(49), "InputFinished exposes final feature frame");

  Begin("filterbank feature dimensions and finite values");
  FbankOptions fbank_opts;
  fbank_opts.frame_opts.dither = 0;
  fbank_opts.mel_opts.num_bins = 40;
  Fbank fbank(fbank_opts);
  Matrix<BaseFloat> banks;
  fbank.ComputeFeatures(wave, 16000, 1.0, &banks);
  Check(banks.NumRows() == 48 && banks.NumCols() == 40, "filterbank shape = 48 x 40");
  bool finite = true;
  for (int32 r = 0; r < banks.NumRows(); ++r)
    for (int32 c = 0; c < banks.NumCols(); ++c) finite = finite && std::isfinite(banks(r, c));
  Check(finite, "filterbank values are finite");

  Begin("independent feature pipelines on two native threads");
  Matrix<BaseFloat> threaded[2];
  std::exception_ptr failures[2];
  auto work = [&](int index) {
    try { threaded[index] = MfccReference(); }
    catch (...) { failures[index] = std::current_exception(); }
  };
  std::thread first(work, 0), second(work, 1);
  first.join(); second.join();
  if (failures[0]) std::rethrow_exception(failures[0]);
  if (failures[1]) std::rethrow_exception(failures[1]);
  Check(threaded[0].ApproxEqual(offline, 1.0e-6) && threaded[1].ApproxEqual(offline, 1.0e-6),
        "two native feature pipelines reproduce the serial result");

  if (!feature_output.empty()) {
    std::ofstream out(feature_output);
    if (!out) throw std::runtime_error("opening feature output: " + feature_output);
    out << std::setprecision(10) << offline.NumRows() << ' ' << offline.NumCols() << '\n';
    for (int32 r = 0; r < offline.NumRows(); ++r) {
      for (int32 c = 0; c < offline.NumCols(); ++c) out << offline(r, c) << ' ';
      out << '\n';
    }
    Check(bool(out), "feature comparison artifact written");
  }
  std::cout << "[METRIC] mfcc_stream_error=" << error << '\n';
}

void FstTests() {
  Begin("weighted FST composition and shortest path");
  fst::StdVectorFst left, right;
  for (int i = 0; i < 3; ++i) { left.AddState(); right.AddState(); }
  left.SetStart(0); right.SetStart(0);
  left.AddArc(0, fst::StdArc(1, 3, 0.25f, 1));
  left.AddArc(1, fst::StdArc(2, 4, 0.5f, 2));
  left.SetFinal(2, 0.75f);
  right.AddArc(0, fst::StdArc(3, 10, 0.75f, 1));
  right.AddArc(1, fst::StdArc(4, 20, 0.5f, 2));
  right.SetFinal(2, 0.75f);
  fst::StdVectorFst composed, best;
  fst::Compose(left, right, &composed);
  fst::ShortestPath(composed, &best);
  std::vector<int32> input, output;
  fst::TropicalWeight weight;
  Check(fst::GetLinearSymbolSequence(best, &input, &output, &weight), "best FST path is linear");
  Check(input == std::vector<int32>({1, 2}) && output == std::vector<int32>({10, 20}),
        "composition maps input labels to expected words");
  Check(std::abs(weight.Value() - 3.5f) < 1.0e-6, "composed tropical cost = 3.5");

  Begin("Vosk lookahead composition and FST binary roundtrip");
  std::vector<int32> disambiguation;
  std::unique_ptr<fst::LookaheadFst<fst::StdArc, int32>> lazy(
      fst::LookaheadComposeFst(left, right, disambiguation));
  fst::StdVectorFst lazy_copy(*lazy);
  Check(fst::Equal(composed, lazy_copy), "lazy Vosk composition preserves weighted arcs");
  std::stringstream stream(std::ios::in | std::ios::out | std::ios::binary);
  Check(composed.Write(stream, fst::FstWriteOptions("memory")), "FST binary serialization");
  std::unique_ptr<fst::StdVectorFst> restored(
      fst::StdVectorFst::Read(stream, fst::FstReadOptions("memory")));
  Check(restored && fst::Equal(composed, *restored), "FST states/arcs/weights survive binary roundtrip");
}

std::unique_ptr<fst::SymbolTable> ReadModelWords(const std::string &path) {
  // Symbols precede the compact ngram payload. Public OpenFST APIs can read
  // these tables independently; no ngram decoder or private layout is used.
  std::ifstream stream(path, std::ios::binary);
  fst::FstHeader header;
  if (!stream || !header.Read(stream, path)) throw std::runtime_error("invalid grammar FST header");
  std::unique_ptr<fst::SymbolTable> input, output;
  if (header.GetFlags() & fst::FstHeader::HAS_ISYMBOLS) input.reset(fst::SymbolTable::Read(stream, path));
  if (header.GetFlags() & fst::FstHeader::HAS_OSYMBOLS) output.reset(fst::SymbolTable::Read(stream, path));
  if (!output) throw std::runtime_error("model grammar has no output symbol table");
  return output;
}

struct DecodeResult {
  std::string text;
  int32 frames;
  double graph_cost;
  double acoustic_cost;
};

DecodeResult Decode(const std::string &model, const std::string &wave_path,
                    int32 chunk_size, bool silence, const std::string &full_grammar) {
  TransitionModel transitions;
  nnet3::AmNnetSimple network;
  bool binary;
  Input model_input(model + "/am/final.mdl", &binary);
  transitions.Read(model_input.Stream(), binary);
  network.Read(model_input.Stream(), binary);
  nnet3::SetBatchnormTestMode(true, &network.GetNnet());
  nnet3::SetDropoutTestMode(true, &network.GetNnet());
  nnet3::CollapseModel(nnet3::CollapseModelConfig(), &network.GetNnet());

  LatticeIncrementalDecoderConfig decoder_config;
  nnet3::NnetSimpleLoopedComputationOptions computation_config;
  OnlineEndpointConfig endpoint_config;
  ParseOptions model_options("native Kaldi model consumer");
  decoder_config.Register(&model_options);
  computation_config.Register(&model_options);
  endpoint_config.Register(&model_options);
  model_options.ReadConfigFile(model + "/conf/model.conf");
  nnet3::DecodableNnetSimpleLoopedInfo computation(computation_config, &network);

  OnlineNnet2FeaturePipelineInfo feature_info;
  feature_info.feature_type = "mfcc";
  ReadConfigFromFile(model + "/conf/mfcc.conf", &feature_info.mfcc_opts);
  feature_info.mfcc_opts.frame_opts.dither = 0;
  OnlineIvectorExtractionConfig ivector;
  ivector.splice_config_rxfilename = model + "/ivector/splice.conf";
  ivector.cmvn_config_rxfilename = model + "/ivector/online_cmvn.conf";
  ivector.lda_mat_rxfilename = model + "/ivector/final.mat";
  ivector.global_cmvn_stats_rxfilename = model + "/ivector/global_cmvn.stats";
  ivector.diag_ubm_rxfilename = model + "/ivector/final.dubm";
  ivector.ivector_extractor_rxfilename = model + "/ivector/final.ie";
  ivector.max_count = 100;
  feature_info.use_ivectors = true;
  feature_info.ivector_extractor_info.Init(ivector);

  std::unique_ptr<fst::SymbolTable> words = ReadModelWords(model + "/graph/Gr.fst");
  // The lookahead FST is provided by the installed core OpenFST headers/library.
  // Read its exact type directly, without optional runtime plugin registration.
  std::unique_ptr<fst::StdOLabelLookAheadFst> hcl(
      fst::StdOLabelLookAheadFst::Read(model + "/graph/HCLr.fst"));
  if (!hcl) throw std::runtime_error("loading original lookahead acoustic graph");
  fst::StdVectorFst digits;
  digits.AddState(); digits.SetStart(0); digits.SetFinal(0, fst::TropicalWeight::One());
  for (const char *token : {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "oh"}) {
    auto label = words->Find(token);
    if (label < 0) throw std::runtime_error(std::string("model vocabulary missing ") + token);
    digits.AddArc(0, fst::StdArc(label, label, 0.0f, 0));
  }
  fst::ArcSort(&digits, fst::ILabelCompare<fst::StdArc>());
  std::unique_ptr<fst::StdFst> grammar;
  if (!full_grammar.empty()) {
#ifdef KALDI_TEST_NGRAM
    if (full_grammar == "original") {
      grammar.reset(fst::NGramFst<fst::StdArc>::Read(model + "/graph/Gr.fst"));
    } else
#endif
    grammar.reset(fst::StdFst::Read(full_grammar));
    if (!grammar) throw std::runtime_error("loading full language graph");
  }
  std::vector<int32> disambiguation;
  if (!ReadIntegerVectorSimple(model + "/graph/disambig_tid.int", &disambiguation))
    throw std::runtime_error("loading graph disambiguation labels");
  std::unique_ptr<fst::LookaheadFst<fst::StdArc, int32>> graph(
      fst::LookaheadComposeFst(*hcl, grammar ? *grammar : digits, disambiguation));
  OnlineNnet2FeaturePipeline features(feature_info);
  SingleUtteranceNnet3IncrementalDecoder decoder(decoder_config, transitions,
                                                computation, *graph, &features);
  Input wave_input(wave_path);
  WaveData wave;
  wave.Read(wave_input.Stream());
  if (wave.SampFreq() != 16000 || wave.Data().NumRows() != 1)
    throw std::runtime_error("fixture must be mono PCM at 16000 Hz");
  Vector<BaseFloat> samples(wave.Data().Row(0));
  if (silence) samples.SetZero();
  for (int32 offset = 0; offset < samples.Dim(); offset += chunk_size) {
    SubVector<BaseFloat> chunk(samples, offset, std::min(chunk_size, samples.Dim() - offset));
    features.AcceptWaveform(16000, chunk);
    decoder.AdvanceDecoding();
  }
  features.InputFinished(); decoder.AdvanceDecoding(); decoder.FinalizeDecoding();
  Lattice best;
  decoder.GetBestPath(true, &best);
  std::vector<int32> alignment, word_ids;
  LatticeWeight cost;
  if (!fst::GetLinearSymbolSequence(best, &alignment, &word_ids, &cost))
    throw std::runtime_error("decoder best path is not linear");
  std::ostringstream transcript;
  for (size_t i = 0; i < word_ids.size(); ++i) {
    if (i) transcript << ' ';
    transcript << words->Find(word_ids[i]);
  }
  // Exercise incremental lattice extraction in addition to best-path output.
  const CompactLattice &lattice = decoder.GetLattice(decoder.NumFramesDecoded(), true);
  if (lattice.NumStates() == 0) throw std::runtime_error("empty final decoder lattice");
  return {transcript.str(), decoder.NumFramesDecoded(), cost.Value1(), cost.Value2()};
}

void DecodeTests(const std::string &model, const std::string &wave,
                 const std::string &full_grammar) {
  // Linux x86_64 baseline from the same pinned model, PCM and decoder settings.
  // The unrestricted model makes two substitutions (i know / one oh); preserve
  // that measured model behavior instead of treating it as a porting defect.
  const std::string expected = full_grammar.empty()
      ? "one zero zero zero one nine oh two one oh zero one eight zero three"
      : "one zero zero zero one nine oh two i know zero one eight zero three";
  Begin("real acoustic model, iVectors, lookahead graph and streaming Nnet3 decode");
  DecodeResult first = Decode(model, wave, 4000, false, full_grammar);
  std::cout << "[TRANSCRIPT] " << first.text << '\n'
            << "[METRIC] frames=" << first.frames << " graph_cost=" << first.graph_cost
            << " acoustic_cost=" << first.acoustic_cost << '\n';
  Check(first.text == expected, "transcription matches the fixed Linux reference for this grammar");
  Check(first.frames == 277, "decoded frame count matches the Linux reference");
  Check(std::isfinite(first.acoustic_cost) && std::isfinite(first.graph_cost), "finite model path costs");
  Check(std::abs(first.acoustic_cost - (full_grammar.empty() ? -912.6262207 : -915.4348755)) < 0.05,
        "acoustic path cost matches Linux within floating-point tolerance");

  Begin("decoder recreation and different PCM chunk boundaries");
  DecodeResult second = Decode(model, wave, 1280, false, full_grammar);
  Check(second.text == first.text && second.frames == first.frames, "stream chunk boundaries preserve transcription");
  Check(std::abs(second.acoustic_cost - first.acoustic_cost) < 2.0,
        "stream chunk boundaries preserve acoustic score within tolerance");

  Begin("silent PCM is not reported as spoken digits");
  DecodeResult quiet = Decode(model, wave, 4000, true, full_grammar);
  Check(quiet.text.empty(), "silence returns empty transcription");
}
}  // namespace

int main(int argc, char **argv) {
  try {
    std::cout << std::setprecision(10);
    if (argc < 2) throw std::runtime_error("usage: test_native_chain numeric [features.txt] | decode MODEL WAV [FULL_GRAMMAR]");
    const std::string mode(argv[1]);
    if (mode == "numeric") {
      NumericalTests<float>("float32");
      NumericalTests<double>("float64");
      FeatureTests(argc > 2 ? argv[2] : "");
      FstTests();
    } else if (mode == "decode" && argc >= 4) {
      DecodeTests(argv[2], argv[3], argc > 4 ? argv[4] : "");
    } else {
      throw std::runtime_error("invalid test mode or missing model/WAV input");
    }
    std::cout << "[PASS] " << cases << " cases; " << assertions << " assertions\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "[FAIL] case=" << cases << " assertion=" << assertions
              << " reason=" << error.what() << '\n';
    return 1;
  }
}

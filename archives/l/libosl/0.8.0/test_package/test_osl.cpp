#include "osl/oslConfig.h"
#include "osl/basic_type.h"
#include "osl/numEffectState.h"
#include "osl/csa.h"

#include <cstdio>
#include <string>

#include <cstring>

namespace {

int check_move_api() {
  using namespace osl;
  // Normal move: 7g-7f pawn push by Black.
  const Move m76fu(Square(7, 7), Square(7, 6), PAWN, PTYPE_EMPTY, false, BLACK);
  if (m76fu.isPass() || !m76fu.isNormal() || m76fu.isInvalid()) {
    std::printf("FAIL move_api: 7g-7f pawn push misclassified\n");
    return 1;
  }
  // Pass move must be a pass, not a normal move.
  const Move pass = Move::PASS(WHITE);
  if (!pass.isPass() || pass.isNormal() || pass.player() != WHITE) {
    std::printf("FAIL move_api: PASS(WHITE) misclassified\n");
    return 1;
  }
  // Capturing the king is an invalid move.
  const Move bug = Move::makeDirect(-58698240);
  if (bug.isValid()) {
    std::printf("FAIL move_api: king capture considered valid\n");
    return 1;
  }
  std::printf("CHECK move_api: PASS\n");
  return 0;
}

int check_initial_state() {
  using namespace osl;
  OslConfig::setUp();
  // Hirate (even) starting position in CSA format.
  NumEffectState state(CsaString(
      "P1-KY-KE-GI-KI-OU-KI-GI-KE-KY\n"
      "P2 * -HI *  *  *  *  * -KA * \n"
      "P3-FU-FU-FU-FU-FU-FU-FU-FU-FU\n"
      "P4 *  *  *  *  *  *  *  *  * \n"
      "P5 *  *  *  *  *  *  *  *  * \n"
      "P6 *  *  *  *  *  *  *  *  * \n"
      "P7+FU+FU+FU+FU+FU+FU+FU+FU+FU\n"
      "P8 * +KA *  *  *  *  * +HI * \n"
      "P9+KY+KE+GI+KI+OU+KI+GI+KE+KY\n"
      "+\n").initialState());
  if (state.turn() != BLACK) {
    std::printf("FAIL initial_state: turn is not BLACK\n");
    return 1;
  }
  if (!state.isConsistent(true)) {
    std::printf("FAIL initial_state: state inconsistent\n");
    return 1;
  }
  // Black king must sit on 5i.
  const Piece black_king = state.pieceAt(Square(5, 9));
  if (black_king.isEmpty() || black_king.ptype() != KING ||
      black_king.owner() != BLACK) {
    std::printf("FAIL initial_state: no BLACK KING on 5i\n");
    return 1;
  }
  std::printf("CHECK initial_state: PASS\n");
  return 0;
}

int check_platform_config() {
  using namespace osl;
  const std::string conf = OslConfig::configuration();
  std::printf("configuration: %s\n", conf.c_str());
#if defined(__aarch64__)
  // On OHOS/aarch64 the x86 SSE path must be off (scalar fallback).
  if (conf.find("nosse") == std::string::npos) {
    std::printf("FAIL platform_config: expected 'nosse' on aarch64\n");
    return 1;
  }
#endif
  std::printf("CHECK platform_config: PASS\n");
  return 0;
}

}  // namespace

// Optional argv filter so ctest can register each CHECK group as its own
// deterministic test case: `test_osl move_api`, `test_osl initial_state`,
// `test_osl platform_config`. No argument runs all groups (local default).
int main(int argc, char** argv) {
  int rc = 0;
  const bool all = (argc < 2);
  bool known = all;
  if (all || std::strcmp(argv[1], "move_api") == 0) {
    rc |= check_move_api();
    known = true;
  }
  if (all || std::strcmp(argv[1], "initial_state") == 0) {
    rc |= check_initial_state();
    known = true;
  }
  if (all || std::strcmp(argv[1], "platform_config") == 0) {
    rc |= check_platform_config();
    known = true;
  }
  if (!known) {
    std::printf("FAIL: unknown check '%s'\n", argv[1]);
    return 2;
  }
  if (rc == 0)
    std::printf("ALL CHECKS PASSED\n");
  return rc;
}

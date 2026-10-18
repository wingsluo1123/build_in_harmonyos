/* Consumer test for the installed Freecell Solver 6.16.0 package.
 *
 * Drives the public solver API end to end on the canonical Microsoft
 * Freecell deal #24 used throughout the upstream manual:
 * allocate -> apply preset -> set game -> solve -> replay every move ->
 * stringify the final state.  Each case prints TEST PASS / TEST FAIL and
 * the program exits non-zero when any case failed.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <freecell-solver/fcs_enums.h>
#include <freecell-solver/fcs_move.h>
#include <freecell-solver/fcs_user.h>

#define EXPECTED_VERSION "6.16.0"

static const char board_24[] = ": 4C 2C 9C 8C QS 4S 2H\n"
                               ": 5H QH 3C AC 3H 4H QD\n"
                               ": QC 9S 6H 9H 3S KS 3D\n"
                               ": 5D 2S JC 5C JH 6D AS\n"
                               ": 2D KD TH TC TD 8D\n"
                               ": 7H JS KH TS KC 7C\n"
                               ": AH 5S 6S AD 8H JD\n"
                               ": 7S 6C 7D 4D 8S 9D\n";

#define SOLVED_FOUNDATIONS "Foundations: H-K C-K D-K S-K"

static int checks_total = 0;
static int checks_failed = 0;

static void check(int condition, const char *name, const char *detail)
{
    checks_total++;
    if (condition)
    {
        printf("TEST PASS: %s\n", name);
    }
    else
    {
        printf("TEST FAIL: %s%s%s\n", name, detail ? " - " : "",
            detail ? detail : "");
        checks_failed++;
    }
}

int main(void)
{
    void *instance = freecell_solver_user_alloc();
    check(instance != NULL, "alloc-instance",
        "freecell_solver_user_alloc returned NULL");
    if (instance == NULL)
    {
        printf("TEST SUMMARY: %d/%d passed (fatal)\n", 0, checks_total);
        return 1;
    }

    const char *version = freecell_solver_user_get_lib_version(instance);
    check(version != NULL && strcmp(version, EXPECTED_VERSION) == 0,
        "lib-version", version ? version : "NULL");

    int preset_rc = freecell_solver_user_apply_preset(instance, "freecell");
    check(preset_rc == FCS_PRESET_CODE_OK, "preset-freecell", "rc != OK");

    int unknown_rc =
        freecell_solver_user_apply_preset(instance, "no-such-preset-6-16-0");
    check(unknown_rc == FCS_PRESET_CODE_NOT_FOUND, "preset-unknown",
        "unknown preset not reported as NOT_FOUND");

    /* 4 freecells, 8 columns, 1 deck, alternate-colour runs, limited
     * sequence moves, empty columns accept any card: standard Freecell. */
    int game_rc = freecell_solver_user_set_game(instance, 4, 8, 1,
        FCS_SEQ_BUILT_BY_ALTERNATE_COLOR, 0, FCS_ES_FILLED_BY_ANY_CARD);
    check(game_rc == 0, "set-game", "freecell parameters rejected");

    int solve_rc = freecell_solver_user_solve_board(instance, board_24);
    check(solve_rc == FCS_STATE_WAS_SOLVED, "solve-board-24",
        "deal #24 did not solve");

    fcs_iters_int iterations =
        freecell_solver_user_get_num_times_long(instance);
    check(iterations > 0, "iterations-positive",
        "solver reported no iterations");

    int moves_left = freecell_solver_user_get_moves_left(instance);
    check(moves_left > 0, "moves-left-positive",
        "empty solution move list");

    fcs_move_t move;
    int move_count = 0;
    int null_moves = 0;
    int first_move_length = -1;
    int end_rc = -1;
    while ((end_rc = freecell_solver_user_get_next_move(instance, &move)) == 0)
    {
        if (fcs_move_get_type(move) == FCS_MOVE_TYPE_NULL)
        {
            null_moves++;
        }
        if (move_count == 0)
        {
            char *rendered = freecell_solver_user_move_to_string(move, 1);
            if (rendered != NULL)
            {
                first_move_length = (int)strlen(rendered);
                free(rendered);
            }
        }
        move_count++;
        if (move_count > 100000)
        {
            break;
        }
    }
    check(move_count > 0 && move_count == moves_left, "replay-move-count",
        "replayed moves differ from get_moves_left");
    check(null_moves == 0, "replay-move-types", "NULL move in solution");
    check(first_move_length > 0, "replay-move-rendering",
        "move_to_string returned an empty string");
    check(end_rc == 1 && move_count <= 100000, "replay-reaches-end",
        "get_next_move did not terminate with 1");

    /* Zero-initialised: stringify writes a NUL-terminated string only when
     * the state is valid, and the buffer is also passed to the check printer
     * as %s.  (The API returns void, so there is no status to check.) */
    char final_state[1024] = {0};
    /* parseable_output=1: "Foundations: H-K C-K D-K S-K" is the canonical
     * solved-state form (the display form aligns the freecells and omits the
     * "Foundations:" prefix). */
    freecell_solver_user_current_state_stringify(
        instance, final_state, 1, 0, 1);
    check(strstr(final_state, SOLVED_FOUNDATIONS) != NULL,
        "solved-foundations", final_state);

    freecell_solver_user_free(instance);

    if (checks_failed == 0)
    {
        printf("TEST SUMMARY: %d/%d passed\n", checks_total, checks_total);
        return 0;
    }
    printf("TEST SUMMARY: %d/%d passed (%d failed)\n",
        checks_total - checks_failed, checks_total, checks_failed);
    return 1;
}

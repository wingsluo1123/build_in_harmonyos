#include <errno.h>
#include <stdio.h>
#include <sys/types.h>

enum scenario {
    FAIL_FIRST_PIPE,
    FAIL_SECOND_PIPE,
    FAIL_FORK,
    PARENT_SUCCESS
};

static enum scenario active_scenario;
static int pipe_calls;
static int fork_calls;
static int close_calls;
static int closed_fds[8];

static int cvm_test_pipe(int descriptors[2]);
static pid_t cvm_test_fork(void);
static int cvm_test_close(int descriptor);

#define pipe cvm_test_pipe
#define fork cvm_test_fork
#define close cvm_test_close
#include "../client_xfer_command.c"
#undef close
#undef fork
#undef pipe

static void reset(enum scenario scenario)
{
    int index;

    active_scenario = scenario;
    pipe_calls = 0;
    fork_calls = 0;
    close_calls = 0;
    for (index = 0; index < 8; ++index) closed_fds[index] = -1;
}

static int cvm_test_pipe(int descriptors[2])
{
    ++pipe_calls;
    if ((active_scenario == FAIL_FIRST_PIPE && pipe_calls == 1) ||
        (active_scenario == FAIL_SECOND_PIPE && pipe_calls == 2)) {
        errno = EMFILE;
        return -1;
    }
    descriptors[0] = pipe_calls == 1 ? 10 : 20;
    descriptors[1] = descriptors[0] + 1;
    return 0;
}

static pid_t cvm_test_fork(void)
{
    ++fork_calls;
    if (active_scenario == FAIL_FORK) {
        errno = EAGAIN;
        return -1;
    }
    return 1234;
}

static int cvm_test_close(int descriptor)
{
    if (close_calls < (int)(sizeof(closed_fds) / sizeof(closed_fds[0])))
        closed_fds[close_calls] = descriptor;
    ++close_calls;
    return 0;
}

static int expect_counts(const char* name, int pipes, int forks, int closes)
{
    if (pipe_calls != pipes || fork_calls != forks || close_calls != closes) {
        fprintf(stderr,
                "%s: calls pipe=%d/%d fork=%d/%d close=%d/%d\n",
                name, pipe_calls, pipes, fork_calls, forks,
                close_calls, closes);
        return 0;
    }
    return 1;
}

static int expect_closes(const char* name, const int* expected, int count)
{
    int index;

    for (index = 0; index < count; ++index) {
        if (closed_fds[index] != expected[index]) {
            fprintf(stderr, "%s: close[%d]=%d, expected %d\n",
                    name, index, closed_fds[index], expected[index]);
            return 0;
        }
    }
    return 1;
}

int main(void)
{
    int outputs[2] = {-1, -1};
    int result;
    const int second_failure_closes[] = {10, 11};
    const int fork_failure_closes[] = {20, 21, 10, 11};
    const int parent_closes[] = {10, 21};

    reset(FAIL_FIRST_PIPE);
    result = pipefork("unused", outputs);
    if (result != 0) {
        fputs("first pipe failure was accepted\n", stderr);
        return 1;
    }
    if (!expect_counts("first pipe failure", 1, 0, 0))
        return 1;

    reset(FAIL_SECOND_PIPE);
    result = pipefork("unused", outputs);
    if (result != 0) {
        fputs("second pipe failure crossed the fork side-effect barrier\n", stderr);
        return 2;
    }
    if (!expect_counts("second pipe failure", 2, 0, 2) ||
        !expect_closes("second pipe failure", second_failure_closes, 2))
        return 2;

    reset(FAIL_FORK);
    result = pipefork("unused", outputs);
    if (result != 0) {
        fputs("fork failure was accepted\n", stderr);
        return 3;
    }
    if (!expect_counts("fork failure", 2, 1, 4) ||
        !expect_closes("fork failure", fork_failure_closes, 4))
        return 3;

    reset(PARENT_SUCCESS);
    outputs[0] = outputs[1] = -1;
    result = pipefork("unused", outputs);
    if (result != 1 || !expect_counts("parent success", 2, 1, 2) ||
        !expect_closes("parent success", parent_closes, 2) ||
        outputs[0] != 11 || outputs[1] != 20) {
        fprintf(stderr, "parent success: returned descriptors %d,%d\n",
                outputs[0], outputs[1]);
        return 4;
    }

    puts("four-stage pipe/fork acquisition matrix is failure-atomic");
    return 0;
}

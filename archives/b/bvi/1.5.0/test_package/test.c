#include <unistd.h>

/* bvi is a terminal editor (ncurses); --version requires a PTY.
 * Smoke test: verify the binary exists and is executable.
 * Usage: ./test_bvi /path/to/bvi */
int main(int argc, char *argv[])
{
    if (argc < 2)
        return 1;
    return access(argv[1], X_OK) == 0 ? 0 : 1;
}

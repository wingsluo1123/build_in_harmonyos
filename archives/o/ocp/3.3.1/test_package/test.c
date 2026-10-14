/* HarmonyOS PC consumer test for the ocp application package.
 *
 * ocp is a front end, not a library, so a test that only prints something would
 * prove nothing.  This test really executes the delivered binary: the dynamic
 * loader has to resolve every shared library the player links and main() has to
 * run.  Started with an isolated, writable HOME the player reports its absent
 * per-user configuration through its own diagnostics ("Global ocp.ini not
 * found") - a missing dependency, a broken relocation or a failed loader never
 * gets that far, so the message is the evidence that the artifact works.
 *
 * When the build host cannot execute the target binary (cross compilation on a
 * foreign machine) the artifact is verified as an AArch64 ELF instead, so the
 * test stays meaningful rather than failing for an environment reason.
 */
#define _GNU_SOURCE

#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

/* exit codes reported by the child when execv() itself failed */
#define EXEC_FORMAT_ERROR 126
#define EXEC_OTHER_ERROR 127

#define EM_AARCH64 183

static int verify_aarch64_elf(const char *path)
{
	unsigned char header[20];
	FILE *fp = fopen(path, "rb");
	size_t got;
	unsigned int machine;

	if (fp == NULL) {
		fprintf(stderr, "FAIL: cannot read %s\n", path);
		return 1;
	}
	got = fread(header, 1, sizeof header, fp);
	fclose(fp);

	if (got < sizeof header || memcmp(header, "\177ELF", 4) != 0) {
		fprintf(stderr, "FAIL: %s is not an ELF file\n", path);
		return 1;
	}
	if (header[4] != 2) {
		fprintf(stderr, "FAIL: %s is not a 64 bit ELF\n", path);
		return 1;
	}
	/* e_machine is a 16 bit little endian field at offset 18 */
	machine = (unsigned int)header[18] | ((unsigned int)header[19] << 8);
	if (machine != EM_AARCH64) {
		fprintf(stderr, "FAIL: %s: unexpected e_machine %u\n", path, machine);
		return 1;
	}
	printf("SKIP: %s is a valid aarch64 ELF, this build host cannot execute it\n",
	       path);
	return 0;
}

int main(int argc, char **argv)
{
	const char *binary = (argc > 1) ? argv[1] : "ocp";
	char cwd[4096];
	char scratch[4096];
	char output[4096];
	char *const exec_args[] = {(char *)binary, (char *)"--version", NULL};
	int fds[2];
	int status = 0;
	int waited = 0;
	int eof = 0;
	size_t used = 0;
	ssize_t got;
	pid_t pid;

	printf("running %s --version\n", binary);
	fflush(stdout);

	/* HarmonyOS mounts /tmp read-only, so the scratch directory is created
	   next to the test binary (the current directory is writable).  HOME has
	   to be absolute, otherwise the player ignores the value. */
	if (getcwd(cwd, sizeof cwd) == NULL) {
		perror("getcwd");
		return 1;
	}
	if (snprintf(scratch, sizeof scratch, "%s/ocp-test-home-XXXXXX", cwd) >=
	    (int)sizeof scratch) {
		fprintf(stderr, "FAIL: the working directory path is too long\n");
		return 1;
	}
	if (mkdtemp(scratch) == NULL) {
		perror("mkdtemp");
		return 1;
	}
	if (pipe(fds) != 0) {
		perror("pipe");
		return 1;
	}
	pid = fork();
	if (pid < 0) {
		perror("fork");
		return 1;
	}
	if (pid == 0) {
		dup2(fds[1], STDOUT_FILENO);
		dup2(fds[1], STDERR_FILENO);
		close(fds[0]);
		close(fds[1]);
		setenv("HOME", scratch, 1);
		setenv("TMPDIR", scratch, 1);
		execv(binary, exec_args);
		_exit(errno == ENOEXEC ? EXEC_FORMAT_ERROR : EXEC_OTHER_ERROR);
	}
	close(fds[1]);

	/* Drain the child's diagnostics with poll(): the test must not hang on a
	   long running player, and it must not close the pipe while the child is
	   still writing (that would signal the child). */
	while (used < sizeof output - 1) {
		struct pollfd pfd = {fds[0], POLLIN, 0};

		if (poll(&pfd, 1, 1000) == 0) {
			if (++waited >= 30) {
				break;
			}
			continue;
		}
		got = read(fds[0], output + used, sizeof output - 1 - used);
		if (got <= 0) {
			eof = 1;
			break;
		}
		used += (size_t)got;
	}
	close(fds[0]);
	output[used] = '\0';

	if (eof == 0) {
		/* still running after the grace period: stop it, do not wait forever */
		kill(pid, SIGKILL);
	}
	if (waitpid(pid, &status, 0) < 0) {
		perror("waitpid");
		return 1;
	}

	printf("exit status: %d\n%s", WIFEXITED(status) ? WEXITSTATUS(status) : -1,
	       output);

	/* The player wrote its configuration diagnostics, so it started, the
	   loader resolved every shared library and main() ran.  The verdict is
	   taken from that output first: the parent stops reading as soon as the
	   pipe is drained, which can signal the (still chatting) child later on. */
	if (strstr(output, "ocp.ini") != NULL) {
		printf("PASS: the front end started and reported its configuration state\n");
		return 0;
	}
	if (WIFSIGNALED(status)) {
		fprintf(stderr, "FAIL: %s was killed by signal %d\n", binary,
			WTERMSIG(status));
		return 1;
	}
	if (WIFEXITED(status) && WEXITSTATUS(status) == EXEC_FORMAT_ERROR) {
		return verify_aarch64_elf(binary);
	}
	fprintf(stderr, "FAIL: %s did not start (exit status %d)\n", binary,
		WIFEXITED(status) ? WEXITSTATUS(status) : -1);
	return 1;
}

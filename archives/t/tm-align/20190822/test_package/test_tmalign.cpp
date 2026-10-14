// Consumer test for the packaged tm-align tools (TMalign / TMscore).
//
// Flow: build synthetic protein C-alpha traces (PDB files) -> run the packaged
// TMalign / TMscore binaries on them -> check the numeric results against the
// geometry we constructed:
//   a.pdb : ideal alpha helix, 60 residues
//   b.pdb : a.pdb rotated 40 deg about Y and translated by (10, -5, 3)
//   c.pdb : extended beta-strand-like trace, 60 residues
// TM-align must find the exact rigid transform a->b (TM-score 1, RMSD 0 and the
// recovered rotation/translation), and must score helix-vs-strand low.
//
// usage: test_tmalign <path-to-TMalign> <path-to-TMscore>
#include <sys/wait.h>
#include <unistd.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static int g_fail = 0;
#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (!(cond)) {                                                     \
            std::cerr << "FAIL: " << msg << " (" #cond ")" << std::endl;   \
            ++g_fail;                                                      \
        } else {                                                           \
            std::cout << "ok:   " << msg << std::endl;                     \
        }                                                                  \
    } while (0)

struct P3 { double x, y, z; };

static void write_pdb(const std::string &fn, const std::vector<P3> &ca) {
    static const char *res[4] = {"ALA", "LEU", "GLU", "LYS"};
    std::FILE *f = std::fopen(fn.c_str(), "w");
    if (!f) { std::perror(fn.c_str()); std::exit(2); }
    for (size_t i = 0; i < ca.size(); ++i)
        std::fprintf(f, "ATOM  %5zu  CA  %3s A%4zu    %8.3f%8.3f%8.3f  1.00  0.00           C\n",
                     i + 1, res[i % 4], i + 1, ca[i].x, ca[i].y, ca[i].z);
    std::fputs("TER\nEND\n", f);
    std::fclose(f);
}

// fork/exec (no shell: OHOS PC may not provide a usable /bin/sh), capture stdout+stderr.
// TM_TEST_RUNNER (optional, e.g. "qemu-aarch64") prefixes the command on hosts that cannot exec the binary directly.
static int run(std::vector<std::string> argv, std::string &out) {
    if (const char *runner = std::getenv("TM_TEST_RUNNER")) argv.insert(argv.begin(), runner);
    int fd[2];
    if (pipe(fd) != 0) return -1;
    pid_t pid = fork();
    if (pid < 0) return -1;
    if (pid == 0) {
        dup2(fd[1], 1);
        dup2(fd[1], 2);
        close(fd[0]);
        close(fd[1]);
        std::vector<char *> av;
        for (const auto &a : argv) av.push_back(const_cast<char *>(a.c_str()));
        av.push_back(nullptr);
        execvp(av[0], av.data());
        _exit(127);
    }
    close(fd[1]);
    char buf[4096];
    ssize_t n;
    while ((n = read(fd[0], buf, sizeof buf)) > 0) out.append(buf, (size_t)n);
    close(fd[0]);
    int st = 0;
    waitpid(pid, &st, 0);
    return WIFEXITED(st) ? WEXITSTATUS(st) : -1;
}

// first number following `key` in text, NaN if absent
static double num_after(const std::string &text, const std::string &key, size_t from = 0, size_t *end = nullptr) {
    size_t p = text.find(key, from);
    if (p == std::string::npos) return NAN;
    p += key.size();
    char *e = nullptr;
    double v = std::strtod(text.c_str() + p, &e);
    if (end) *end = (size_t)(e - text.c_str());
    return v;
}

int main(int argc, char **argv) {
    if (argc < 3) { std::cerr << "usage: test_tmalign TMalign TMscore\n"; return 2; }
    const std::string tmalign = argv[1], tmscore = argv[2];
    const int N = 60;
    const double PI = std::acos(-1.0);

    std::vector<P3> A, B, C;
    const double th = 40.0 * PI / 180.0, ct = std::cos(th), st = std::sin(th);
    for (int i = 0; i < N; ++i) {
        double a = 100.0 * i * PI / 180.0;
        P3 p{2.3 * std::cos(a), 2.3 * std::sin(a), 1.5 * i};
        A.push_back(p);
        B.push_back({ct * p.x - st * p.z + 10.0, p.y - 5.0, st * p.x + ct * p.z + 3.0});
        C.push_back({1.0 * (i % 2), 0.0, 3.3 * i});
    }
    write_pdb("a.pdb", A);
    write_pdb("b.pdb", B);
    write_pdb("c.pdb", C);

    std::string out;

    // 1. TMalign -v: version banner
    out.clear();
    run({tmalign, "-v"}, out);
    CHECK(out.find("Version 20190822") != std::string::npos, "TMalign -v reports Version 20190822");

    // 2. TMalign on a rigid-body copy: perfect structural match
    out.clear();
    int rc = run({tmalign, "a.pdb", "b.pdb", "-m", "matrix.txt"}, out);
    CHECK(rc == 0, "TMalign a.pdb b.pdb exits 0");
    CHECK(out.find("Length of Chain_1: 60 residues") != std::string::npos, "TMalign parsed 60 residues from the PDB file");
    CHECK(num_after(out, "Aligned length=") == 60.0, "TMalign aligned all 60 residues");
    CHECK(num_after(out, "RMSD=") < 0.01, "TMalign RMSD of rigid-body copy ~ 0");
    size_t e1 = 0;
    double tm1 = num_after(out, "TM-score=", 0, &e1);
    double tm2 = num_after(out, "TM-score=", e1);
    CHECK(tm1 > 0.999 && tm2 > 0.999, "TMalign TM-score ~ 1 for both normalisations");

    // 3. rotation matrix written with -m must recover the constructed transform
    {
        std::ifstream mf("matrix.txt");
        std::stringstream ss;
        ss << mf.rdbuf();
        std::string m = ss.str();
        CHECK(!m.empty(), "TMalign -m wrote matrix.txt");
        // rows: "<i> t u1 u2 u3" after the header line starting with 'm'
        size_t hp = m.find("u[m][2]");
        double r[3][4] = {};
        bool parsed = hp != std::string::npos;
        if (parsed) {
            std::istringstream is(m.substr(hp + 7));
            for (int i = 0; i < 3 && parsed; ++i) {
                int idx;
                parsed = (bool)(is >> idx >> r[i][0] >> r[i][1] >> r[i][2] >> r[i][3]);
            }
        }
        CHECK(parsed, "matrix.txt rows parsed");
        CHECK(parsed && std::fabs(r[0][0] - 10.0) < 0.01 && std::fabs(r[1][0] + 5.0) < 0.01 && std::fabs(r[2][0] - 3.0) < 0.01,
              "recovered translation (10,-5,3)");
        CHECK(parsed && std::fabs(r[0][1] - ct) < 1e-3 && std::fabs(r[0][3] + st) < 1e-3 &&
                  std::fabs(r[2][1] - st) < 1e-3 && std::fabs(r[1][2] - 1.0) < 1e-3,
              "recovered 40 degree rotation about Y");
    }

    // 4. helix vs strand: clearly different folds
    out.clear();
    run({tmalign, "a.pdb", "c.pdb"}, out);
    double tmc = num_after(out, "TM-score=");
    CHECK(!std::isnan(tmc) && tmc < 0.5, "TMalign helix vs strand TM-score < 0.5");

    // 5. -fast mode and user-length normalisation reach the same answer on a perfect match
    out.clear();
    run({tmalign, "a.pdb", "b.pdb", "-fast", "-u", "60"}, out);
    CHECK(num_after(out, "TM-score=") > 0.999, "TMalign -fast -u 60 TM-score ~ 1");

    // 6. TMscore (fixed residue correspondence) on the same pair
    out.clear();
    rc = run({tmscore, "a.pdb", "b.pdb"}, out);
    CHECK(rc == 0, "TMscore a.pdb b.pdb exits 0");
    CHECK(num_after(out, "Number of residues in common=") == 60.0, "TMscore matched 60 common residues");
    CHECK(num_after(out, "TM-score    =") > 0.999, "TMscore TM-score ~ 1");
    CHECK(num_after(out, "GDT-HA-score=") > 0.999, "TMscore GDT-HA ~ 1");

    // 7. TMscore must penalise the mismatching pair
    out.clear();
    run({tmscore, "a.pdb", "c.pdb"}, out);
    double s = num_after(out, "TM-score    =");
    CHECK(!std::isnan(s) && s < 0.5, "TMscore helix vs strand TM-score < 0.5");

    std::cout << (g_fail ? "TM-align consumer test FAILED" : "TM-align consumer test PASSED") << std::endl;
    return g_fail ? 1 : 0;
}

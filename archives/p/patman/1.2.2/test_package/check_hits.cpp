// 消费者程序：解析 patman 输出的制表符分隔命中表（库名、模式名、起、止、链、编辑距离），
// 与期望表逐行比对（顺序无关）。任何格式错误或差异都以非零退出码失败。
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct Hit {
    std::string db, pat, strand;
    long first, last;
    int dist;
    bool operator<(const Hit &o) const {
        if (db != o.db) return db < o.db;
        if (pat != o.pat) return pat < o.pat;
        if (first != o.first) return first < o.first;
        if (last != o.last) return last < o.last;
        if (strand != o.strand) return strand < o.strand;
        return dist < o.dist;
    }
    bool operator==(const Hit &o) const {
        return db == o.db && pat == o.pat && strand == o.strand &&
               first == o.first && last == o.last && dist == o.dist;
    }
};

static bool load(const char *path, std::vector<Hit> &out) {
    std::ifstream in(path);
    if (!in) { std::cerr << "cannot open " << path << "\n"; return false; }
    std::string line;
    while (std::getline(in, line)) {
        std::vector<std::string> f;
        std::stringstream ss(line);
        std::string cell;
        while (std::getline(ss, cell, '\t')) f.push_back(cell);
        if (f.size() != 6 || (f[4] != "+" && f[4] != "-")) {
            std::cerr << path << ": malformed line: " << line << "\n";
            return false;
        }
        Hit h{f[0], f[1], f[4], std::atol(f[2].c_str()), std::atol(f[3].c_str()),
              std::atoi(f[5].c_str())};
        if (h.first < 1 || h.last < h.first) {
            std::cerr << path << ": bad coordinates: " << line << "\n";
            return false;
        }
        out.push_back(h);
    }
    std::sort(out.begin(), out.end());
    return true;
}

int main(int argc, char **argv) {
    if (argc != 3) { std::cerr << "usage: check_hits <actual.tsv> <expected.tsv>\n"; return 2; }
    std::vector<Hit> actual, expected;
    if (!load(argv[1], actual) || !load(argv[2], expected)) return 2;
    if (actual.size() != expected.size() || !std::equal(actual.begin(), actual.end(), expected.begin())) {
        std::cerr << "MISMATCH: got " << actual.size() << " hits, expected " << expected.size() << "\n";
        return 1;
    }
    std::cout << "OK: " << actual.size() << " hits match " << argv[2] << "\n";
    return 0;
}

# jira-cli 1.7.0 Build Notes

## Build Info
- **Software**: jira-cli (github.com/ankitpokhrel/jira-cli)
- **Version**: 1.7.0
- **Build System**: Go (CGO_ENABLED=0, GOOS=linux, GOARCH=arm64)
- **Go Version**: go1.26.4
- **Go Binary**: /storage/Users/currentUser/.harmonybrew/Cellar/go/1.26.4_4/libexec/bin/go
- **Build Date**: 2026-07-06
- **GOPROXY**: https://goproxy.cn

## Build Process
1. Source extracted from jira-cli-1.7.0.tar.gz at $BUILD_SRC_DIR
2. Go environment set up with harmonybrew go1.26.4 (see Key Issues below)
3. `go mod download` — dependencies downloaded successfully via goproxy.cn
4. `go build -ldflags="..." -o jira ./cmd/jira` — compiled with version ldflags:
   - Version=v1.7.0, GitCommit=release, SourceDateEpoch=0, -s -w (stripped)
5. Binary verified as ELF64 arm64 static executable via `file` and `readelf`
6. Version check passed: (Version="v1.7.0", GoVersion="go1.26.4", Platform="linux/arm64")
7. Binary installed to $TEST_PREFIX and $DEFAULT_PREFIX
8. Precompiled package created: jira-cli-1.7.0-ohos-aarch64.tar.gz

## Binary Info
- **Format**: ELF executable, 64-bit LSB arm64, static, stripped
- **Size**: 19285056 bytes (~18.4 MB)
- **SHA256**: 852d4ae1164988a07563e071e3d4aad8232de6ea0c2fc04a890b9cc6c38302c9
- **Security**: NX stack enabled (GNU_STACK RW), not PIE (Go default EXEC type)
- **Dynamic deps**: None (static binary)

## Key Issues & Solutions

### Issue 1: Go binary execution permission denied
- **Problem**: The go binary at `/storage/Users/currentUser/usr/local/bin/go` (13564865 bytes,
  dated 2026-06-30) could not be executed — "permission denied" (exit code 126).
  The HarmonyOS MAC (hmmac=use_task on tmpfs) blocks execution of unsigned static ELF binaries.
- **Root cause**: The go binary was not signed/authorized by the HarmonyOS security framework.
  The SELinux context is `u:r:hishell_hap:s0` which restricts execution of unsigned static binaries.
- **Solution**: Used the harmonybrew-installed go binary at
  `/storage/Users/currentUser/.harmonybrew/Cellar/go/1.26.4_4/libexec/bin/go`
  (13026368 bytes, dated 2026-07-02) which is properly signed and executable.
  Go version confirmed: go1.26.4 linux/arm64.
- **Note**: The `/storage/Users/currentUser/usr/local/go/VERSION` file says "go1.24.0" but
  the harmonybrew Cellar path indicates go1.26.4. The harmonybrew binary was used.

### Issue 2: Conan/conanfile not applicable for Go projects
- **Problem**: The SKILL.md framework is primarily designed for C/C++ projects using
  configure/make/autotools and Conan package management. jira-cli is a pure Go project.
- **Solution**: Used `go build` directly instead of configure/make. No conanfile.py
  generated (Go modules handle dependency management natively). Precompiled package
  created manually as tar.gz instead of using `conan create`.

## Quality Gate Results
- **G0 (Pre-build risk)**: N/A (Go project, no knowledge graph entry for Go build issues)
- **G1 (Recipe completeness)**: N/A (Go project, no conanfile.py needed)
- **G2 (conan create)**: Skipped (Go project, uses go modules not conan)
- **G3 (System lib isolation)**: N/A (static binary, no shared libs)
- **G4 (Artifact completeness)**: PASS — binary exists, ELF64 arm64 static, runs correctly
- **L2 (Smoke test)**: PASS — `jira version` outputs correct version info
- **L4 (Security scan)**: PASS — NX stack enabled, no dynamic deps to check
- **L5 (Baseline)**: PASS — SHA256 recorded for future comparison

## Precompiled Package
- **Path**: archives/j/jira-cli/1.7.0/packaging/jira-cli-1.7.0-ohos-aarch64.tar.gz
- **Size**: 19290003 bytes
- **Contents**: storage/Users/currentUser/usr/local/bin/jira

---

**编译结束**: 2026-07-06 11:15
**最终状态**: built

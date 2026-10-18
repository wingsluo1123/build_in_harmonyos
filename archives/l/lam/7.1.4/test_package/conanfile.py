import os
import shutil
import socket
import tempfile
from shlex import quote

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep(self):
        return self.dependencies["lam"]

    def _path(self, name):
        for bindir in self._dep().cpp_info.bindirs:
            candidate = os.path.join(bindir, name)
            if os.path.exists(candidate):
                return candidate
        found = shutil.which(name)
        if found:
            return found
        raise Exception(f"{name} not found in lam package")

    def _session_dir(self):
        # lamd creates its unix domain socket (lam-kernel-socket) under the
        # session directory.  On filesystems like HMDFS (where the CI conan
        # cache lives) bind(2) for AF_UNIX fails with EPERM ("lamd kernel:
        # problem with bind ...: Operation not permitted").  LAM resolves
        # the session dir as: explicit -b flag > $LAM_MPI_SESSION_PREFIX >
        # $TMPDIR > /tmp (share/etc/kill.c::lam_tmpdir_init_opt).  Probe
        # candidate dirs with a real socket bind and point the prefix at
        # the first one that works, so the test never depends on where the
        # conan cache happens to live.
        candidates = [
            os.environ.get("TMPDIR", ""),
            "/data/storage/el2/base/cache",
            tempfile.gettempdir(),
            os.getcwd(),
        ]
        for cand in candidates:
            if not cand:
                continue
            probe = os.path.join(cand, f"lam-probe-{os.getpid()}.sock")
            try:
                os.makedirs(cand, exist_ok=True)
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    s.bind(probe)
                finally:
                    s.close()
                os.unlink(probe)
                return cand
            except OSError:
                continue
        return None

    def _sdk_lib_dirs(self):
        # LAM's C++ tools (laminfo, mpic++, lamd) link libc++_shared.so from
        # the OHOS NDK.  Locate it relative to the active clang++ instead of
        # hardcoding any sandbox-specific absolute path.
        cxx = shutil.which("clang++") or "clang++"
        try:
            printed = os.popen(f"{quote(cxx)} -print-file-name=libc++_shared.so").read().strip()
        except Exception:
            return []
        if printed and os.sep in printed and os.path.isfile(printed):
            return [os.path.dirname(printed)]
        return []

    def build(self):
        dep = self._dep().cpp_info
        cc = os.environ.get("CC") or shutil.which("clang") or "clang"
        incs = " ".join(f"-I{p}" for p in dep.includedirs)
        libdirs = " ".join(f"-L{p}" for p in dep.libdirs)
        # LAM's hcc/mpicc/mpic++ wrapper binaries silently fail to spawn the
        # compiler on OHOS, so the consumer compiles with the underlying
        # compiler plus the exact flags the wrappers expose via --showme.
        self.run(f'"{cc}" {incs} test.c -o test_mpi {libdirs} -llammpi++ -lmpi -llam -ldl')

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link smoke only")
            return

        laminfo = self._path("laminfo")
        lamboot = self._path("lamboot")
        mpirun = self._path("mpirun")
        lamhalt = self._path("lamhalt")

        sdk_dirs = ":".join(self._sdk_lib_dirs())
        ld_path = f"{sdk_dirs}:$LD_LIBRARY_PATH" if sdk_dirs else "$LD_LIBRARY_PATH"
        # DESTDIR install with --prefix=/ leaves $SYSCONFDIR=/etc, which has
        # no lam-bhost.def.  lamboot searches the local directory first, so
        # materialize the upstream single-node default hostfile (etc/
        # lam-bhost.def: "localhost") in the run directory.
        with open("lam-bhost.def", "w") as f:
            f.write("localhost\n")
        session = self._session_dir()
        if session is None:
            raise Exception(
                "no directory supports AF_UNIX socket bind (needed by lamd); "
                "tried TMPDIR, /data/storage/el2/base/cache, system temp, cwd"
            )
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        command = (
            f'export LD_LIBRARY_PATH="{ld_path}"; '
            f'export LAM_MPI_SESSION_PREFIX="{session}"; '
            # Redirect to a file instead of piping through tee: the local
            # cache filesystem intermittently denies writes to pipe fds.
            f'"{laminfo}" > laminfo.out 2>&1 && '
            f'grep -q "LAM/MPI" laminfo.out && '
            f'grep -q "linux-ohos" laminfo.out && '
            f'timeout 60 "{lamboot}" -v && '
            f'timeout 120 "{mpirun}" -np 1 ./test_mpi && '
            f'timeout 120 "{mpirun}" -np 2 ./test_mpi && '
            f'timeout 60 "{lamhalt}" && '
            f'echo LAM-TEST-PACKAGE-PASSED'
        )
        self.run(f"{quote(bash)} -c {quote(command)}", env="conanrun")

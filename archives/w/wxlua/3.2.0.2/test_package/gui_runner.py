"""Run real wxLua tests against a private GTK Broadway display."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time


def run_gui(command, broadway, env, workdir, marker, executor=None):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    runtime = workdir / ("runtime-" + str(os.getpid()))
    runtime.mkdir(exist_ok=True)
    child_env = dict(env)
    child_env["GDK_BACKEND"] = "broadway"
    child_env["XDG_RUNTIME_DIR"] = str(runtime)
    # The private runtime directory isolates the display socket from other jobs.
    child_env["BROADWAY_DISPLAY"] = ":1"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = runtime / "fonts.conf"
    config.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/system/fonts</dir><cachedir>' + str(runtime / "fonts-cache") + '</cachedir></fontconfig>')
    child_env["FONTCONFIG_FILE"] = str(config)
    with (workdir / "broadway.log").open("w") as log:
        server = subprocess.Popen([str(broadway), "-a", "127.0.0.1", "-p", str(port), ":1"], env=child_env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(50):
                if server.poll() is not None:
                    raise RuntimeError("Broadway failed: " + (workdir / "broadway.log").read_text())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Broadway did not become ready")
            if executor:
                output = executor(command, child_env)
                result = subprocess.CompletedProcess(command, 0, output)
            else:
                result = subprocess.run([str(x) for x in command], env=child_env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
            (workdir / "test-output.log").write_text(result.stdout)
            print(result.stdout, flush=True)
            if result.returncode or marker not in result.stdout:
                raise RuntimeError(f"wxLua test failed: exit={result.returncode}, required marker={marker}")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            shutil.rmtree(runtime)


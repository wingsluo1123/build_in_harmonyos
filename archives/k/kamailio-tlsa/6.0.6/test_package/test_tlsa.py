#!/usr/bin/env python3
"""Real-core consumer tests for the installed TLSA module; no core API stubs."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import socket
import ssl
import subprocess
import time


def request(port, certificate, version, sequence):
    context = ssl.create_default_context(cafile=str(certificate))
    context.minimum_version = context.maximum_version = version
    with context.wrap_socket(socket.create_connection(("127.0.0.1", port), timeout=5),
                             server_hostname="localhost") as connection:
        message = (
            "OPTIONS sip:localhost SIP/2.0\r\n"
            f"Via: SIP/2.0/TLS 127.0.0.1:{connection.getsockname()[1]};"
            f"branch=z9hG4bKtlsa{sequence};rport\r\n"
            f"From: <sip:alice@localhost>;tag=tlsa{sequence}\r\n"
            "To: <sip:localhost>\r\n"
            f"Call-ID: tlsa-{sequence}@localhost\r\n"
            "CSeq: 1 OPTIONS\r\nMax-Forwards: 70\r\nContent-Length: 0\r\n\r\n"
        )
        connection.sendall(message.encode())
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = connection.recv(8192)
            if not chunk:
                raise AssertionError("TLS connection closed before the SIP response")
            response.extend(chunk)
            if len(response) > 65536:
                raise AssertionError("SIP response exceeded the test limit")
        assert response.startswith(b"SIP/2.0 200 "), repr(response)
        return {"tls": connection.version(), "status": response.split(b"\r\n")[0].decode()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--arch", required=True)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    package, build = args.package.resolve(), args.build.resolve()
    runtime = build / "runtime"
    runtime.mkdir(exist_ok=True)
    results = []

    def check(name, passed, actual=None):
        item = {"name": name, "pass": bool(passed)}
        if actual is not None:
            item["actual"] = actual
        results.append(item)
        print(json.dumps(item), flush=True)

    module = package / "lib/kamailio/modules/tlsa.so"
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if not readelf:
        raise RuntimeError("llvm-readelf or readelf is required for the ELF checks")
    elf = subprocess.check_output([readelf, "-h", "-d", "--dyn-syms", str(module)], text=True)
    (runtime / "module-elf.txt").write_text(elf)
    check("ELF shared module", "DYN" in elf)
    check("target architecture", ("AArch64" if args.arch == "armv8" else "X86-64") in elf)
    check("embedded OpenSSL has no dynamic SSL dependency",
          not re.search(r"NEEDED.*lib(?:ssl|crypto)", elf))
    defined = [line for line in elf.splitlines() if re.search(r"\bGLOBAL\b", line)
               and not re.search(r"\bUND\b", line)]
    check("OpenSSL API symbols stay local", not any(re.search(
        r"\b(?:SSL_CTX_new|SSL_new|CRYPTO_malloc|OPENSSL_init_crypto)\b", line) for line in defined))
    check("Kamailio ABI exports remain visible", all(any(re.search(r"\b" + name + r"$", line)
          for line in defined) for name in ("exports", "mod_register", "module_version", "module_flags")))
    check("no embedded runtime search paths", not re.search(r"\((?:RPATH|RUNPATH)\)", elf))
    check("license and configuration installed", (package / "licenses/COPYING").is_file()
          and (package / "lib/kamailio/modules/tls.cfg").is_file())
    subprocess.run([str(build / "make_certificate"), str(runtime / "key.pem"),
                    str(runtime / "cert.pem")], check=True, timeout=30)
    source = build / "host-source/src"
    for mode in ("normal", "foreign-ssl-first", "high-keys"):
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        (runtime / "tls.cfg").write_text(
            "[server:default]\nmethod=TLSv1.2+\nverify_certificate=no\n"
            f"require_certificate=no\nprivate_key={runtime}/key.pem\ncertificate={runtime}/cert.pem\n")
        config = runtime / "kamailio.cfg"
        config.write_text(
            "debug=2\nlog_stderror=yes\nfork=yes\nchildren=2\ntcp_children=2\n"
            f'enable_tls=yes\nlisten=tls:127.0.0.1:{port}\nloadmodule "{module}"\n'
            f'loadmodule "{source}/modules/sl/sl.so"\n'
            f'modparam("tlsa", "config", "{runtime}/tls.cfg")\n'
            'modparam("sl", "bind_tm", 0)\n'
            'request_route { sl_send_reply("200", "OK"); exit; }\n')
        environment = os.environ.copy()
        environment.pop("LD_PRELOAD", None)
        environment.pop("TLSA_HIGH_KEYS", None)
        if mode != "normal":
            environment["LD_PRELOAD"] = str(build / "foreign_ssl.so")
        if mode == "high-keys":
            environment["TLSA_HIGH_KEYS"] = "1"
        process = None
        logpath = runtime / (mode + ".log")
        try:
            with logpath.open("w") as log:
                command = [str(source / "kamailio"), "-DD", "-E", "-Y", str(runtime),
                           "-f", str(config), "-m", "64", "-M", "8"]
                print("[STEP]", mode, command, flush=True)
                process = subprocess.Popen(command, stdout=log, stderr=log,
                                           env=environment, start_new_session=True)
                deadline = time.monotonic() + 15
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(f"core exited during startup: {process.returncode}")
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=.2):
                            break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("TLS listener startup")
                        time.sleep(.1)
                for version in (ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3):
                    response = request(port, runtime / "cert.pem", version, version.value)
                    check(mode + ": " + version.name + " SIP OPTIONS", True, response)
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    answers = list(pool.map(lambda number: request(
                        port, runtime / "cert.pem", ssl.TLSVersion.TLSv1_3, number + 1000), range(12)))
                check(mode + ": 12 connections / 4 clients / 2 TCP workers", len(answers) == 12)
                try:
                    context = ssl.create_default_context()
                    with context.wrap_socket(socket.create_connection(("127.0.0.1", port), timeout=5),
                                             server_hostname="localhost"):
                        check(mode + ": client rejects untrusted certificate", False)
                except ssl.SSLCertVerificationError:
                    check(mode + ": client rejects untrusted certificate", True)
        except Exception as error:
            check(mode + ": execution", False, repr(error))
        finally:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        logtext = logpath.read_text()
        check(mode + ": clean core exit", process is not None and process.returncode == 0)
        check(mode + ": no allocator corruption", "BUG:" not in logtext and "bad pointer" not in logtext)
        if mode != "normal":
            check(mode + ": external OpenSSL initialized first", "[FOREIGN_SSL] initialized" in logtext)
            preserved = re.findall(r"\[FOREIGN_STATE\] child=(\d+) preserved=(\d)", logtext)
            usable = re.findall(r"\[FOREIGN_STATE\] child=(\d+) ssl_context=(\d)", logtext)
            check(mode + ": foreign keys survive every observed child fork",
                  len({pid for pid, _ in preserved}) >= 2 and all(value == "1" for _, value in preserved))
            check(mode + ": foreign SSL works in every observed child",
                  len(usable) == len(preserved) and bool(usable) and all(value == "1" for _, value in usable))
            check(mode + ": foreign allocator remains unchanged",
                  "allocator_unchanged=1" in logtext and "allocator_unchanged=0" not in logtext)
    (runtime / "test-results.json").write_text(json.dumps(results, indent=2) + "\n")
    passed = sum(item["pass"] for item in results)
    print(f"[SUMMARY] {passed}/{len(results)} assertions passed", flush=True)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

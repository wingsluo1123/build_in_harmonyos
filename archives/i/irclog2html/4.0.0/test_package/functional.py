import os
import subprocess
import sys
import tempfile


def main():
    package = os.path.abspath(sys.argv[1])
    python_path = os.path.join(package, "lib", "python")
    wrapper = os.path.join(package, "bin", "irclog2html")
    if not os.path.isfile(wrapper):
        raise SystemExit("packaged irclog2html command is missing")
    command = [sys.executable, wrapper]

    with tempfile.TemporaryDirectory(prefix="irclog2html-consumer-") as work:
        source = os.path.join(work, "sample.log")
        output = source + ".html"
        with open(source, "w", encoding="utf-8") as log:
            log.write("2005-01-08T23:33:54  *** tester has joined #sample\n")
            log.write("2005-01-08T23:34:46  <tester> package consumer works\n")

        subprocess.run(command + ["--help"], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(command + [source], check=True)
        if not os.path.isfile(output):
            raise SystemExit("consumer did not produce the expected HTML file")
        with open(output, encoding="utf-8") as html:
            result = html.read()
        if "package consumer works" not in result:
            raise SystemExit("generated HTML does not contain the sample message")
        if not os.path.isfile(os.path.join(python_path, "irclog2html", "irclog.css")):
            raise SystemExit("packaged CSS resource is missing")
        print("consumer scenario passed: import, CLI help, HTML output, CSS resource")


if __name__ == "__main__":
    main()

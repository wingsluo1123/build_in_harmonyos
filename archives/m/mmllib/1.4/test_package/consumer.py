"""One installed-package workflow: parse numeric MML, export XML, use both CLIs."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from xml.dom import minidom

parser = argparse.ArgumentParser()
parser.add_argument("--package-folder", type=Path, required=True)
args = parser.parse_args()
package = args.package_folder.resolve()
modules = package / "lib" / "python"
sys.path.insert(0, str(modules))
import mmllib
from mmllib.musicxml import convert_mml_file
from mmllib.parser import mml_file, mml_file_meta

assert Path(mmllib.__file__).resolve().is_relative_to(modules), mmllib.__file__
distribution = importlib.metadata.distribution("MMLlib")
assert distribution.version == "1.4", distribution.version
assert {entry.name for entry in distribution.entry_points if entry.group == "console_scripts"} == {"mml2musicxml", "mmllint"}

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "numeric.mml"
    path.write_text("# Title: Numeric consumer\n\nT120L4N60N0\n", encoding="utf-8")
    tracks = mml_file(str(path))
    assert len(tracks) == 1 and tracks[0][0][0] > 0, tracks
    assert mml_file_meta(str(path))["duration"] == 1.0
    xml = convert_mml_file(str(path))
    document = minidom.parseString(xml)
    notes = document.getElementsByTagName("note")
    assert len(notes) == 2
    assert notes[0].getElementsByTagName("step")[0].firstChild.data == "B"
    assert notes[0].getElementsByTagName("octave")[0].firstChild.data == "6"
    assert len(notes[1].getElementsByTagName("rest")) == 1
    converted = subprocess.run([sys.executable, "-B", str(package / "bin/mml2musicxml"), str(path)], check=True, capture_output=True)
    assert converted.stdout.strip() == xml.strip(), converted.stdout
    checked = subprocess.run([sys.executable, "-B", str(package / "bin/mmllint"), "-q", str(path)], check=True, capture_output=True)
    assert b"No errors." in checked.stdout, checked.stdout
    print(json.dumps({"consumer_programs": 1, "assertions": 11, "module": mmllib.__file__,
                      "version": distribution.version, "api_xml_notes": 2,
                      "mml2musicxml_rc": converted.returncode, "mmllint_rc": checked.returncode,
                      "mmllint_output": checked.stdout.decode("utf-8"), "platform": sys.platform}))

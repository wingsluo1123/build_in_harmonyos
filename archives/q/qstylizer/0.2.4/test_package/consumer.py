"""One delivered-package QSS edit/serialize/reparse workflow; no Qt GUI required."""
import argparse
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--package-folder', required=True)
args = parser.parse_args()
package = Path(args.package_folder).resolve()
sys.path.insert(0, str(package / 'lib/python'))
import qstylizer.parser

assert Path(qstylizer.parser.__file__).resolve().is_relative_to(package)
sheet = qstylizer.parser.parse('QLabel { qproperty-text: "left;right"; color: red; }')
assert sheet.QLabel['qproperty-text'].value == '"left;right"'
sheet.QLabel.color.setValue('blue;')
assert sheet.QLabel.color.value == 'blue'
sheet.QLabel['image'] = 'url(data:image/png;base64,AAAA);'
assert sheet.QLabel.image.value == 'url(data:image/png;base64,AAAA)'
output = sheet.toString()
assert 'qproperty-text: "left;right";' in output
restored = qstylizer.parser.parse(output)
assert restored.QLabel['qproperty-text'].value == '"left;right"'
assert restored.QLabel.color.value == 'blue'
assert restored.QLabel.image.value == 'url(data:image/png;base64,AAAA)'
print(json.dumps({'consumer_flows': 1, 'assertions': 8, 'qss': output, 'module': qstylizer.parser.__file__}))

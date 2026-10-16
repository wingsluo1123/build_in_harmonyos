"""One package consumer: extract a complete region, claim it, retain all text."""
import argparse
import json
from pathlib import Path
import re
import sys


def consume(package_folder):
    delivered = Path(package_folder).resolve() / 'lib/python'
    sys.path.insert(0, str(delivered))
    import manuel
    assert Path(manuel.__file__).resolve().is_relative_to(delivered), manuel.__file__
    text = 'intro\nBEGIN block\nbody\nEND block\ntail\n'
    document = manuel.Document(text)
    regions = document.find_regions(re.compile(r'^BEGIN.*$', re.M), re.compile(r'^END', re.M))
    assert len(regions) == 1
    region = regions[0]
    assert region.source == 'BEGIN block\nbody\nEND block\n', 'MANUEL_REGION_CONTENT_LOSS: end-marker line suffix truncated'
    document.claim_region(region)
    region.parsed = {'body': 'body'}
    assert ''.join(item.source for item in document) == text, 'MANUEL_REGION_CONTENT_LOSS: claim_region changed document text'
    assert [item.lineno for item in document] == [1, 2, 5]
    result = {'scenario': 'delivered-package region extraction/claim/reassembly', 'package_module': manuel.__file__, 'regions': len(document.regions), 'preserves_document': True, 'consumer_scenarios': 1, 'assertions': 5}
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package-folder', required=True)
    consume(parser.parse_args().package_folder)

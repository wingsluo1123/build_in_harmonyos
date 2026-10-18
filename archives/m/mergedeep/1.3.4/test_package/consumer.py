"""Check strict Mapping conflicts and unchanged Counter semantics through public merge."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--package-folder', required=True)
args = parser.parse_args()
package = Path(args.package_folder).resolve()
import mergedeep
from mergedeep import Strategy, merge

module = Path(mergedeep.__file__).resolve()
assert module.is_relative_to(package), (module, package)
assert mergedeep.__version__ == '1.3.4'
assert not sys.flags.optimize, 'Assertions must remain enabled'
calls = 0
vectors = []
strict = (Strategy.TYPESAFE, Strategy.TYPESAFE_REPLACE, Strategy.TYPESAFE_ADDITIVE)
for strategy in strict:
    for reverse in (False, True):
        for nested in (False, True):
            a, b = Counter(a=1), {'b': 2}
            if reverse:
                a, b = b, a
            dst, src = {'key': a}, {'key': b}
            if nested:
                dst, src = {'outer': dst}, {'outer': src}
            before_dst, before_src = deepcopy(dst), deepcopy(src)
            expected = f'destination type: {type(a)} differs from source type: {type(b)} for key: "key"'
            calls += 1
            try:
                merge(dst, src, strategy=strategy)
            except TypeError as exc:
                assert str(exc) == expected, str(exc)
            else:
                raise AssertionError('Strict Mapping conflict silently merged')
            assert dst == before_dst and src == before_src
            actual_node = dst['outer']['key'] if nested else dst['key']
            assert type(actual_node) is type(a)
            vectors.append(f'{strategy.name}/reverse={reverse}/nested={nested}')
for strategy in strict:
    dst = {'key': Counter(a=1, common=2)}
    src = {'key': Counter(b=3, common=4)}
    before_src = deepcopy(src)
    calls += 1
    actual = merge(dst, src, strategy=strategy)
    common = 6 if strategy == Strategy.TYPESAFE_ADDITIVE else 4
    assert actual is dst and type(dst['key']) is Counter
    assert dst['key'] == Counter(a=1, b=3, common=common) and src == before_src
    vectors.append(f'{strategy.name}/same-type-Counter')
dst, src = {'key': {'a': [1]}}, {'key': {'a': [2]}}
calls += 1
assert merge(dst, src, strategy=Strategy.TYPESAFE_ADDITIVE) == {'key': {'a': [1, 2]}}
assert src == {'key': {'a': [2]}}
vectors.append('TYPESAFE_ADDITIVE/same-type-recursive-dict-list')
for strategy in (Strategy.REPLACE, Strategy.ADDITIVE):
    for reverse in (False, True):
        a, b = Counter(a=1), {'b': 2}
        if reverse:
            a, b = b, a
        dst, src = {'key': a}, {'key': b}
        calls += 1
        assert merge(dst, src, strategy=strategy) == {'key': {'a': 1, 'b': 2}}
        assert type(dst['key']) is type(a)
        vectors.append(f'{strategy.name}/mixed-Mapping/reverse={reverse}')
print(json.dumps({'consumer_programs': 1, 'merge_calls': calls, 'functional_vectors': len(vectors),
                  'identity_checks': 2, 'module': str(module), 'vectors': vectors,
                  'module_sha256': hashlib.sha256((module.parent / 'mergedeep.py').read_bytes()).hexdigest()},
                 indent=2))

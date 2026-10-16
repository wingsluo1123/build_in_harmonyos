"""Parse only original positive command fixtures without grntest directives."""
import copy
import json

def _reject_constant(value):
    raise ValueError('Non-JSON constant: ' + value)

DECODER = json.JSONDecoder(parse_constant=_reject_constant)

def commands(source):
    if '#@' in source or '#|' in source:
        raise ValueError('grntest directives/log expectations require upstream harness')
    # grntest's ordinary physical line continuation; source bytes remain untouched.
    lines = source.replace('\\\n', '').splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line.startswith(('table_create ', 'column_create ', 'select ', 'normalize ', 'tokenize ')):
            result.append(line)
        elif line.startswith('load '):
            payload = []
            while i < len(lines):
                payload.append(lines[i]); i += 1
                try:
                    parsed = json.loads('\n'.join(payload), parse_constant=_reject_constant)
                except json.JSONDecodeError:
                    continue
                if not isinstance(parsed, list):
                    raise ValueError('Selected load payload must be original JSON array')
                result.append(line + '\n' + '\n'.join(payload)); break
            else:
                raise ValueError('Incomplete load payload')
        else:
            raise ValueError('Unsupported command in selected parser: ' + line)
    if not result:
        raise ValueError('Empty fixture')
    return result

def expected_responses(source, oracle):
    cursor = 0
    result = []
    for command in commands(source):
        while cursor < len(oracle) and oracle[cursor].isspace(): cursor += 1
        if not oracle.startswith(command + '\n', cursor):
            raise ValueError('Oracle command echo does not match original logical command')
        cursor += len(command) + 1
        while cursor < len(oracle) and oracle[cursor].isspace(): cursor += 1
        response, cursor = DECODER.raw_decode(oracle, cursor)
        normalized = normalize_response(response)
        if normalized[0][0] != 0:
            raise ValueError('Selection contains upstream expected-error fixture')
        result.append(normalized)
    if oracle[cursor:].strip():
        raise ValueError('Unparsed oracle tail; no fields or logs may be discarded')
    return result

def actual_responses(stdout):
    result = []
    cursor = 0
    while cursor < len(stdout):
        while cursor < len(stdout) and stdout[cursor].isspace(): cursor += 1
        if cursor == len(stdout): break
        response, cursor = DECODER.raw_decode(stdout, cursor)
        result.append(normalize_response(response))
    return result

def normalize_response(response):
    if not (isinstance(response, list) and len(response) >= 2 and
            isinstance(response[0], list) and len(response[0]) >= 3 and
            isinstance(response[0][0], int) and not isinstance(response[0][0], bool) and
            all(isinstance(response[0][i], (int, float)) and not isinstance(response[0][i], bool) for i in [1, 2])):
        raise ValueError('Invalid original JSON response/header')
    normalized = copy.deepcopy(response)
    normalized[0][1] = 0.0
    normalized[0][2] = 0.0
    return normalized

def json_semantically_equal(left, right):
    # JSON objects ignore key order; booleans must never compare equal to numbers.
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if type(left) is not type(right): return False
    if isinstance(left, list):
        return len(left) == len(right) and all(json_semantically_equal(a,b) for a,b in zip(left,right))
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_semantically_equal(left[k],right[k]) for k in left)
    return left == right

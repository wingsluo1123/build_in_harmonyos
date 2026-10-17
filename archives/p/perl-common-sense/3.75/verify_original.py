"""Original tests plus provenance of the actual native-generated hint module."""
import hashlib,json,re
def verify(source,out,rc):
    lock=json.loads((source/'original-source-tests.json').read_bytes());expected=lock['source_files']
    assert len(expected)==2 and {p.relative_to(source).as_posix() for p in (source/'t').glob('*.t')}==set(expected)
    assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in expected.items()),'ORIGINAL_SOURCE_DRIFT'
    stdout=(out/'stdout').read_text();stderr=(out/'stderr').read_text();text=stdout+'\n'+stderr
    assert rc==0 and not re.search(r'^not ok\b|^Bail out!|#\s*(?:SKIP|TODO)\b',text,re.M|re.I),'ORIGINAL_TEST_FAILURE_OR_SKIP'
    files=re.findall('^t/(\\S+[.]t)\\b',stdout,re.M);assert {'t/'+n for n in files}==set(expected) and len(files)==2
    plans=re.findall(r'^1\.\.(\d+)[ \t]*$',stdout,re.M);rows=re.findall(r'^ok\s+\d+(?:[ \t]+[^\r\n]*)?$',stdout,re.M)
    assert plans==['1','1'] and len(rows)==2 and re.search(r'Files=2,\s*Tests=2\b',text) and 'All tests successful.' in text
    generated=(source/'sense.pm').read_bytes();assert b'package common::sense;' in generated and b'our $VERSION = 3.75;' in generated
    (out/'generated-sense.pm').write_bytes(generated)
    value={'source_files':expected,'source_file_count':2,'actual_passed_assertions':2,'skip':0,'todo':0,'rc':rc,'full_upstream_pass':True,'native_generator_input_sha256':hashlib.sha256((source/'sense.pm.PL').read_bytes()).hexdigest(),'native_generated_module_sha256':hashlib.sha256(generated).hexdigest(),'stdout_sha256':hashlib.sha256((out/'stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/'stderr').read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(value,sort_keys=True));return value

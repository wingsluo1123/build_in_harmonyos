import pytest
from qstylizer.parser import parse
from qstylizer.style import StyleSheet


@pytest.mark.parametrize('value, expected', [
    ('"left;right"', '"left;right"'),
    ("'left;right';", "'left;right'"),
    ('"left;right";  ', '"left;right"  '),
    ('url(data:image/png;base64,AAAA);', 'url(data:image/png;base64,AAAA)'),
    (r'left\;', r'left\;'),
    ('red;;', 'red'),
])
def test_literal_and_terminator(value, expected):
    assert StyleSheet._sanitize_value(value) == expected


def test_parser_roundtrip():
    sheet = parse('QLabel { qproperty-text: "left;right"; color: red; }')
    assert sheet.QLabel['qproperty-text'].value == '"left;right"'
    assert sheet.QLabel.color.value == 'red'
    output = sheet.toString()
    assert 'qproperty-text: "left;right";' in output
    assert parse(output).QLabel['qproperty-text'].value == '"left;right"'

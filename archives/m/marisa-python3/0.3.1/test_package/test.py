import sys
from pathlib import Path
import marisa
import _marisa

expected = Path(sys.argv[1]).resolve()
assert Path(marisa.__file__).resolve().parent == expected
assert Path(_marisa.__file__).resolve().parent == expected
def text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value
keys = ["ascii", "icecream", "かな/仮名", "かな/カナ"]
keyset = marisa.Keyset()
for key in keys:
    keyset.push_back(key)
trie = marisa.Trie()
trie.build(keyset)
assert trie.num_keys() == 4
print("PASS four keys")
agent = marisa.Agent()
agent.set_query("ascii")
assert trie.lookup(agent)
identifier = agent.key_id()
print("PASS lookup")
agent.set_query("absent")
assert not trie.lookup(agent)
print("PASS missing lookup")
agent.set_query(identifier)
trie.reverse_lookup(agent)
assert text(agent.key_str()) == "ascii"
print("PASS reverse lookup")
agent.set_query("かな/仮名")
assert trie.lookup(agent)
print("PASS unicode key")
agent.set_query("icecream soda")
prefixes = []
while trie.common_prefix_search(agent):
    prefixes.append(text(agent.key_str()))
assert prefixes == ["icecream"]
print("PASS common prefix")
trie.save("consumer.dic")
loaded = marisa.Trie()
loaded.load("consumer.dic")
agent.set_query("ascii")
assert loaded.lookup(agent)
print("PASS save load")
mapped = marisa.Trie()
mapped.mmap("consumer.dic")
agent.set_query("かな")
predictions = []
while mapped.predictive_search(agent):
    predictions.append(text(agent.key_str()))
assert set(predictions) == {"かな/仮名", "かな/カナ"}
print("PASS mmap predictive")
print("MARISA_PYTHON_CONSUMER_RESULT=8/8")

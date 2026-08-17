"""Load the mirrored production parameters extracted by scripts/sync.py."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(os.path.dirname(_HERE), "data")


def weights_path():
    return os.path.join(_DATA, "weights.json")


def load_weights(path=None):
    """Return the parsed data/weights.json ({meta, note, groups})."""
    with open(path or weights_path(), encoding="utf-8") as f:
        return json.load(f)


def flat_values(doc=None):
    """{ParamName: value} across all groups."""
    doc = doc or load_weights()
    out = {}
    for group in doc["groups"].values():
        for name, entry in group.items():
            out[name] = entry["value"]
    return out


def refs(doc=None):
    """{ParamName: 'file:line'}"""
    doc = doc or load_weights()
    out = {}
    for group in doc["groups"].values():
        for name, entry in group.items():
            out[name] = entry["ref"]
    return out

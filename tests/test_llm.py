"""Appel Claude : schéma nettoyé pour l'API et lecture de la réponse JSON."""
import json
from types import SimpleNamespace

import pytest

from clipper import llm
from clipper import prompts
from clipper.slides import prompts as sprompts, trends


def _objects(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for v in node.values():
            yield from _objects(v)
    elif isinstance(node, list):
        for v in node:
            yield from _objects(v)


@pytest.mark.parametrize("schema", [prompts.SELECTION_SCHEMA, prompts.TITLES_SCHEMA, sprompts.IDEAS_SCHEMA,
                                    sprompts.SCRIPT_SCHEMA, sprompts.PICK_SCHEMA, trends.SHOT_SCHEMA,
                                    trends.BATCH_SCHEMA])
def test_api_schema_is_accepted_shape(schema):
    s = llm.api_schema(schema)
    assert all(o.get("additionalProperties") is False for o in _objects(s))
    txt = json.dumps(s)
    assert '"minimum"' not in txt and '"maximum"' not in txt
    assert schema != s and "additionalProperties" not in json.dumps(schema)   # l'original n'est pas modifié


def test_structured_uses_output_config(monkeypatch):
    sent = {}

    class Msgs:
        def create(self, **kw):
            sent.update(kw)
            return SimpleNamespace(stop_reason="end_turn", content=[
                SimpleNamespace(type="thinking", thinking="…"),
                SimpleNamespace(type="text", text='{"index": 2, "character_match": true}')])

    monkeypatch.setattr(llm, "_client", SimpleNamespace(messages=Msgs()))
    out = llm.structured(model="m", system="s", user="u", tool_name="pick_image", tool_desc="Store it.",
                         schema=sprompts.PICK_SCHEMA)
    assert out == {"index": 2, "character_match": True}
    assert "tool_choice" not in sent and "tools" not in sent
    assert sent["extra_body"]["output_config"]["format"]["type"] == "json_schema"


def test_structured_truncated(monkeypatch):
    budgets = []

    class Msgs:
        def create(self, **kw):
            budgets.append(kw["max_tokens"])
            return SimpleNamespace(stop_reason="max_tokens", content=[SimpleNamespace(type="text", text='{"a"')])
    monkeypatch.setattr(llm, "_client", SimpleNamespace(messages=Msgs()))
    with pytest.raises(RuntimeError, match="tronquée"):
        llm.structured(model="m", system="s", user="u", tool_name="t", tool_desc="d", schema={"type": "object"})
    assert budgets == [4096, 16384, 20000]


def test_structured_retries_with_more_tokens(monkeypatch):
    budgets = []

    class Msgs:
        def create(self, **kw):
            budgets.append(kw["max_tokens"])
            if len(budgets) == 1:
                return SimpleNamespace(stop_reason="max_tokens", content=[])
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text='{"a": 1}')])
    monkeypatch.setattr(llm, "_client", SimpleNamespace(messages=Msgs()))
    assert llm.structured(model="m", system="s", user="u", tool_name="t", tool_desc="d",
                          schema={"type": "object"}, max_tokens=12000) == {"a": 1}
    assert budgets == [12000, 20000]

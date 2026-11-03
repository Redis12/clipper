"""Appels à Claude avec réponse JSON garantie par un schéma (sorties structurées, `output_config.format`).

Les modèles récents refusent `tool_choice` forcé ; les sorties structurées marchent sur tous les modèles.
Le schéma est « nettoyé » pour l'API : `additionalProperties: false` partout, sans contraintes numériques.
"""
from __future__ import annotations

import copy
import json
from typing import Any

from . import config
from .util import log

_client = None
UNSUPPORTED = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
               "minLength", "maxLength", "maxItems", "pattern"}


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.secret("ANTHROPIC_API_KEY"), max_retries=4)
    return _client


def api_schema(schema: dict) -> dict:
    """Copie du schéma acceptée par l'API : contraintes non gérées déplacées dans la description."""
    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            out, notes = {}, []
            for k, v in node.items():
                if k in UNSUPPORTED:
                    notes.append(f"{k}={v}")
                elif k == "minItems" and v not in (0, 1):
                    notes.append(f"minItems={v}")
                else:
                    out[k] = walk(v)
            if out.get("type") == "object":
                out["additionalProperties"] = False
            if notes:
                out["description"] = (out.get("description", "") + f" ({', '.join(notes)})").strip()
            return out
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node
    return walk(copy.deepcopy(schema))


MAX_RETRY_TOKENS = 20000   # au-delà, le SDK exige le streaming (requête > 10 min possible)


def structured(*, model: str, system: str, user: str | list, tool_name: str, tool_desc: str,
               schema: dict[str, Any], max_tokens: int = 4096) -> dict[str, Any]:
    """Rend un dict conforme à `schema`. `tool_name`/`tool_desc` servent de consigne (compatibilité)."""
    sys_prompt = f"{system}\n\nAnswer with the JSON object only ({tool_desc.rstrip('.')})."
    budget = max_tokens
    while True:
        msg = client().messages.create(
            model=model,
            max_tokens=budget,
            system=sys_prompt,
            messages=[{"role": "user", "content": user}],
            extra_body={"output_config": {"format": {"type": "json_schema", "schema": api_schema(schema)}}},
        )
        # Tronqué (souvent : la réflexion du modèle a mangé le budget) → on relance avec 4× plus, jusqu'à 20k.
        if msg.stop_reason != "max_tokens" or budget >= MAX_RETRY_TOKENS:
            break
        log.info("réponse tronquée (%s, %d tokens) : nouvel essai avec plus de place", tool_name, budget)
        budget = min(budget * 4, MAX_RETRY_TOKENS)
    if msg.stop_reason == "max_tokens":
        raise RuntimeError(f"Réponse de Claude tronquée ({tool_name}) même avec {budget} tokens")
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"Claude a refusé de répondre ({tool_name})")
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Réponse JSON illisible ({tool_name}) : {text[:300]}") from e


def image_block(path, max_side: int = 384) -> dict:
    """Image réduite en JPEG base64, prête à être envoyée à Claude (vision)."""
    import base64
    import io

    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(buf.getvalue()).decode()}}

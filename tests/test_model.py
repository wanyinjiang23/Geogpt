import json

import httpx
import pytest

from geosite.model import parse_llm, strict_schema
from geosite.parser import EXAMPLE, Clarification, parse_request
from geosite.workflow import run


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("GEOSITE_API_KEY", "test-placeholder")
    monkeypatch.setenv("GEOSITE_MODEL", "test-model")
    monkeypatch.setenv("GEOSITE_API_BASE", "https://example.invalid/v1")


def test_schema_requires_all_properties():
    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert set(node["required"]) == set(node["properties"])
                assert node["additionalProperties"] is False
            for v in node.values():
                check(v)
        if isinstance(node, list):
            for v in node:
                check(v)

    check(strict_schema())


def test_model_uses_same_gis_pipeline(config, tmp_path):
    def handler(request):
        body = json.loads(request.content)
        assert body["response_format"]["json_schema"]["strict"] is True
        assert "tools" not in body
        decision = {
            "needs_clarification": False,
            "issues": [],
            "request": parse_request(EXAMPLE).model_dump(),
        }
        decision["request"]["confirmed"] = True  # Model cannot grant user confirmation.
        return httpx.Response(
            200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(decision)}}]}
        )

    transport = httpx.MockTransport(handler)

    def model_parser(text):
        return parse_llm(text, transport=transport)

    first = run(EXAMPLE, tmp_path, mode="llm", model_parser=model_parser)
    assert first["state"] == "NEEDS_CLARIFICATION"
    assert not first["request"]["confirmed"]
    done = run(EXAMPLE, tmp_path, mode="llm", model_parser=model_parser, confirmed=True)
    offline = run(EXAMPLE, tmp_path, confirmed=True)
    assert done["top_k"] == offline["top_k"]


@pytest.mark.parametrize(
    "message,finish",
    [
        ({"refusal": "refused"}, "stop"),
        ({"content": "{broken"}, "stop"),
        ({"content": "{}"}, "stop"),
        ({"content": "{}"}, "length"),
    ],
)
def test_bad_outputs(config, message, finish):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"choices": [{"message": message, "finish_reason": finish}]})
    )
    with pytest.raises(Clarification):
        parse_llm(EXAMPLE, transport=transport)


def test_timeout_safe(config):
    def handler(request):
        raise httpx.ReadTimeout("sensitive-provider-details")

    with pytest.raises(Clarification, match="^MODEL_TIMEOUT$"):
        parse_llm(EXAMPLE, transport=httpx.MockTransport(handler))

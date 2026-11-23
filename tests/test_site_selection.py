import copy

import pytest

from geosite.datasets import demo_layers
from geosite.parser import EXAMPLE, parse_request
from geosite.schema import Preference
from geosite.selection import rank_candidates, select, validate_results


def test_explanation_and_rerank():
    r = parse_request(EXAMPLE)
    layers = demo_layers()
    rows, _, _, _ = select(r, layers)
    validate_results(rows, r, layers)
    assert all(c["passed"] for row in rows for c in row["constraints"])
    assert rank_candidates(rows, r) == rows
    original = rows[0]["candidate_id"]
    r.soft_preferences = [Preference(feature_layer="hospital", weight=1)]
    new = rank_candidates(rows, r)
    assert new[0]["candidate_id"] != original
    assert new[0]["distances_m"]["hospital"] == min(x["distances_m"]["hospital"] for x in rows)


def test_tampered_results_rejected():
    request = parse_request(EXAMPLE)
    layers = demo_layers()
    rows, _, _, _ = select(request, layers)
    bad = copy.deepcopy(rows)
    bad[0]["distances_m"]["hospital"] += 10
    with pytest.raises(ValueError, match="DISTANCE_MISMATCH"):
        validate_results(bad, request, layers)
    bad = copy.deepcopy(rows)
    bad[0]["score"] += 0.5
    with pytest.raises(ValueError, match="SCORE_MISMATCH"):
        validate_results(bad, request, layers)

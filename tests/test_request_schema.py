import pytest
from pydantic import ValidationError

from geosite.parser import EXAMPLE, Clarification, parse_request
from geosite.schema import Constraint, Preference, SiteSelectionRequest


def test_units_and_example():
    assert parse_request("距医院不超过0.5公里").hard_constraints[0].distance_m == 500
    r = parse_request(EXAMPLE)
    assert len(r.hard_constraints) == 2
    assert r.soft_preferences[0].feature_layer == "major_road"


@pytest.mark.parametrize(
    "text",
    [
        "医院附近",
        "距学校不超过500米",
        "北京距医院不超过500米",
        "距医院不超过一千米",
        "距医院不超过500米且人口大于100",
    ],
)
def test_clarification(text):
    with pytest.raises(Clarification):
        parse_request(text)


@pytest.mark.parametrize("n", [-1, 0, 10001, float("nan"), float("inf")])
def test_invalid_distances(n):
    with pytest.raises(ValidationError):
        Constraint(feature_layer="hospital", operator="within", distance_m=n)


def test_conflict_and_weights():
    with pytest.raises(ValidationError, match="CONFLICTING"):
        parse_request("距医院不超过500米，距医院至少800米")
    with pytest.raises(ValidationError, match="ZERO_WEIGHT"):
        SiteSelectionRequest(
            hard_constraints=[Constraint(feature_layer="hospital", operator="within", distance_m=500)],
            soft_preferences=[Preference(feature_layer="major_road", weight=0)],
        )

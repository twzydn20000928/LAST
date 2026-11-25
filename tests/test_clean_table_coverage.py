import pytest

from last.clean_table import render


def test_partial_inputs_and_official_inapplicability_remain_distinct():
    score = dict(status="completed", expected_units=20, valid_units=19,
                 not_applicable_units=1, mean=0.5, full_dimension_inputs=True)
    report = dict(family="hunyuan", mode="i2v", method="last", complete=False, v_score=None,
                  dimensions={"Composition": score, "Camera_Motion": dict(score, full_dimension_inputs=False)})
    table = render("hunyuan", [], [report])
    assert "pending (1/18 dimensions)" in table
    assert "I2V LAST, Composition: 1/20" in table
    score.update(valid_units=0, not_applicable_units=20, mean=None)
    table = render("hunyuan", [], [report])
    assert "pending (0/18 dimensions)" in table
    assert "I2V LAST, Composition: 20/20" in table
    score["mean"] = 0
    with pytest.raises(ValueError, match="applicable unit count"):
        render("hunyuan", [], [report])

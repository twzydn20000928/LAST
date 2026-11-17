"""Exercise Wan's optional text dependency before loading any model weights."""
import pytest


def test_both_wan_prompt_cleaners():
    pytest.importorskip('diffusers')
    from diffusers.pipelines.wan.pipeline_wan import prompt_clean as t2v
    from diffusers.pipelines.wan.pipeline_wan_i2v import prompt_clean as i2v
    for clean in (t2v, i2v):
        assert clean('  A  cat\n &amp; dog  ') == 'A cat & dog'
        assert clean('caf\u00c3\u00a9') == 'caf\u00e9'

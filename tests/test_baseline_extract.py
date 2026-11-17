import numpy as np
import pytest
from last.baseline_extract import validate_prediction

def test_native_output_validation_preserves_wrong_bits():
    bits=np.arange(512)%2
    assert np.array_equal(validate_prediction(bits.reshape(1,8,1,8,8)),bits)
    # Zero is a valid decoded bit, never a missing-output substitute.
    assert np.array_equal(validate_prediction(np.zeros(512)),np.zeros(512))
    with pytest.raises(ValueError):validate_prediction(np.zeros(511))
    with pytest.raises(ValueError):validate_prediction(np.full(512,np.nan))
    with pytest.raises(ValueError):validate_prediction(np.full(512,2))

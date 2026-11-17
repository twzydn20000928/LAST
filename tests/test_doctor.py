from last.doctor import version_errors

def test_local_cuda_version_suffix_and_missing_dependency():
    assert version_errors({'torch':'2.5.1+cu124'},{'torch':'2.5.1'})=={}
    assert version_errors({'Pillow':'12.3.0'},{'Pillow':'11.0.0'})['Pillow']['actual']=='12.3.0'
    assert version_errors({}, {'Pillow':'11.0.0'})['Pillow']['actual'] is None

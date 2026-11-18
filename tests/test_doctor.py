from last.doctor import gpu_environment_errors, version_errors

def test_paper_runtime_rejects_cpu_and_other_versions():
    assert gpu_environment_errors((3, 10, 22), True, '12.4') == []
    assert len(gpu_environment_errors((3, 11), False, None)) == 3

def test_local_cuda_version_suffix_and_missing_dependency():
    assert version_errors({'torch':'2.5.1+cu124'},{'torch':'2.5.1'})=={}
    assert version_errors({'Pillow':'12.3.0'},{'Pillow':'11.0.0'})['Pillow']['actual']=='12.3.0'
    assert version_errors({}, {'Pillow':'11.0.0'})['Pillow']['actual'] is None

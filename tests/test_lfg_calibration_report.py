from copy import deepcopy
from last.lfg_calibration_report import select


def candidates():
    return [dict(candidate=str(i), complete=True, lfg_alpha=.025*(i+1),
                 lfg_final_steps=10, final_mean_video_psnr_db=40.,
                 final_mean_ssim=.99) for i in range(15)]


def test_partial_grid_cannot_lock_even_with_eligible_point():
    cells=candidates();cells[0]['final_mean_video_psnr_db']=33.1
    cells[-1]['complete']=False
    assert select(cells)==dict(status='incomplete',selected=None)


def test_quality_gates_no_fallback_to_best_ineligible_candidate():
    cells=candidates()
    assert select(cells)['status']=='unmatched'
    cells[0].update(final_mean_video_psnr_db=33.1,final_mean_ssim=.949)
    assert select(cells)['selected'] is None


def test_accuracy_has_no_effect_and_tie_break_is_deterministic():
    cells=candidates()
    cells[0].update(final_mean_video_psnr_db=33.1,bit_accuracy=1.)
    cells[1].update(final_mean_video_psnr_db=33.1,lfg_final_steps=5,bit_accuracy=0.)
    expected=select(cells)
    assert expected['selected']['candidate']=='1'
    modified=deepcopy(cells)
    for cell in modified:cell['bit_accuracy']=1-cell.get('bit_accuracy',0.)
    assert select(modified)==expected

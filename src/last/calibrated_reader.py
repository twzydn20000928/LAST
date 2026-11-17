"""Development-calibrated energy/spacing control, separate from primary CCTA."""
import torch
from .energy_calibration import projected_energy, transform
from .ccta import energy_fallback


def align(correlations,nodes,calibration,group_frames=4):
    if (correlations.ndim!=3 or correlations.shape!=(len(nodes),16,592)
            or not torch.isfinite(correlations).all() or group_frames<1):
        raise ValueError('Expected finite candidate x16x592 correlations and matching nodes')
    if not nodes:
        return torch.zeros(592,device=correlations.device),dict(route='no_evidence',groups=0)
    for node in nodes:
        if (type(node['start']) is not int or type(node['end']) is not int
                or node['start']<0 or node['end']<node['start']
                or node['end']-node['start']>=group_frames or type(node['segment']) is not int):
            raise ValueError('Invalid temporal candidate bounds')
    scores=transform(projected_energy(correlations.detach().cpu().numpy()),calibration)
    scores=torch.as_tensor(scores,device=correlations.device,dtype=torch.float64)
    soft,meta=energy_fallback(correlations,nodes,group_frames,scores,normalized_fusion=True)
    meta.update(reconstruction=True,calibration_definition=calibration['definition'],
                fusion='Mean of L2-normalized selected group evidence; unique group slots',
                search='Best group per candidate, monotone exact-spacing non-overlap DP per segment')
    return soft,meta

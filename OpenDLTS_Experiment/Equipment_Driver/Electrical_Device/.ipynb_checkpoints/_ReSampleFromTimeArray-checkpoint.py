import numpy as np

__all__ = ['ReSampleFromTimeArray']
def ReSampleFromTimeArray(Input_t_array, N_sample, space: str = 'log'):
    t = np.asarray(Input_t_array)
    valid_indices = np.nonzero(t>0)[0]
    start_idx = valid_indices[0]
    t_min = t[start_idx]
    t_max = t[-1]
    if space == 'lin':
        target_times = np.linspace(t_min, t_max, N_sample)
    elif space == 'log':
        target_times = np.geomspace(t_min,t_max,N_sample)
    idx_insertion = np.searchsorted(t, target_times)
    idx_insertion = np.clip(idx_insertion, start_idx + 1, len(t) - 1)
    idx_left = idx_insertion - 1
    idx_right = idx_insertion
    dt_left = np.abs(t[idx_left] - target_times)
    dt_right = np.abs(t[idx_right] - target_times)
    closest_indices = np.where(dt_left < dt_right, idx_left, idx_right)
    final_indices = np.unique(closest_indices)
    return final_indices
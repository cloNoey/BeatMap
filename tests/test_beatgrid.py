from app.services.audio.analyze import map_to_8count
import numpy as np

def test_map_to_8count_simple():
    beat_times = np.array([i*0.5 for i in range(16)]) # 120 BPM
    phase = 0.0
    out = map_to_8count(beat_times, phase)
    counts = [c for _,_,c,_ in out[:8]]
    assert counts == [1,2,3,4,5,6,7,8]
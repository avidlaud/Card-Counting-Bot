from math import floor
from statistics import mean

def adjust_for_fps(frame_times):
    '''
    Determine an appropriate sampling rate depending on the timing for each frame.
    Normalizes behavior to match performance independent of computer hardware - namely GPU
    '''
    SAMPLES_PER_SECOND = 0.5
    return floor(1/(SAMPLES_PER_SECOND * mean(frame_times)))

def load_card_values(path):
    with open(path, 'r') as f:
        names = f.read().split('\n')
    return list(filter(None, names))

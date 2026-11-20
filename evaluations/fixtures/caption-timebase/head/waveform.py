from timeline import build_index, lookup

def label_for_sample(source, sample_number, sample_rate):
    position_us = sample_number * 1_000_000 // sample_rate
    return lookup(build_index(source), position_us)

from timeline import build_index, lookup

def label_at(source, elapsed_ms):
    return lookup(build_index(source), elapsed_ms)

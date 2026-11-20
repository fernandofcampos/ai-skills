def build_index(source):
    return [(row['start_ms'] * 1000, row['end_ms'] * 1000, row['text']) for row in source]

def lookup(index, position):
    for start_us, end_us, label in index:
        if start_us <= position < end_us:
            return label
    return None

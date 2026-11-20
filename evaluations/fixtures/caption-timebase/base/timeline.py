def build_index(source):
    return [(row['start_ms'], row['end_ms'], row['text']) for row in source]

def lookup(index, position):
    for start, end, label in index:
        if start <= position < end:
            return label
    return None

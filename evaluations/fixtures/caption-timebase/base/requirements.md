# Caption timeline contract, accepted in revision 3

Public clients call label_at(source, elapsed_ms) with an integer number of
milliseconds since playback began. The cue at the inclusive start and exclusive
end of its interval supplies the label. A gap returns None. The internal index
may use a different time unit without changing this interface.

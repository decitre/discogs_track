from dataclasses import dataclass


@dataclass
class Track:
    """

    """
    raw: dict
    artist: "Artist"
    title: str
    duration: str
    records: dict
    in_collection: bool
    alternatives: set # "alternative_tracks" maybe? or "other_versions"?

    _tracks = {}  # Indexed by artist_ids csv, then title, then duration

    @staticmethod
    def get_or_create(track_dict: dict, record: "Record", artist: "Artist" = None):
        title = track_dict["title"]
        duration = track_dict["duration"]
        if record.artist_full_id in Track._tracks and \
                title in Track._tracks[record.artist_full_id] and \
                duration in Track._tracks[record.artist_full_id][title]:
            track = Track._tracks[record.artist_full_id][title][duration]
            track.add_record(record)
        else:
            track = Track(artist, record, track_dict)
        return track

    @staticmethod
    def get_all(artist: "Artist"):
        """Returns the list of Track objects for the specified Artist"""
        return Track._tracks.get(artist.full_id)

    def __init__(self, artist: "Artist", record: "Record", track_dict: dict):
        self.raw = track_dict
        self.artist = artist
        self.title = track_dict["title"].strip()
        self.records = {record.id: record}
        self.duration = track_dict["duration"].strip().lstrip("0")
        if self.duration.startswith(':'):
            self.duration = f"0{self.duration}"
        self.in_collection = record.in_collection
        self.alternatives = set()
        self._register()

    def add_record(self, record: "Record"):
        self.records[record.id] = record
        if record.in_collection is not None:
            if self.in_collection is None:
                self.in_collection = record.in_collection
            else:
                self.in_collection |= record.in_collection

    def _register(self):
        Track._tracks.setdefault(self.artist.full_id, {}).setdefault(self.title, {})
        alternatives = set()
        for other_duration, other_track in Track._tracks[self.artist.full_id][self.title].items():
            if self.duration == other_duration:
                continue
            other_track.alternatives.add(self)
            alternatives.add(other_track)
        self.alternatives.update(alternatives)
        Track._tracks[self.artist.full_id][self.title][self.duration] = self

    def __repr__(self):
        _repr = [self.title, self.duration or "?:??"]
        if self.in_collection:
            _repr.append("X")
        return f'Track({", ".join(_repr)})'

    def __eq__(self, other):
        return self.title == other.title and self.duration == other.duration

    def __hash__(self):
        return hash((self.title, self.duration))

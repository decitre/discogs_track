from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .artist import Artist
    from .record import Record


class Track(dict):
    _tracks = {}  # Indexed by artist_ids, then title, then duration

    @staticmethod
    def get_or_create(artist: Artist, record: Record, track_dict: dict):
        artist_ids = {record['_artist']['id']} | {alias['id'] for alias in record['_artist']['_aliases']}
        artist_ids_id = ','.join(sorted(str(a) for a in artist_ids))
        title = track_dict['title']
        duration = track_dict['duration']
        if artist_ids_id in Track._tracks and \
                title in Track._tracks[artist_ids_id] and \
                duration in Track._tracks[artist_ids_id][title]:
            track = Track._tracks[artist_ids_id][title][duration]
            track.add_record(record)
        else:
            track = Track(artist, record, artist_ids_id, track_dict)
        return track

    @staticmethod
    def get_all(artist: Artist):
        artist_ids = ','.join(sorted([str(artist['id'])] + [str(alias['id']) for alias in artist['_aliases']]))
        return Track._tracks.get(artist_ids)

    def __init__(self, artist: Artist, record: Record, artist_ids: str, track_dict: dict):
        self.update(track_dict)
        self['_artist'] = artist
        self['_records'] = {record}
        self.in_collection = record['_in_collection']
        self.alternatives = set()
        self._register(artist_ids)
        super().__init__()

    def add_record(self, record: Record):
        self['_records'].add(record)
        self.in_collection |= record['_in_collection']

    def _register(self, artist_ids):
        Track._tracks.setdefault(artist_ids, {}).setdefault(self['title'], {})
        alternatives = set()
        for other_duration, other_track in Track._tracks[artist_ids][self['title']].items():
            if self['duration'] == other_duration:
                continue
            other_track.alternatives.add(self)
            alternatives.add(other_track)
        self.alternatives.update(alternatives)
        Track._tracks[artist_ids][self['title']][self['duration']] = self

    def __repr__(self):
        _repr = f'"{self["title"]}"'
        if self['duration']:
            _repr = f'{_repr} ({self["duration"]})'
        if self.in_collection:
            _repr = f'{_repr} X'
        return _repr

    def __eq__(self, other):
        return self['title'] == other['title'] and self['duration'] == other['duration']

    def __hash__(self):
        return hash((self['title'], self['duration']))

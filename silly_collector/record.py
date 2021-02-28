from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from .artist import Artist

from .api import API
from .track import Track

from dataclasses import dataclass

@dataclass
class Version:
    """
    A discogs recording version contains the fields:
    catno, country, format, id, label, major_formats, released , resource_url, stats, status, thumb, title
    We are only interested in: id, title, stats.community.user
    """
    raw: dict
    id: int
    title: str
    in_collection: bool
    in_wantlist: bool

    @classmethod
    def from_version_dict(cls, version_dict: dict):
        in_collection, in_wantlist = False, False
        if 'community' in version_dict['stats'] and 'user' in version_dict['stats']['community']:
            in_collection = version_dict['stats']['community']['user'].get('in_collection', False)
            in_wantlist = version_dict['stats']['community']['user'].get('in_wantlist', False)
        return Version(raw=version_dict, id=version_dict['id'], title=version_dict['title'],
                       in_collection=in_collection, in_wantlist=in_wantlist)

@dataclass
class DetailedRelease:
    """
    A discogs recording release contains the fields:
    artists, artists_sort, community, companies, country, data_quality, date_added, date_changed, estimated_weight,
    extraartists, format_quantity, formats, genres, id, identifiers, images, labels, lowest_price, master_id,
    master_url, num_for_sale, released, released_formatted, resource_url, series, status, styles, thumb, title,
    tracklist, uri, videos, year
    We are only interested in:
    artists[]|(id, name), extraartists[]|(id, name, role), formats, genres, id, master_id, num_for_sale, styles, title,
    tracklist[]|(duration, position, title, type_), uri, year
    """
    raw: dict
    id: int
    master_id: int
    title: str
    extra_artists: List[Dict[str, str]]
    formats: List[dict]
    genres: List[str]
    styles: List[str]


class Record(dict):

    @classmethod
    def from_version(cls, version: Version):
        return Record(release_or_version = version)

    @classmethod
    def from_release_id(cls, release_id):
        return Record(release_or_version = API.get_release(release_id))

    def __init__(self,
                 artist: Artist,
                 release_or_version: dict,
                 api: API):

        self.update(release_or_version)
        self['_artist'] = artist
        self['_in_collection'] = release_or_version['stats']['user']['in_collection'] != 0
        self['_tracks'] = []
        self['_missing_tracks'] = []
        self['_missing_tracks_ratio'] = 0.0
        release_details = api.get_release(release_id=self['id'])
        self.update(release_details)
        if 'format' in self:
            self['_format'] = self['format']
        else:
            self['_format'] = ', '.join(f['name'] for f in self['formats'])
            format_descriptions = ', '.join(', '.join(f['descriptions']) for f in self['formats'])
            if format_descriptions:
                self['_format'] = f'{format}, {format_descriptions}'
        self['_year'] = self.get('year', self.get('released', 'Unknown'))

        artist_ids = {artist['id']} | {alias['id'] for alias in artist['_aliases']}

        self['_track_artist_ids'] = set()
        for track_dict in self['tracklist']:
            if track_dict['type_'] != 'track':
                continue
            self['_track_artist_ids'].update(
                {a['id']
                 for a in track_dict.get('artists', self.get('artists', []))}
            )

        super().__init__()

    @property
    def track_artist_ids(self):
        return self['_track_artist_ids']

    def register(self, artists: Dict[str, Artist]):
        artist_ids = {self['_artist'] ['id']} | {alias['id'] for alias in self['_artist'] ['_aliases']}
        for track_dict in self['tracklist']:
            if track_dict['type_'] != 'track':
                continue
            track_artist_ids = {a['id'] for a in track_dict.get('artists', self.get('artists', []))}
            for track_artist_id in artist_ids.intersection(track_artist_ids):
                track_artist = artists[track_artist_id]
                self['_tracks'].append(Track.get_or_create(track_artist, self, track_dict))

    def __hash__(self):
        return hash((self['id'],))

    def __repr__(self):
        return f"{self.__class__.__name__}" \
               f"({self['_artist']['name']}, " \
               f"{self['title']}, " \
               f"{self['_format']}, " \
               f"{self['_year']}, " \
               f"{self['_missing_tracks_ratio']}, " \
               f"{self['uri']} )"

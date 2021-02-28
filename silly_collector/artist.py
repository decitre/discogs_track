from .api import API
from .record import Record, Version
from .track import Track
from typing import Optional


class Artist(dict):
    artists = {}

    @classmethod
    def create(cls, artist_id: int, api: API, alias=None) -> object:

        if artist_id in Artist.artists:
            return Artist.artists[artist_id]
        else:
            return Artist(artist_id, api, alias)

    def __init__(self, artist_id: Optional[int], api: Optional[API] = None, alias=None):
        self['id'] = artist_id
        self['_aliases'] = []
        self['_records'] = {}
        self['_missing_tracks'] = {}
        Artist.artists[artist_id] = self

        if api:
            self.update(api.get_artist(artist_id=artist_id))

            if not alias:
                # The entry artist is getting all aliases in its self.aliases
                if 'aliases' in self:
                    self['_aliases'] = [Artist.create(artist_id=a['id'], api=api, alias=self)
                                        for a in self['aliases']]
            else:
                # The alias artists have only one alias: the entry artist
                if alias not in self['_aliases']:
                    self['_aliases'].append(alias)
                if self not in alias['_aliases']:
                    alias['_aliases'].append(self)

            self['_records'].update(self._get_records(artist_id, api=api))

            if not alias:
                self['_missing_tracks'].update(self.get_missing_tracks())
                for alias in self['_aliases']:
                    alias['_missing_tracks'].update(alias.get_missing_tracks())

            super().__init__()

    def _get_records(self, record_id: int, api: API) -> dict:
        records = {}
        releases_pages = api.get_releases(record_id)
        for release_page in releases_pages:
            for release in release_page['releases']:
                if release['artist'] != self['name'] and release['artist'] != 'Various':
                    continue

                if release['type'] == 'master':
                    master_versions_pages = api.get_master_releases(master_id=release['id'])
                    for page in master_versions_pages:
                        for version_dict in page['versions']:
                            version = Version.from_version_dict(version_dict=version_dict)
                            record = Record(artist=self, release_or_version=version_dict, api=api)
                            record.register({id:Artist.artists[id] for id in record.track_artist_ids if id in Artist.artists})
                            if 'AIFF' in record['_format'] or 'FLAC' in record['_format'] or 'MP3' in record['_format']:
                                continue
                            records[record['id']] = record
                else:
                    record = Record(
                        artist=self,
                        release_or_version=release,
                        api=api)
                    record.register({id:Artist.artists[id] for id in record.track_artist_ids if id in Artist.artists})
                    if 'AIFF' in record['_format'] or 'FLAC' in record['_format'] or 'MP3' in record['_format']:
                        continue
                    records[record['id']] = record
        return records

    def get_tracks(self):
        return Track.get_all(self)

    def get_missing_tracks(self) -> dict:
        tracks = self.get_tracks()
        _missing = {}

        for title, title_data in tracks.items():
            for duration, track in title_data.items():
                if not track.in_collection and not (not track['duration'] and track.alternatives):
                    _missing.setdefault(title, {})[duration] = track
                    for record in track['_records']:
                        assert (not record['_in_collection'])
                        if track not in record['_missing_tracks']:
                            record['_missing_tracks'].append(track)
        return _missing

    def get_records_with_missing_tracks(self):
        _missing = {}
        for id_, record in self['_records'].items():
            if not isinstance(record, Record):
                continue
            if record['_in_collection'] or not record['_missing_tracks']:
                continue
            _missing.setdefault(len(record['_missing_tracks']), {})[id_] = record
            record['_missing_tracks_ratio'] = 1.0 * len(record['_missing_tracks']) / len(record['_tracks'])
        return _missing

    def __repr__(self):
        return f"Artist({self['name']})"


various = Artist(artist_id=None)
various['name'] = 'Various'

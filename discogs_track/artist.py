from .api import API
from .record import Record
from .track import Track
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class Artist:
    """
    A dict hosting the values returned by the API get_artist(artist_id) method.
    For example:
        {'id': 27963,
         'name': 'Frank Tovey', 'namevariations': ['F Tovey', 'F. Tovey', 'Tovey'], 'realname': 'Francis John Tovey',
         'aliases': [{'id': 2705, 'name': 'Fad Gadget', 'resource_url': 'https://api.discogs.com/artists/2705',
                      'thumbnail_url': 'https://img.discogs.com/...jpg'}],
         'data_quality': 'Needs Vote',
         'groups': [{'active': True, 'id': 2706, 'name': 'Mkultra',
                     'resource_url': 'https://api.discogs.com/artists/2706', 'thumbnail_url': ''},
                    {'active': True, 'id': 101467, 'name': 'Frank Tovey & The Pyros',
                     'resource_url': 'https://api.discogs.com/artists/101467', 'thumbnail_url': 'https://img.discogs.com/...jpg'}],
         'images': [...],
         'profile': '...',
         'releases_url': 'https://api.discogs.com/artists/27963/releases', 'resource_url': 'https://api.discogs.com/artists/27963',
         'uri': 'https://www.discogs.com/artist/27963-Frank-Tovey',
         'urls': ['http://www.franktovey.de/', 'https://en.wikipedia.org/wiki/Fad_Gadget']
         }

    The dict is enhanced with:
    - "_aliases": the list of Artist object of each id. Artists with no aliases have self as unique _aliases value.
    - "_records": the dict of the artist Record objects indexed by their release id
    - "_missing_tracks": The dict of the user's collection missing artist tracks, indexed by track title

    For example:

      '_aliases': [Artist(Fad Gadget)]
      '_records': {28107: Record(Frank Tovey, Some Bizzare Album, LP, Compilation, Album, 1981, 0.0, https://www.discogs.com/Various-Some-Bizzare-Album/release/28107 )
                    ...}
      '_missing_tracks':  {"Collapsing New People":
                            {'3:33': Track(Collapsing New People, 3:33),
                             '3:50': Track(Collapsing New People, 3:50), ... }

    The class is mostly useful for its get_missing_tracks() and get_records_with_missing_tracks() methods
    """
    raw: dict
    id: int
    all: Dict[int, "Artist"]
    full_id: str
    name: str
    api: API
    from_cache: bool

    aliases: list
    records: dict
    missing_tracks: dict

    artists = {}

    @classmethod
    def from_artist_id(cls, artist_id: int, api: API, alias=None) -> object:
        """
        Creates a new Artist object for a specific id, and register it in Artist.artists class dict.
        If the Artist already exists in the artists dict, return it instead of creating it.

        This method is mostly useful to not multiply Artist instances for the various artist aliases.
        It is typically initially called with no alias parameter by the Artist.__init__ constructor

        :param artist_id:
        :param api:
        :param alias:
        :return: Artist class instance
        """

        if artist_id in Artist.artists:
            return Artist.artists[artist_id]
        else:
            return Artist(artist_id, api, alias)

    def __init__(self, artist_id: Optional[int], api: Optional[API] = None, alias=None, from_cache=True):
        """
        The constructor is typically called without alias.
        It then calls itself recursively to consume all aliases.

        :param artist_id:
        :param api:
        :param alias:
        """

        self.id = artist_id
        self.all, self.full_id = {}, ''  # will be set by self.__init_aliases
        self.api = api
        self.aliases = []
        self.records = {}
        self.missing_tracks = {}
        self.completing_records = {}

        Artist.artists[artist_id] = self

        if not api:
            return

        self.raw = api.get_artist(artist_id=artist_id, from_cache=from_cache)
        self.from_cache = from_cache
        self.name = self.raw["name"]
        self.__init_aliases(alias, api)
        self.records = self.get_records(artist_id, api=api, from_cache=from_cache)
        if not alias:
            self.missing_tracks.update(self.discover_missing_tracks())
            for alias in self.aliases:
                alias.missing_tracks.update(alias.discover_missing_tracks())

    def __init_aliases(self, alias, api):
        if not alias:
            # The entry artist is getting all aliases in its self.aliases
            if "aliases" in self.raw:
                self.aliases = [Artist.from_artist_id(artist_id=a.id, api=api, alias=self) for a in self.aliases]
            self.__init_all()
        else:
            # The alias artists have only one alias: the entry artist
            if alias not in self.aliases:
                self.aliases.append(alias)
            if self not in alias.aliases:
                alias.aliases.append(self)

    def __init_all(self):
        self.all = {self.id: self}
        self.all.update({alias.id: alias for alias in self.aliases})
        self.full_id = f"f{','.join(sorted(map(str, self.all)))}"
        for alias in self.aliases:
            alias.all = self.all
            alias.full_id = self.full_id

    def check_for_completing_records(self):
        """Sets self.completing_records and calculates for each artist record, its missing tracks ratio"""
        self.completing_records = {}
        for id_, record in self.records.items():
            #if id_ in (3079185, 2976585):
            #    import pdb; pdb.set_trace()
            #    pass # 2976585 should be in collection, 3079185 not
            #if id_ == 8665018:
            #    import pdb; pdb.set_trace()
            #    pass
            if isinstance(record, Record):
                record.set_missing_tracks_ratio(self.full_id)
                self.completing_records.setdefault(len(record.missing_tracks), {})[id_] = record

    def get_records(self, artist_id: int, api: API, from_cache: bool=None) -> dict:
        records = {}
        releases_pages = api.get_releases(artist_id, from_cache=from_cache)
        for release_page in releases_pages:
            for release in release_page["releases"]:
                if release["artist"] == self.name:
                    artist = self
                elif release["artist"] == "Various":
                    artist = various
                else:
                    continue

                if release["type"] == "master":
                    master_versions_pages = api.get_master_releases(master_id=release["id"], from_cache=from_cache)
                    if len(master_versions_pages) > 1:
                        import pdb; pdb.set_trace()
                        pass # check for master_versions_pages and decide if we extract the method for readability
                    for page in master_versions_pages:
                        for version in page["versions"]:
                            record = Record(record_id=version["id"], artist=artist, with_artists=self.artists, version_raw_data=version, api=api, from_cache=from_cache)
                            if not record.is_digital:
                                records[record.id] = record
                else:
                    assert(release["type"] == "release")
                    #if release["id"] in (3079185, 2976585):
                    #    import pdb; pdb.set_trace()
                    #    pass # 2976585 should be in collection, 3079185 not
                    record = Record(record_id=release["id"], artist=artist, with_artists=self.artists, api=api, from_cache=from_cache)
                    if not record.is_digital:
                        records[record.id] = record
        return records

    def get_tracks(self):
        """Returns the list of the artist related Track objects"""
        return Track.get_all(self)

    def discover_missing_tracks(self) -> dict:
        tracks = self.get_tracks()
        _missing = {}
        for title, title_data in tracks.items():
            for duration, track in title_data.items():
                if not track.in_collection and not (not track.duration and track.alternatives):
                    _missing.setdefault(title, {})[duration] = track
                    for record_id, record in track.records.items():
                        assert (not record.in_collection)
                        if track not in record.missing_tracks:
                            record.missing_tracks.append(track)
        return _missing

    def get_completing_records(self):
        """
        Returns a nested dict of records containing tracks missed in the user's collection.
        The dict is indexed by number of missing tracks in the collection, then the record relaese id.
        :return:
        """
        return self.completing_records

    def tracks_report(self):
        """
        Returns for the artist a table of tracks details.
        The first element is a headers tuple:
            ('', 'track', 'm:s', 'alt', 'artist', 'record', '', 'format', 'year', 'uri')
        The first column contains a X when the track is in the user's collection.
        The 7th column contains a X when the track's release is in the user's collection.

        :return: A list of tuples
        """
        tracks_table = [('', 'track', 'm:s', 'alt', 'artist', 'record', '', 'format', 'year', 'uri')]
        tracks = self.get_tracks()
        for track_title in sorted(tracks):
            track_data = tracks[track_title]
            for duration in sorted(track_data)[::-1]:
                track = track_data[duration]
                for record_id, record in track.records.items():
                    tracks_table.append((
                        '' if not track.in_collection else 'X',
                        track_title, duration,
                        len(track.alternatives),
                        record.artist.name,
                        record.title,
                        '' if not record.in_collection else 'X',
                        record.format,
                        record.year,
                        record.url))
        return tracks_table

    def completing_records_report(self, min_tracks_number: int=0, for_sale: bool=False):
        records_table = [['nb', 'record']]
        for missing_nb in sorted(self.completing_records):
            if missing_nb <=0:
                continue
            with_this_nb = self.completing_records[missing_nb]
            for release_id, record in with_this_nb.items():
                if for_sale and not record.num_for_sale:
                    continue
                records_table.append([missing_nb, record])
                missing_nb = ''
        return records_table

    def __repr__(self):
        return f'Artist({self.name})'


class Various:
    def __init__(self):
        self.name = "Various"
        self.id, self.all, self.full_id = None, {None: self}, None


various = Various()

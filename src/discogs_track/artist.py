from tqdm import tqdm  # type: ignore  # https://github.com/tqdm/tqdm/issues/260

from .api import API  # type: ignore
from .record import Record  # type: ignore
from .track import Track  # type: ignore

from typing import Optional, Dict, Union, ClassVar
from dataclasses import dataclass


@dataclass
class Artist:
    """
    Hosts the values returned by the API get_artist(artist_id) method.

    Primary members:
    - aliases: the list of Artist object of each id. Artists with no aliases have self
      as unique _aliases value.
    - records: the dict of the artist Record objects indexed by their release id
    - missing_tracks: The dict of the user's collection missing artist tracks, indexed
      by track title

    For example:
      aliases: [Artist(Fad Gadget)]
      records: {28107: Record(Frank Tovey, Some Bizzare Album, LP, Compilation, Album,
                1981, 0.0, https://www.discogs.com/Various-Some-Bizzare-Album/release
                /28107 )
                ...}
      missing_tracks:  {"Collapsing New People":
                            {'3:33': Track(Collapsing New People, 3:33),
                             '3:50': Track(Collapsing New People, 3:50), ... }

    The class is mostly useful for its discover_missing_tracks() and
    check_for_completing_records() methods
    """

    raw: dict
    id: Optional[int]
    all: Dict[int, "Artist"]
    full_id: str
    name: str
    api: API
    from_cache: bool

    aliases: list
    records: dict
    missing_tracks: dict
    completing_records: Dict[int, Dict[int, Record]]

    ARTISTS: ClassVar[Dict[Union[int, None], "Artist"]] = {}

    @classmethod
    def from_artist_id(cls, artist_id: int, api: API, alias=None) -> object:
        """
        Creates a new Artist object for a specific id, and register it in Artist.ARTISTS
        class dict. If the Artist already exists in the ARTISTS dict, return it
        instead of creating it.

        This method is mostly useful to not multiply Artist instances for the various
        artist aliases. It is typically initially called with no alias parameter by
        the Artist.__init__ constructor

        :param artist_id:
        :param api:
        :param alias:
        :return: Artist class instance
        """

        if artist_id in Artist.ARTISTS:
            return Artist.ARTISTS[artist_id]
        else:
            return Artist(artist_id, api, alias)

    def __init__(
        self,
        artist_id: int,
        api: Optional[API] = None,
        alias=None,
        from_cache=True,
        verbosity: int = 0,
    ):
        """
        The constructor is typically called without alias.
        It then calls itself recursively to consume all aliases.

        :param artist_id:
        :param api:
        :param alias:
        """

        self.id = artist_id
        self.all, self.full_id = {}, ""  # will be set by self.__init_aliases
        self.api = api
        self.aliases = []
        self.records = {}
        self.missing_tracks = {}
        self.completing_records = {}

        Artist.ARTISTS[artist_id] = self

        if not api:
            return

        self.raw = api.get_artist(artist_id=artist_id, from_cache=from_cache)
        self.from_cache = from_cache
        self.name = self.raw["name"]
        self.__init_aliases(alias, api)
        self.records = self.get_records(
            artist_id, api=api, from_cache=from_cache, verbosity=verbosity
        )
        if not alias:
            self.missing_tracks.update(self.discover_missing_tracks())
            for alias in self.aliases:
                alias.missing_tracks.update(alias.discover_missing_tracks())

    def __init_aliases(self, alias, api):
        if not alias:
            # The entry artist is getting all aliases in its self.aliases
            if "aliases" in self.raw:
                self.aliases = [
                    Artist.from_artist_id(artist_id=a.id, api=api, alias=self)
                    for a in self.aliases
                ]
            self.__init_all()
        else:
            # The alias ARTISTS have only one alias: the entry artist
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
        """Sets self.completing_records and calculates for each artist record,
        its missing tracks ratio"""
        self.completing_records = {}
        for id_, record in self.records.items():
            if isinstance(record, Record):
                record.set_missing_tracks_ratio(self.full_id)
                self.completing_records.setdefault(len(record.missing_tracks), {})[
                    id_
                ] = record

    def get_records(
        self, artist_id: int, api: API, from_cache: bool = None, verbosity: int = 0
    ) -> dict:
        records = {}
        releases_pages = api.get_releases(artist_id, from_cache=from_cache)
        with tqdm(desc="releases") as pbar:
            for release in [
                release
                for release_page in releases_pages
                for release in release_page["releases"]
            ]:
                if release["artist"] == self.name:
                    artist: Union[Artist, Various] = self
                elif release["artist"] == "Various":
                    artist = various
                else:
                    continue

                if release["type"] == "master":
                    master_versions_pages = api.get_master_releases(
                        master_id=release["id"], from_cache=from_cache
                    )
                    for page in master_versions_pages:
                        for version in page["versions"]:
                            record = Record(
                                record_id=version["id"],
                                artist=artist,
                                with_artists=self.ARTISTS,
                                version_raw_data=version,
                                api=api,
                                from_cache=from_cache,
                            )
                            pbar.update(1)
                            if not record.is_digital:
                                records[record.id] = record
                else:
                    assert release["type"] == "release"
                    record = Record(
                        record_id=release["id"],
                        artist=artist,
                        with_artists=self.ARTISTS,
                        api=api,
                        from_cache=from_cache,
                    )
                    pbar.update(1)
                    if not record.is_digital:
                        records[record.id] = record
        return records

    def get_tracks(self):
        """Returns the list of the artist related Track objects"""
        return Track.get_all(self)

    def discover_missing_tracks(self) -> dict:
        tracks = self.get_tracks()
        _missing: Dict[str, Dict[str, Track]] = {}
        for title, title_data in tracks.items():
            for duration, track in title_data.items():
                if not track.in_collection and not (
                    not track.duration and track.alternatives
                ):
                    _missing.setdefault(title, {})[duration] = track
                    for _record_id, record in track.records.items():
                        assert not record.in_collection
                        if track not in record.missing_tracks:
                            record.missing_tracks.append(track)
        return _missing

    def tracks_report(self):
        """
        Returns for the artist a table of tracks details.
        The first element is a headers tuple:
            ('', 'track', 'm:s', 'alt', 'artist', 'record', '', 'format', 'year', 'uri')
        The first column contains a X when the track is in the user's collection.
        The 7th column contains a X when the track's release is in the user's collection.

        :return: A list of tuples
        """
        tracks_table = [
            ("", "track", "m:s", "alt", "artist", "record", "", "format", "year", "uri")
        ]
        tracks = self.get_tracks()
        for track_title in sorted(tracks):
            track_data = tracks[track_title]
            for duration in sorted(track_data)[::-1]:
                track = track_data[duration]
                for _record_id, record in track.records.items():
                    tracks_table.append(
                        (
                            "" if not track.in_collection else "X",
                            track_title,
                            duration,
                            len(track.alternatives),
                            record.artist.name,
                            record.title,
                            "" if not record.in_collection else "X",
                            record.format,
                            record.year,
                            record.url,
                        )
                    )
        return tracks_table

    def completing_records_report(
        self, min_tracks_number: int = 0, for_sale: bool = False
    ):
        """
        Returns a table of records containing tracks missing in the collection
        :param min_tracks_number: minimum number of missing tracks (default: 0)
        :param for_sale: To only get Records for sale, set this flag to True
        :return: An array of arrays. The first line is the header (nb, record)
        """
        records_table = [["nb", "record"]]
        for missing_nb in sorted(self.completing_records):
            if missing_nb <= min_tracks_number:
                continue
            with_this_nb = self.completing_records[missing_nb]
            missing_nb_s = str(missing_nb)
            for _release_id, record in with_this_nb.items():
                if for_sale and not record.num_for_sale:
                    continue
                records_table.append([missing_nb_s, record])
                missing_nb_s = ""
        return records_table

    def __repr__(self):
        return f"Artist({self.name})"


class Various:
    def __init__(self):
        self.name = "Various"
        self.id, self.all, self.full_id = None, {None: self}, None


various = Various()

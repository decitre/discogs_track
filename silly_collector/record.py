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
    A Discogs recording version contains the fields:
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
        if "community" in version_dict["stats"] and "user" in version_dict["stats"]["community"]:
            in_collection = version_dict["stats"]["community"]["user"].get("in_collection", False)
            in_wantlist = version_dict["stats"]["community"]["user"].get("in_wantlist", False)
        return Version(raw=version_dict, id=version_dict["id"], title=version_dict["title"],
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

@dataclass
class Record:
    """
    A dict hosting the values returned by the API get_release(artist_id) method.
    Example:
        {
         'artist': "Ak'chamel, The Giver Of Illness",
         'id': 4548889,
         'artists': [{'anv': '', 'id': 3281311, 'join': '', 'name': "Ak'chamel, The Giver Of Illness",
                      'resource_url': 'https://api.discogs.com/artists/3281311', 'role': '',
                      'thumbnail_url': 'https://i.discogs.com/...jpeg', 'tracks': ''}],
         'artists_sort': "Ak'chamel, The Giver Of Illness",
         'blocked_from_sale': False,
         'community': {...}, 'companies': [], 'country': 'US', 'data_quality': 'Needs Vote',
         'date_added': '2013-05-08T14:16:53-07:00', 'date_changed': '2015-07-19T19:14:36-07:00',
         'extraartists': [],
         'format': '8xFile, MP3, Album, 320', 'format_quantity': 0,
         'formats': [{'descriptions': ['MP3', 'Album'], 'name': 'File', 'qty': '8', 'text': '320 kbps'}],
         'genres': ['Electronic', 'Folk, World, & Country'],
         'identifiers': [],
         'images': [...],
         'label': 'DNA Collective',
         'labels': [{'catno': 'none', 'entity_type': '1', 'entity_type_name': 'Label', 'id': 790847, 'name': 'DNA Collective',
                     'resource_url': 'https://api.discogs.com/labels/790847',
                     'thumbnail_url': 'https://i.discogs.com/...jpeg'}],
         'lowest_price': None,
         'num_for_sale': 0,
         'released': '2013',
         'released_formatted': '2013',
         'resource_url': 'https://api.discogs.com/releases/4548889',
         'role': 'Main', 'series': [],
         'stats': {'community': {'in_collection': 2, 'in_wantlist': 6}, 'user': {'in_collection': 0, 'in_wantlist': 0}},
         'status': 'Accepted',
         'styles': ['Mouth Music', 'Noise'],
         'thumb': 'https://i.discogs.com/...jpeg',
         'title': 'The Divine Vine Tapes',
         'tracklist': [{'duration': '3:28', 'position': '1', 'title': 'The Purge', 'type_': 'track'}, ...],
         'type': 'release',
         'uri': 'https://www.discogs.com/release/4548889-AkchamelGiver-Of-Illness-The-Divine-Vine-Tapes',
         'year': 2013}

    Especially:
    - "id": Discogs release id
    - "artist": The release artist name string
    - "title": release title
    - "format": format string of the release
    - "formats": structured format dict list
    - "uri": Discogs URL of the release
    - "tracklist": List of tracks dict
    - "year", "released": the release year string
    - "artists": list of Discogs artist ids contributing to the release

    The dict is enhanced with:
    - "_artist": The release related Artist object
    - "_format": A formatted format string :)
    - "_in_collection": set to True when the release is in the user collection
    - "_missing_tracks": List of Track objects from that release not in the user collection
    - "_missing_tracks_ratio": Number of the release missing tracks over the total number of release tracks
    - "_track_artist_ids": List of Discogs ids of all tracks contributing artists
    - "_tracks": dict of Track objects lists for a specific artist in the record (valued through calls of set_tracks())

    Above example:
        '_artist': Artist(Ak'chamel, The Giver Of Illness)
        '_format': '8xFile, MP3, Album, 320'
        '_in_collection': False
        '_missing_tracks': []
        '_missing_tracks_ratio': 0.0
        '_track_artist_ids': {3281311}
        '_tracks': {}
        '_year': 2013
    """
    raw: dict
    version_raw: dict
    id: int
    artists: dict
    artist_full_id: str
    title: str
    url: str
    format: str
    year: str
    is_digital: bool
    num_for_sale: int
    tracks: dict
    track_artist_ids: set
    missing_tracks: list
    missing_tracks_ratio: dict
    in_collection: bool

    def __init__(self,
                 record_id: int,
                 artist: Artist=None,
                 with_artists: Dict[int, Artist] = None,
                 from_cache: bool = True,
                 api: API = None,
                 version_raw_data: dict=None):

        assert(artist is not None)

        self.id = record_id
        self.artist = artist
        self.with_artists = with_artists
        self.artist_full_id = artist.full_id
        self.tracks = {}
        self.missing_tracks = []
        self.missing_tracks_ratio = {}

        if api is None:
            api = API(cached=from_cache)
        release_details = api.get_release(release_id=self.id, from_cache=from_cache)

        self.raw = release_details
        self.title = release_details["title"]
        self.url = release_details.get("uri")
        self.year = release_details.get("year", release_details.get("released", "Unknown"))

        if version_raw_data:
            self.version_raw = version_raw_data
        elif "master_id" in release_details:
            master = api.get_master_releases(master_id=release_details["master_id"], from_cache=from_cache)
            for page in master:
                for version in page["versions"]:
                    if version["id"] == self.id:
                        self.version_raw = version
                        break
        else:
            self.version_raw = None

        self.__init_in_collection(api, release_details)

        self.track_artist_ids = set()
        self.num_for_sale = None if from_cache else release_details.get("num_for_sale", 0)

        self.__init_format()
        self.is_digital = "AIFF" in self.format or "FLAC" in self.format or "MP3" in self.format

        self.__init_tracks()

    def __init_in_collection(self, api, release_details):
        self.in_collection = False
        if "stats" in release_details:
            self.in_collection = release_details["stats"]["user"]["in_collection"] != 0
        elif self.version_raw and "stats" in self.version_raw:
            self.in_collection = self.version_raw["stats"]["user"]["in_collection"] != 0
        else:
            for page in api.get_collection_item(release_id=self.id):
                for release in page["releases"]:
                    if release["id"] == self.id:
                        self.in_collection = True
                        break
                if self.in_collection:
                    break
            else:
                self.in_collection = False

    def __init_format(self):
        if "format" in self.raw:
            self.format = self.raw["format"]
        else:
            self.format = ', '.join(sorted(f["name"] for f in self.raw["formats"]))
            format_descriptions = ', '.join(', '.join(sorted(f.get("descriptions", [])))
                                            for f in self.raw["formats"])
            if format_descriptions:
                self.format = f'{self.format}, {format_descriptions}'

    def __init_tracks(self):
        """Create the record related Track objects and registers them.
        :param artists: Only create Track instances for specific artists (example of compilations)
        :return: None
        """

        for track_dict in self.raw["tracklist"]:
            if track_dict["type_"] != "track":
                continue
            self.track_artist_ids.update(
                {artist["id"]
                 for artist in track_dict.get("artists", self.raw.get("artists", []))}
            )
            track_artist_ids = {artist["id"] for artist in track_dict.get("artists", self.raw.get("artists", []))}
            if self.with_artists:
                track_artist_ids = track_artist_ids.intersection(self.with_artists)
            for track_artist_id in track_artist_ids:
                track_artist = self.with_artists[track_artist_id] if self.with_artists else self.artist
                track = Track.get_or_create(track_dict, self, artist=track_artist)
                self.tracks.setdefault(track_artist.full_id if track_artist else None, []).append(track)

    def set_missing_tracks_ratio(self, artist_ids: str):
        # _missing_tracks are set by the Artist get_missing_tracks() method. This is weird.
        if self.in_collection:
            score = 0.0
        elif not self.missing_tracks:
            score = 0.0
        else:
            score = 1.0 * len(self.missing_tracks) / len(self.tracks[artist_ids])
        self.missing_tracks_ratio[artist_ids] = score

    def __hash__(self):
        return hash((self.id,))

    def __repr__(self):
        return f'{self.__class__.__name__}' \
               f'({self.artist.name}, ' \
               f'{self.title}, ' \
               f'{self.format}, ' \
               f'{self.year}, ' \
               f'{int(next(iter(self.missing_tracks_ratio.values()), 0)*100)}%, ' \
               f'{self.num_for_sale}, ' \
               f'{self.url} )'

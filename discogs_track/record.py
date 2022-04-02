from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING

from .api import API  # type: ignore
from .track import Track  # type: ignore

if TYPE_CHECKING:
    from .artist import Artist  # type: ignore
from dataclasses import dataclass


@dataclass
class Record:
    """
    Hosts the values returned by the API get_release(artist_id) method.

    Primary members:
    - ARTISTS: The release related Artist objects indexed by artist id
    - format: A formatted format string :)
    - in_collection: set to True when the release is in the user collection
    - missing_tracks: List of Track objects from that release not in the user collection
    - missing_tracks_ratio: Number of the release missing tracks over the total
    number of release tracks
    - track_artist_ids: List of Discogs ids of all tracks contributing ARTISTS
    - tracks: dict of Track objects lists for a specific artist in the record
    """

    raw: dict
    version_raw: Optional[dict]
    id: int
    artists: dict
    artist_full_id: str
    title: str
    url: Optional[str]
    format: str
    year: str
    is_digital: bool
    num_for_sale: Optional[int]
    tracks: dict
    track_artist_ids: set
    missing_tracks: list
    missing_tracks_ratio: dict
    in_collection: bool

    def __init__(
        self,
        record_id: int,
        artist: Artist = None,
        with_artists: Dict[int, Artist] = None,
        from_cache: bool = True,
        api: API = None,
        version_raw_data: dict = None,
    ):

        assert artist is not None

        self.id = record_id
        self.artist = artist
        self.with_artists = with_artists
        self.artist_full_id = artist.full_id
        self.tracks = {}
        self.missing_tracks = []
        self.missing_tracks_ratio = {}

        if api is None:
            api = API()
        release_details = api.get_release(release_id=self.id, from_cache=from_cache)

        self.raw = release_details
        self.title = release_details["title"]
        self.url = release_details.get("uri")
        self.year = release_details.get(
            "year", release_details.get("released", "Unknown")
        )

        if version_raw_data:
            self.version_raw = version_raw_data
        elif "master_id" in release_details:
            master = api.get_master_releases(
                master_id=release_details["master_id"], from_cache=from_cache
            )
            for page in master:
                for version in page["versions"]:
                    if version["id"] == self.id:
                        self.version_raw = version
                        break
        else:
            self.version_raw = None

        self.__init_in_collection(api, release_details)

        self.track_artist_ids = set()
        self.num_for_sale = (
            None if from_cache else release_details.get("num_for_sale", 0)
        )

        self.__init_format()
        self.is_digital = (
            "AIFF" in self.format or "FLAC" in self.format or "MP3" in self.format
        )

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
            self.format = ", ".join(sorted(f["name"] for f in self.raw["formats"]))
            format_descriptions = ", ".join(
                ", ".join(sorted(f.get("descriptions", [])))
                for f in self.raw["formats"]
            )
            if format_descriptions:
                self.format = f"{self.format}, {format_descriptions}"

    def __init_tracks(self):
        """Create the record related Track objects and registers them.
        :param ARTISTS: Only create Track instances for specific ARTISTS (example of
        compilations)
        :return: None
        """

        for track_dict in self.raw["tracklist"]:
            if track_dict["type_"] != "track":
                continue
            self.track_artist_ids.update(
                {
                    artist["id"]
                    for artist in track_dict.get("ARTISTS", self.raw.get("ARTISTS", []))
                }
            )
            track_artist_ids = {
                artist["id"]
                for artist in track_dict.get("ARTISTS", self.raw.get("ARTISTS", []))
            }
            if self.with_artists:
                track_artist_ids = track_artist_ids.intersection(self.with_artists)
            for track_artist_id in track_artist_ids:
                track_artist = (
                    self.with_artists[track_artist_id]
                    if self.with_artists
                    else self.artist
                )
                track = Track.get_or_create(track_dict, self, artist=track_artist)
                self.tracks.setdefault(
                    track_artist.full_id if track_artist else None, []
                ).append(track)

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
        return (
            f"{self.__class__.__name__}"
            f"({self.artist.name}, "
            f"{self.title}, "
            f"{self.format}, "
            f"{self.year}, "
            f"{int(next(iter(self.missing_tracks_ratio.values()), 0)*100)}%, "
            f"{self.num_for_sale}, "
            f"{self.url} )"
        )

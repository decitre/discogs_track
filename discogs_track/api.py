from redis import Redis
from requests import Session, Response, PreparedRequest
from requests_oauthlib import OAuth1  # type: ignore
from ujson import loads

import discogs_track

from time import sleep
import configparser
import os
from typing import List, Union

from logging import getLogger

logger = getLogger("discogs_track")


class Config:
    _auth: OAuth1

    CONFIG_FILE = "dt.cfg"

    def __init__(self, config_path: str = None):
        """
        :param config_path: The path of the .ini config file. Takes "dt.cfg" or
        "~/.dt.cfg" if not provided

        The config file must have a Discogs section, containing Discogs your
        credentials:
            [Discogs]
            user_name = ...
            consumer_key = ...
            consumer_secret = ...
            access_token_here = ...
            access_secret_here = ...
        """
        config = configparser.ConfigParser()
        config.read(
            [
                config_path or "",
                Config.CONFIG_FILE,
                os.path.expanduser(f"~/.{Config.CONFIG_FILE}"),
            ]
        )
        self._auth = OAuth1(
            config.get("Discogs", "consumer_key"),
            config.get("Discogs", "consumer_secret"),
            config.get("Discogs", "access_token_here"),
            config.get("Discogs", "access_secret_here"),
        )
        self._user_name = config.get("Discogs", "user_name")

    @property
    def auth(self):
        return self._auth

    @property
    def user_name(self):
        return self._user_name


class TooQuicklyRequests(Exception):
    pass


class Cache:
    _cache: Redis
    REDIS_DB = 0

    def __init__(self):
        self._cache = Redis(host="localhost", port=6379, db=Cache.REDIS_DB)

    def __getitem__(self, key: str) -> Union[str, None]:
        return self._cache.get(key)

    def __setitem__(self, key: str, value: str) -> None:
        self._cache.set(key, value)

    def __contains__(self, key: str) -> bool:
        return bool(self._cache.exists(key))


class API(object):
    """
    A very light wrapper around the Discogs Databse API
    https://www.discogs.com/developers#page:home
    """

    base_url = "https://api.discogs.com"
    max_per_minute = 59

    def __init__(self, config: Config = None, currency: str = "EUR"):
        """
        :param config: instance of Config class
        :param currency: The currency for Discogs prices. Takes "EUR" if not provided.
        """
        self.currency = currency

        self.cache = Cache()

        if config is None:
            config = Config()

        self.user_name = config.user_name
        self.user_agent = f"discogs_track/{discogs_track.__version__}"

        self.session = Session()
        self.session.auth = config.auth
        self.session.headers.update({"User-Agent": self.user_agent})

    def get_artist(self, artist_id: int, from_cache: bool = False) -> dict:
        """
        https://www.discogs.com/developers#page:database,header:database-artist-get
        :param artist_id: the Discogs artist id
        :param from_cache: Set to True: takes artist information form the cache
        (default: False)
        :return: a dictionary containing the Discogs artist details
        """
        obj = self.uncache_or_get(f"/artists/{artist_id}", from_cache=from_cache)
        return obj

    def get_releases(self, artist_id: int, from_cache: bool = True) -> List[dict]:
        """
        https://www.discogs.com/developers
                                    #page:database,header:database-artist-releases-get
        :param artist_id: the Discogs artist id
        :param from_cache: True to get releases from cache if available
        :return: an array of pages of Discogs releases for the artist
        """
        pages: List[dict] = []
        while True:
            expected_page_number = len(pages) + 1
            obj = self.get_artist_releases_page(
                artist_id, expected_page_number, from_cache=from_cache
            )
            pages.append(obj)
            if obj["pagination"]["pages"] == expected_page_number:
                break
        return pages

    def get_artist_releases_page(
        self, artist_id, expected_page_number, from_cache
    ) -> dict:
        return self.uncache_or_get(
            f"/artists/{artist_id}/releases?per_page=500&page={expected_page_number}",
            from_cache=from_cache,
        )

    def get_release(self, release_id: int, from_cache: bool = True) -> dict:
        """
        https://www.discogs.com/developers#page:database,header:database-release-get
        :param release_id: the Discogs record release id
        :param from_cache: True to get release from cache if available
        :return: a dictionary containing the details of the release
        """
        obj = self.uncache_or_get(
            f"/releases/{release_id}?{self.currency}", from_cache=from_cache
        )
        return obj

    def get_stats(self, release_id: int, from_cache: bool = True) -> dict:
        """
        https://www.discogs.com/developers#page:database,header:database-release-stats
        :param release_id: the Discogs record release id
        :param from_cache: True to get stats for releases in cache if available
        :return: a dictionary containing the details of the release
        """
        obj = self.uncache_or_get(
            f"/releases/{release_id}/stats", from_cache=from_cache
        )
        return obj

    def get_master_releases(self, master_id: int, from_cache=True) -> List[dict]:
        """
        https://www.discogs.com/developers#page:database,header:database-master-release-versions-get
        :param from_cache: True to get master releases from cache if available
        :param master_id: the Discogs record master id
        :return:
        """
        pages: List[dict] = []
        while True:
            expected_page_number = len(pages) + 1
            obj = self.get_master_releases_page(
                master_id, expected_page_number, from_cache=from_cache
            )
            pages.append(obj)
            if obj["pagination"]["pages"] == expected_page_number:
                break
        return pages

    def get_master_releases_page(self, master_id, pages_number, from_cache):
        obj = self.uncache_or_get(
            f"/masters/{master_id}/versions?per_page=500&page={pages_number + 1}",
            from_cache=from_cache,
        )
        return obj

    def get_collection_item(
        self, release_id: int, from_cache: bool = True
    ) -> List[dict]:
        """
        https://www.discogs.com/developers/
                page:user-collection,header:user-collection-collection-items-by-release
        :param release_id: the Discogs record release id
        :param from_cache: True to get collection items from cache if available
        :return: a dictionary containing the details of the release
        """
        pages: List[dict] = []
        while True:
            expected_page_number = len(pages) + 1
            obj = self.get_collection_item_page(
                release_id, expected_page_number, from_cache=from_cache
            )
            pages.append(obj)
            if obj["pagination"]["pages"] == expected_page_number:
                break
        return pages

    def get_collection_item_page(self, release_id, expected_page_number, from_cache):
        obj = self.uncache_or_get(
            f"/users/{self.user_name}/collection/releases/{release_id}?"
            f"per_page=500&page={expected_page_number}",
            from_cache=from_cache,
        )
        return obj

    def uncache_or_get(self, query: str, from_cache: bool = True) -> dict:
        url = f"{API.base_url}{query}"
        cached = url in self.cache and from_cache
        if cached:
            logger.debug(f"{url} (from cache)")
            text = self.cache[url]
        else:
            text = self.get(url)
            self.cache[url] = text

        obj = self.loads_or_fail(text)

        return obj

    @staticmethod
    def loads_or_fail(text):
        obj = loads(text)
        if obj == {"message": "We are making requests too quickly."}:
            raise TooQuicklyRequests()
        return obj

    def get(self, url) -> str:
        resp = self.session.get(url)
        text = resp.text
        self.sleep_if_needed(resp)
        return text

    @staticmethod
    def sleep_if_needed(resp: Response):
        rate_limit_remaining = int(resp.headers["X-Discogs-Ratelimit-Remaining"])
        request: PreparedRequest = resp.request
        logger.debug(
            f"{request.url} (remaining rate limit: {rate_limit_remaining}/minute)"
        )
        if rate_limit_remaining < 2:
            logger.warning("Wait 90s")
            sleep(90)
        elif rate_limit_remaining < 6:
            sleep(5)
        elif rate_limit_remaining < 10:
            sleep(2)

import redis  # brew services start redis
from requests import Session
from requests_oauthlib import OAuth1
from ujson import loads

from time import sleep
from pdb import set_trace
import configparser
import os
from typing import List


class API(object):
    """
    A very light asynchronous wrapper around the Discogs Databse API
    https://www.discogs.com/developers#page:home
    """
    my_version = 1.0
    base_url = 'https://api.discogs.com'
    max_per_minute = 59
    redis_db = 0

    def __init__(self, cached: bool = False, config_path: str = '', currency: str = 'EUR'):
        """
        :param cached: if True, uses the local API.redis_db as cache.
        :param config_path: The path of the .ini config file. Takes "sc.cfg" or "~/.sc.cfg" if not provided
        :param currency: The currency for Discogs prices. Takes "EUR" if not provided.

        The config file must have a Discogs section, containing Discogs your credentials:
            [Discogs]
            user_name = ...
            consumer_key = ...
            consumer_secret = ...
            access_token_here = ...
            access_secret_here = ...
        """
        self.currency = currency
        self._cache = redis.Redis(host='localhost', port=6379, db=API.redis_db)
        self.cached = cached

        config = configparser.ConfigParser()
        config.read([config_path, 'sc.cfg', os.path.expanduser('~/.sc.cfg')])
        self.auth = OAuth1(config.get('Discogs', 'consumer_key'),
                           config.get('Discogs', 'consumer_secret'),
                           config.get('Discogs', 'access_token_here'),
                           config.get('Discogs', 'access_secret_here'))
        self.user_name = config.get('Discogs', 'user_name')
        self.user_agent = f'missing_songs/{API.my_version}'
        self.session = Session()
        self.session.auth = self.auth
        self.session.headers.update({'User-Agent': self.user_agent})

    def get_artist(self, artist_id: int, from_cache: bool=False) -> dict:
        """
        https://www.discogs.com/developers#page:database,header:database-artist-get
        :param artist_id: the Discogs artist id
        :param from_cache: Set to True: takes artist information form the cache (default: False)
        :return: a dictionary containing the Discogs artist details
        """
        obj = self._get(f'/artists/{artist_id}', from_cache=from_cache)
        return obj

    def get_releases(self, artist_id: int, from_cache: bool=True) -> List[dict]:
        """
        https://www.discogs.com/developers#page:database,header:database-artist-releases-get
        :param artist_id: the Discogs artist id
        :return: an array of pages of Discogs releases for the artist
        """
        pages = []
        while True:
            obj = self._get(f'/artists/{artist_id}/releases?per_page=500&page={len(pages) + 1}', from_cache=from_cache)
            pages.append(obj)
            if obj['pagination']['pages'] == len(pages):
                break
        return pages

    def get_release(self, release_id: int, from_cache: bool=True) -> dict:
        """
        https://www.discogs.com/developers#page:database,header:database-release-get
        :param release_id: the Discogs record release id
        :return: a dictionary containing the details of the release
        """
        obj = self._get(f'/releases/{release_id}?{self.currency}', from_cache=from_cache)
        return obj

    def get_stats(self, release_id: int, from_cache: bool=True) -> dict:
        """
        https://www.discogs.com/developers#page:database,header:database-release-stats
        :param release_id: the Discogs record release id
        :return: a dictionary containing the details of the release
        """
        obj = self._get(f'/releases/{release_id}/stats', from_cache=from_cache)
        return obj

    def get_master_releases(self, master_id: int, from_cache=True) -> List[dict]:
        """
        https://www.discogs.com/developers#page:database,header:database-master-release-versions-get
        :param master_id: the Discogs record master id
        :return:
        """
        pages = []
        while True:
            obj = self._get(f'/masters/{master_id}/versions?per_page=500&page={len(pages) + 1}', from_cache=from_cache)
            pages.append(obj)
            if obj['pagination']['pages'] == len(pages):
                break
        return pages

    def get_collection_item(self, release_id: int, from_cache: bool=True) -> List[dict]:
        """
        https://www.discogs.com/developers/#page:user-collection,header:user-collection-collection-items-by-release
        :param release_id: the Discogs record release id
        :return: a dictionary containing the details of the release
        """
        pages = []
        while True:
            obj = self._get(f'/users/{self.user_name}/collection/releases/{release_id}?per_page=500&page={len(pages) + 1}',
                            from_cache=from_cache)
            pages.append(obj)
            if obj['pagination']['pages'] == len(pages):
                break
        return pages


    #
    def _get(self, query: str, from_cache: bool=True) -> dict:
        url = f'{API.base_url}{query}'
        if self.cached and url in self._cache and from_cache:
            print(f'{url} (from cache)')
            return loads(self._cache[url].decode())
        for _ in range(3):
            resp = self.session.get(url)
            text = resp.text
            rate_limit_remaining = int(resp.headers["X-Discogs-Ratelimit-Remaining"])
            print(f'{url} (remaining rate limit: {rate_limit_remaining}/minute)')
            self._cache[url] = text
            if rate_limit_remaining < 2:
                print('Wait 60s')
                sleep(60)
            elif rate_limit_remaining < 6:
                sleep(5)
            elif rate_limit_remaining < 10:
                sleep(2)
            obj = loads(text)
            if obj == {'message': 'You are making requests too quickly.'}:
                set_trace()
                pass
            return obj

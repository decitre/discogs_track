from time import sleep
import redis  # brew services start redis
from pdb import set_trace
import configparser
import os
from requests import Session
from requests_oauthlib import OAuth1
from json import loads
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
        self.user_agent = f'missing_songs/{API.my_version}'
        self.session = Session()
        self.session.auth = self.auth
        self.session.headers.update({'User-Agent': self.user_agent})

    def get_artist(self, artist_id: int) -> dict:
        """
        https://www.discogs.com/developers#page:database,header:database-artist-get
        :param artist_id: the Discogs artist id
        :return: a dictionary containing the Discogs artist details
        """
        obj = self._get(f'/artists/{artist_id}')
        return obj

    def get_releases(self, artist_id: int) -> List[dict]:
        """
        https://www.discogs.com/developers#page:database,header:database-artist-releases-get
        :param artist_id: the Discogs artist id
        :return: an array of pages of Discogs releases for the artist
        """
        pages = []
        while True:
            obj = self._get(f'/artists/{artist_id}/releases?per_page=500&page={len(pages) + 1}')
            pages.append(obj)
            if obj['pagination']['pages'] == len(pages):
                break
        return pages

    def get_release(self, release_id: int) -> dict:
        """
        https://www.discogs.com/developers#page:database,header:database-release-get
        :param release_id: the Discogs record release id
        :return: a dictionary containing the details of the release
        """
        obj = self._get(f'/releases/{release_id}?{self.currency}')
        return obj

    def get_master_releases(self, master_id: int) -> List[dict]:
        """
        https://www.discogs.com/developers#page:database,header:database-master-release-versions-get
        :param master_id: the Discogs record master id
        :return:
        """
        pages = []
        while True:
            obj = self._get(f'/masters/{master_id}/versions?per_page=500&page={len(pages) + 1}')
            pages.append(obj)
            if obj['pagination']['pages'] == len(pages):
                break
        return pages

    def _get(self, query: str) -> dict:
        url = f'{API.base_url}{query}'
        if self.cached and url in self._cache:
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

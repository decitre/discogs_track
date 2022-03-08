# silly collector

A tool for completists and other pop music collectors.
It is inspired from R.I.P the discogs.com [Track project](https://www.discogs.com/track). 

## missing tracks ratio
It calculates for a specified artist, a per record `missing_tracks_ratio`: 
The number of tracks none of the records of the user's collection contain, over the number of tracks in the record.
 A record with a 0% score is either already in the collection as one of its various releases, or all its tracks are contained by a set of other records in the collection.
A record with a 100% score only contains tracks not present in any other record of the user's collection.

## Installation

This tool is not yet in pypi.org.

    pip -v install https://github.com/gradracing/silly_collector.git

## Usage

| class | comment |
|:-------|:-------|
| `silly_collector.api.API` | A very light asynchronous wrapper around the [Discogs API](https://www.discogs.com/developers/). <p>Uses a local redis instance if <code>cached=True</code> is passed to its constructor.  |
| `silly_collector.aritist.Artist` | <p>A dict class derived from the Json returned by `/artists/{artist_id}`.</p><p>hosts the `get_missing_tracks()` and `get_completing_records()` methods</p> |
| `silly_collector.record.Record` | |



    Help on function __init__ in module silly_collector.api:

    __init__(self, cached: bool = False, config_path: str = '', currency: str = 'EUR')
    :param cached: if True, uses the local API.redis_db as cache.
    :param config_path: The path of the .ini config file. Takes "sc.cfg" or "~/.sc.cfg" if not provided
    :param currency: The currency for Discogs prices. Takes "EUR" if not provided.
    
        The config file must have a Discogs section, containing Discogs your credentials:
            [Discogs]
            consumer_key = ...
            consumer_secret = ...
            access_token_here = ...
            access_secret_here = ...    

## References


3. https://medium.com/@petehouston/install-and-config-redis-on-mac-os-x-via-homebrew-eb8df9a4f298
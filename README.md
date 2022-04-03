# discogs track

A tool for completists and other pop music collectors.
It is inspired by R.I.P the discogs.com [Tracks Beta project](https://www.discogs.com/track). 

## Installation

This tool is not yet in pypi.org.

```shell
$ pip -v install https://github.com/decitre/discogs_track.git
```


To start Redis service on Macos:

```shell
$ brew services start redis
```

[Shell completion](https://click.palletsprojects.com/en/latest/shell-completion) on zsh:

```shell
_DISCOGS_TRACK_COMPLETE=zsh_source discogs_track > ~/.discogs_track-complete.zsh
echo ". ~/.discogs_track-complete.zsh" >> ~/.zshrc
```

## Usage

```help
discogs_track --help
Usage: discogs_track [OPTIONS] COMMAND [ARGS]...

Options:
    --version             Show the version and exit.
    -v, --verbose         [x>=0]
    --cache / --no-cache
    --help                Show this message and exit.

Commands:
    artist
```

Examples:

```shell
$ discogs_track artist -i 3281311 show-tracks
$ discogs_track artist -i 3281311 show-completing
$ discogs_track --no-cache artist -i 3281311 show-completing --for-sale
$ discogs_track artist -i 3281311 release -i 20846845 show
```

The tool expects in `~/.dt.cfg` a INI config file containing a Discogs user credentials:

```ini
[Discogs]
user_name = ...
consumer_key = ...
consumer_secret = ...
access_token_here = ...
access_secret_here = ...    
```

## SDK

Some classes can be used as a SDK giving access to a subset of Discogs API features.

| class | comment |
|:-------|:-------|
| `api.API` | A very light asynchronous wrapper around the [Discogs API](https://www.discogs.com/developers/). <p>Uses a local redis instance if <code>cached=True</code> is passed to its constructor.  |
| `artist.Artist` | <p>Hosts the Json returned by `/artists/{artist_id}`.</p> and a few derived attributes. |
| `record.Record` | |
| `record.Track` | An abstraction of releases `tracklist` array elements|


## missing tracks ratio

It calculates for a specified artist, a per record `missing_tracks_ratio`:
The number of tracks none of the records of the user's collection contain, over the number of tracks in the record.
A record with a 0% score is either already in the collection as one of its various releases, or all its tracks are contained by a set of other records in the collection.
A record with a 100% score only contains tracks not present in any other record of the user's collection.

## To contribute

To install the dev/test tools and contribute to the project, do in your virtualenv:

```shell
$ pip install -e ".[dev]"
```

To upload a change:

```shell
$ python setup.py sdist bdist_wheel
$ twine upload dist/*
```



<!--
## References

3. https://medium.com/@petehouston/install-and-config-redis-on-mac-os-x-via-homebrew-eb8df9a4f298

-->
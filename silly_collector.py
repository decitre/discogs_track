from silly_collector.api import API
from silly_collector.artist import Artist

from tabulate import tabulate
from pprint import pprint
from sys import argv


if __name__ == "__main__":

    api = API(cached=True)

    artist = Artist(artist_id=int(argv[1]), api=api)

    tracks_table = []
    tracks = artist.get_tracks()

    for track_title in sorted(tracks):
        track_data = tracks[track_title]
        _track_title = track_title
        for duration in sorted(track_data)[::-1]:
            track = track_data[duration]

            for record in track['_records']:
                tracks_table.append(['' if not track.in_collection else 'X',
                                     _track_title,
                                     duration,
                                     len(track.alternatives),
                                     record['_artist']['name'],
                                     record['title'],
                                     '' if not record['_in_collection'] else 'X',
                                     record['_format'],
                                     record['_year'],
                                     record['uri']])
                _track_title = ''
    print(tabulate(tracks_table, headers=['', 'track', 'm:s', 'alt', 'artist', 'record', '', 'format', 'year', 'uri']))

    tracks_table = []
    records_with_missing_tracks = artist.get_records_with_missing_tracks()
    for missing_nb in sorted(records_with_missing_tracks):
        with_this_nb = records_with_missing_tracks[missing_nb]
        for release_id, record in with_this_nb.items():
            tracks_table.append([missing_nb, record])
            missing_nb = ''
    print(tabulate(tracks_table, headers=['nb', 'record']))

    for record_id in argv[2:]:
        record = artist['_records'][int(record_id)]
        print(record['uri'])
        pprint([(t, t.alternatives) for t in record['_tracks']])
    # pprint([(t, d, t.in_collection, [(r, r.in_collection) for r in t['_records']]) for d,t in Track.tracks[
    # '29001']['Dead And Re-Buried'].items()])

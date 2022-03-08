from silly_collector.api import API
from silly_collector.artist import Artist

from tabulate import tabulate
from pprint import pprint
from sys import argv


if __name__ == "__main__":

    api = API(cached=True)

    artist = Artist(artist_id=int(argv[1]), api=api)
    tracks_table = artist.tracks_report()
    print(tabulate(tracks_table[1:], headers=tracks_table[0]))

    #import pdb; pdb.set_trace()
    artist.check_for_completing_records()
    record_table = artist.completing_records_report(min_tracks_number=1)
    print(tabulate(record_table[1:], headers=record_table[0]))

    artist = Artist(artist_id=int(argv[1]), api=api, from_cache=False)
    artist.check_for_completing_records()

    record_table = artist.completing_records_report(min_tracks_number=1, for_sale=True)
    print(tabulate(record_table[1:], headers=record_table[0]))

    for record_id in argv[2:]:
        record = artist.records[int(record_id)]
        print(record.url)
        pprint([(t, t.alternatives) for ts in record.tracks.values() for t in ts])

    # pprint([(t, d, t.in_collection, [(r, r.in_collection) for r in t['_records']]) for d,t in Track.tracks[
    # '29001']['Dead And Re-Buried'].items()])

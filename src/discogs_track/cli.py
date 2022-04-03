import click
from tabulate import tabulate

from .api import API, Cache  # type: ignore
from .artist import Artist  # type: ignore

from logging import getLogger, basicConfig, DEBUG, INFO
from pprint import pprint

logger = getLogger("discogs_track")


@click.group("discogs_track")
@click.version_option()
@click.option("-v", "--verbose", count=True)
@click.option("--from-cache/--no-from-cache", default=True)
@click.pass_context
def cli(ctx, from_cache: bool, verbose: int):
    ctx.ensure_object(dict)
    basicConfig()
    if verbose == 1:
        logger.setLevel(INFO)
    elif verbose > 1:
        logger.setLevel(DEBUG)
    ctx.obj["from_cache"] = from_cache
    ctx.obj["api"] = API()
    ctx.obj["verbose"] = verbose
    if verbose > 2:
        for line in tabulate(ctx.obj["api"].cache.info().items()).split("\n"):
            logger.debug(f"{ line}")


@cli.group("artist")
@click.option("-i", "--id", type=click.INT, required=True, help="discogs artist id")
@click.pass_context
def artist(ctx, id: int):
    ctx.obj["artist"] = Artist(
        api=ctx.obj["api"],
        artist_id=id,
        verbosity=ctx.obj["verbose"],
        from_cache=ctx.obj["from_cache"],
    )


@artist.command()
@click.pass_context
def show_tracks(ctx):
    """Display details of artist tracks"""
    tracks_table = ctx.obj["artist"].tracks_report()
    print(tabulate(tracks_table[1:], headers=tracks_table[0]))


@artist.command()
@click.pass_context
@click.option("-s", "--for-sale", is_flag=True)
def show_completing(ctx, for_sale: bool):
    """Display details of records needed to complete the artist tracks collection"""
    artist = ctx.obj["artist"]
    artist.check_for_completing_records()
    record_table = artist.completing_records_report(for_sale=for_sale)
    print(tabulate(record_table[1:], headers=record_table[0]))


@artist.group("release")
@click.option("-i", "--id", type=click.INT, required=True, help="discogs release id")
@click.pass_context
def release(ctx, id: int):
    ctx.obj["record"] = ctx.obj["artist"].records[int(id)]


@release.command()
@click.pass_context
def show(ctx):
    record = ctx.obj["record"]
    print(record.url)
    pprint([(t, t.alternatives) for ts in record.tracks.values() for t in ts])


if __name__ == "__main__":
    cli()

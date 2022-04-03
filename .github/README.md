# Contributing

## Workflow

Github is used to share and contribute:

1. Create a new issue in [discogs-track/issues](https://github.com/decitre/discogs_track/issues)
2. Fork [decitre/discogs-track](https://github.com/decitre/discogs_track) repository
3. Git clone the forked repo
4. Create a development branch in the local repo, named after the issue #.
5. Install an editable version of the branched repo
```shell
$ pip install -e ".[dev]"
```
6. Do the code change
7. Commit with a message referring to the Issue # and summary
8. Push the change to the forked origin repo
9. Submit a new github [pull request](https://github.com/decitre/discogs_track/pulls)

## Hints

Use [`pre-commit`](https://pre-commit.com/#intro). `pre-commit` is part of the `dev` project extras.


# LastFM ↔ Discogs handshake

Scrobble an album from your Discogs collection to Last.fm. Two
interfaces, same underlying logic (`core.py`):

- **`app.py`** — a local browser-based GUI: searchable album grid with
  cover art, click an album to see its tracklist, one button to scrobble
- **`scrobble.py`** — a terminal-only CLI, if you prefer that

Both run entirely on your own machine. Nothing is hosted publicly.

## How it works

1. Fetches your Discogs collection (the "All" folder) via the Discogs API
2. You search/pick a release
3. Fetches that release's full tracklist from Discogs (lazy-loaded on
   demand, not for your whole collection up front)
4. Scrobbles each track to Last.fm, with timestamps spaced backward from
   now using each track's actual duration — so it looks like a normal,
   real listen ending now, not a burst of identical timestamps

## Setup

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

- `LASTFM_API_KEY` / `LASTFM_API_SECRET` — register an app at
  https://www.last.fm/api/account/create
- `DISCOGS_TOKEN` — generate a personal access token at
  https://www.discogs.com/settings/developers
- `DISCOGS_USERNAME` — your Discogs username

Then authorize once with Last.fm (opens a browser to approve access):

```
python3 auth_lastfm.py
```

This saves a session key to `.lastfm_session_key` (gitignored) that's
reused on every future run — you only need to do this once, unless you
revoke the app's access on Last.fm.

## Usage

### GUI (recommended)

```
source venv/bin/activate
python3 app.py
```

Opens `http://127.0.0.1:5000` in your browser automatically. Search or
browse the grid, click an album to see its tracklist, tick/untick "Dry
run" and click **Scrobble to Last.fm**.

### CLI

```
source venv/bin/activate
python3 scrobble.py
```

Search your collection, pick a release, review the tracklist, confirm.

To preview without submitting anything to Last.fm:

```
python3 scrobble.py --dry-run
```

## Notes

- Last.fm's guidelines discourage scrobbling music you didn't actually
  listen to. This tool is meant for logging physical/vinyl listens you
  actually had, not for inflating play counts — use it accordingly.
- Tracks without a Discogs-listed duration default to 3 minutes for
  timestamp spacing purposes.
- `.env` and `.lastfm_session_key` are gitignored — never commit them.

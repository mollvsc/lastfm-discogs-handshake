"""Shared Discogs <-> Last.fm logic used by both scrobble.py (CLI) and
app.py (local web GUI)."""
import os
import time

import pylast
import discogs_client
from dotenv import load_dotenv

SESSION_KEY_FILE = ".lastfm_session_key"
DEFAULT_TRACK_SECONDS = 180  # fallback when Discogs has no duration listed

load_dotenv()


class ConfigError(Exception):
    """Missing .env values or Last.fm session."""


def parse_duration(duration_str):
    """Discogs durations look like '3:45' or '1:02:30'; '' if unlisted."""
    if not duration_str:
        return DEFAULT_TRACK_SECONDS
    parts = duration_str.strip().split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return DEFAULT_TRACK_SECONDS
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds or DEFAULT_TRACK_SECONDS


def connect_discogs():
    token = os.environ.get("DISCOGS_TOKEN")
    username = os.environ.get("DISCOGS_USERNAME")
    if not token or not username:
        raise ConfigError("Set DISCOGS_TOKEN and DISCOGS_USERNAME in .env first.")
    d = discogs_client.Client("lastfm-discogs-handshake/1.0", user_token=token)
    return d.user(username)


def connect_lastfm():
    api_key = os.environ.get("LASTFM_API_KEY")
    api_secret = os.environ.get("LASTFM_API_SECRET")
    if not api_key or not api_secret:
        raise ConfigError("Set LASTFM_API_KEY and LASTFM_API_SECRET in .env first.")
    if not os.path.exists(SESSION_KEY_FILE):
        raise ConfigError("No Last.fm session found. Run `python3 auth_lastfm.py` first.")
    with open(SESSION_KEY_FILE) as f:
        session_key = f.read().strip()
    return pylast.LastFMNetwork(api_key=api_key, api_secret=api_secret, session_key=session_key)


def load_collection(user):
    """Returns a list of dicts, one per release in the "All" collection
    folder. Each dict keeps a reference to the live Release object (for
    later lazy-loading its tracklist), plus a stable id and thumbnail
    already available from Discogs' collection response."""
    folder = user.collection_folders[0]  # folder 0 = "All"
    items = []
    for item in folder.releases:
        release = item.release
        artist = ", ".join(a.name for a in release.artists) if release.artists else "Unknown Artist"
        items.append({
            "id": release.id,
            "artist": artist,
            "title": release.title,
            "year": release.year,
            "thumb": release.thumb,
            "release": release,
        })
    return items


def search_collection(items, query):
    if not query:
        return items
    q = query.lower()
    return [i for i in items if q in i["artist"].lower() or q in i["title"].lower()]


def build_tracks(release):
    """Fetches the release's full tracklist (triggers a lazy API call the
    first time, since collection listings only include basic info)."""
    tracks = []
    album_artist = ", ".join(a.name for a in release.artists) if release.artists else "Unknown Artist"
    for t in release.tracklist:
        if not t.title or t.fetch("type_", "track") != "track":
            continue  # skip headings/indexes that aren't actual tracks
        track_artist = ", ".join(a.name for a in t.artists) if t.artists else album_artist
        tracks.append({
            "artist": track_artist,
            "title": t.title,
            "duration": parse_duration(t.duration),
        })
    return tracks


def plan_scrobbles(tracks):
    """Assigns each track a timestamp, spaced backward from now using
    actual track durations, so the whole album appears to have just been
    listened to start-to-finish. Returns a new list of track dicts with a
    'timestamp' key added, in playback order."""
    total_duration = sum(t["duration"] for t in tracks)
    timestamp = int(time.time()) - total_duration
    planned = []
    for t in tracks:
        planned.append({**t, "timestamp": timestamp})
        timestamp += t["duration"]
    return planned


def submit_scrobbles(network, planned, album_title):
    """Actually submits each planned track to Last.fm."""
    for t in planned:
        network.scrobble(
            artist=t["artist"],
            title=t["title"],
            timestamp=t["timestamp"],
            album=album_title,
        )

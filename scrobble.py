#!/usr/bin/env python3
"""Scrobble an album from your Discogs collection to Last.fm.

Usage:
  python3 scrobble.py              # search your collection and scrobble
  python3 scrobble.py --dry-run    # preview the scrobble without submitting
"""
import os
import sys
import time
import argparse

import pylast
import discogs_client
from dotenv import load_dotenv

SESSION_KEY_FILE = ".lastfm_session_key"
DEFAULT_TRACK_SECONDS = 180  # fallback when Discogs has no duration listed

load_dotenv()


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
        print("Set DISCOGS_TOKEN and DISCOGS_USERNAME in .env first.", file=sys.stderr)
        sys.exit(1)
    d = discogs_client.Client("lastfm-discogs-handshake/1.0", user_token=token)
    return d.user(username)


def connect_lastfm():
    api_key = os.environ.get("LASTFM_API_KEY")
    api_secret = os.environ.get("LASTFM_API_SECRET")
    if not api_key or not api_secret:
        print("Set LASTFM_API_KEY and LASTFM_API_SECRET in .env first.", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(SESSION_KEY_FILE):
        print("No Last.fm session found. Run `python3 auth_lastfm.py` first.", file=sys.stderr)
        sys.exit(1)
    with open(SESSION_KEY_FILE) as f:
        session_key = f.read().strip()
    return pylast.LastFMNetwork(api_key=api_key, api_secret=api_secret, session_key=session_key)


def load_collection(user):
    print("Loading your Discogs collection (this can take a moment for large collections)...")
    folder = user.collection_folders[0]  # folder 0 = "All"
    items = []
    for item in folder.releases:
        release = item.release
        artist = ", ".join(a.name for a in release.artists) if release.artists else "Unknown Artist"
        items.append({"artist": artist, "title": release.title, "year": release.year, "release": release})
    print(f"Loaded {len(items)} releases.")
    return items


def search_collection(items, query):
    if not query:
        return items
    q = query.lower()
    return [i for i in items if q in i["artist"].lower() or q in i["title"].lower()]


def pick_release(matches):
    for idx, item in enumerate(matches, 1):
        year = f" ({item['year']})" if item.get("year") else ""
        print(f"  {idx}. {item['artist']} - {item['title']}{year}")
    while True:
        choice = input("\nPick a number (or 'q' to quit): ").strip()
        if choice.lower() == "q":
            sys.exit(0)
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            return matches[int(choice) - 1]
        print("Invalid choice, try again.")


def build_tracks(release):
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


def scrobble_tracks(network, tracks, album_title, dry_run):
    total_duration = sum(t["duration"] for t in tracks)
    start_time = int(time.time()) - total_duration

    print(f"\n{'Would scrobble' if dry_run else 'Scrobbling'} {len(tracks)} tracks from \"{album_title}\":\n")
    timestamp = start_time
    for t in tracks:
        when = time.strftime("%H:%M:%S", time.localtime(timestamp))
        print(f"  [{when}] {t['artist']} - {t['title']} ({t['duration']}s)")
        if not dry_run:
            network.scrobble(
                artist=t["artist"],
                title=t["title"],
                timestamp=timestamp,
                album=album_title,
            )
        timestamp += t["duration"]

    if dry_run:
        print("\nDry run only -- nothing was submitted to Last.fm.")
    else:
        print("\nDone -- scrobbled to Last.fm.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="preview without submitting to Last.fm")
    args = parser.parse_args()

    discogs_user = connect_discogs()
    lastfm_network = None if args.dry_run else connect_lastfm()

    items = load_collection(discogs_user)

    query = input("\nSearch your collection (artist or album, blank for all): ").strip()
    matches = search_collection(items, query)
    if not matches:
        print("No matches found.")
        sys.exit(0)

    chosen = pick_release(matches)
    release = chosen["release"]
    album_title = f"{chosen['artist']} - {chosen['title']}"

    tracks = build_tracks(release)
    if not tracks:
        print("No tracks found on this release.")
        sys.exit(0)

    print(f"\nFound {len(tracks)} tracks on \"{chosen['title']}\":")
    for t in tracks:
        print(f"  - {t['artist']} - {t['title']} ({t['duration']}s)")

    if not args.dry_run:
        confirm = input(f"\nScrobble all {len(tracks)} tracks to Last.fm now? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            sys.exit(0)

    scrobble_tracks(lastfm_network, tracks, chosen["title"], args.dry_run)


if __name__ == "__main__":
    main()

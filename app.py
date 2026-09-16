#!/usr/bin/env python3
"""Local web GUI for scrobbling albums from your Discogs collection to
Last.fm. Runs entirely on your own machine -- nothing is hosted publicly.

Usage:
  python3 app.py
  then open http://127.0.0.1:5000 in your browser (opens automatically)
"""
import sys
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request

import core

app = Flask(__name__)

# Populated once at startup; a personal single-user local tool doesn't need
# per-request reloading or multi-user cache invalidation.
_collection = []
_discogs_user = None


def _find_by_id(release_id):
    for item in _collection:
        if item["id"] == release_id:
            return item
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/collection")
def api_collection():
    return jsonify([
        {"id": i["id"], "artist": i["artist"], "title": i["title"], "year": i["year"], "thumb": i["thumb"]}
        for i in _collection
    ])


@app.route("/api/release/<int:release_id>")
def api_release(release_id):
    item = _find_by_id(release_id)
    if item is None:
        return jsonify({"error": "Release not found in your collection."}), 404
    tracks = core.build_tracks(item["release"])
    return jsonify({
        "id": item["id"],
        "artist": item["artist"],
        "title": item["title"],
        "tracks": tracks,
    })


@app.route("/api/scrobble", methods=["POST"])
def api_scrobble():
    data = request.get_json(force=True)
    release_id = data.get("release_id")
    dry_run = bool(data.get("dry_run"))

    item = _find_by_id(release_id)
    if item is None:
        return jsonify({"error": "Release not found in your collection."}), 404

    tracks = core.build_tracks(item["release"])
    if not tracks:
        return jsonify({"error": "No tracks found on this release."}), 400

    planned = core.plan_scrobbles(tracks)

    if not dry_run:
        try:
            network = core.connect_lastfm()
        except core.ConfigError as e:
            return jsonify({"error": str(e)}), 400
        core.submit_scrobbles(network, planned, item["title"])

    return jsonify({"ok": True, "dry_run": dry_run, "planned": planned})


def main():
    global _collection, _discogs_user

    try:
        _discogs_user = core.connect_discogs()
    except core.ConfigError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print("Loading your Discogs collection (this can take a moment for large collections)...")
    _collection = core.load_collection(_discogs_user)
    print(f"Loaded {len(_collection)} releases.")

    url = "http://127.0.0.1:5000"
    print(f"\nStarting local server at {url} (opening in your browser)...")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()

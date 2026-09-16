#!/usr/bin/env python3
"""One-time Last.fm authorization: obtains a session key via the web auth
flow and saves it locally so scrobble.py doesn't need your password.

Run once: python3 auth_lastfm.py
"""
import os
import sys
import webbrowser

import pylast

from core import SESSION_KEY_FILE  # also triggers core's load_dotenv()


def main():
    api_key = os.environ.get("LASTFM_API_KEY")
    api_secret = os.environ.get("LASTFM_API_SECRET")
    if not api_key or not api_secret:
        print("Set LASTFM_API_KEY and LASTFM_API_SECRET in .env first.", file=sys.stderr)
        sys.exit(1)

    network = pylast.LastFMNetwork(api_key=api_key, api_secret=api_secret)
    skg = pylast.SessionKeyGenerator(network)
    auth_url = skg.get_web_auth_url()

    print("Opening your browser to authorize this app with Last.fm...")
    print(f"If it doesn't open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)
    input("Press Enter once you've clicked 'Allow Access' on the Last.fm page...")

    session_key = skg.get_web_auth_session_key(auth_url)
    with open(SESSION_KEY_FILE, "w") as f:
        f.write(session_key)

    print(f"\nDone. Session key saved to {SESSION_KEY_FILE}.")


if __name__ == "__main__":
    main()

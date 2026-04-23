import requests
import csv
import sys
import json
import os
from dotenv import load_dotenv

# -------------------------------
# CONFIGURATION
# -------------------------------
load_dotenv()
USERNAME = os.getenv('LISTEN_USER')
USER_TOKEN = os.getenv('API_KEY')  # Get from https://listenbrainz.org/profile/
OUTPUT_FILE = "listen_history.csv"
LIMIT = 100  # Max per request (ListenBrainz API limit)
# -------------------------------

API_URL = f"https://api.listenbrainz.org/1/user/{USERNAME}/listens"

def fetch_listens(username, token, limit=100):
    """Fetch all listens for a user from ListenBrainz API."""
    listens = []
    offset = 0

    headers = {"Authorization": f"Token {token}"}

    while True:
        params = {"count": limit, "offset": offset}
        try:
            resp = requests.get(API_URL, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching listens: {e}")
            sys.exit(1)

        data = resp.json()
        batch = data.get("payload", {}).get("listens", [])
        if not batch:
            break

        listens.extend(batch)
        offset += limit

    return listens

def save_to_csv(listens, filename):
    """Save listens to CSV file."""
    with open(filename, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # CSV header
        writer.writerow(["artist", "track", "release", "listened_at"])

        for listen in listens:
            track_meta = listen.get("track_metadata", {})
            artist = track_meta.get("artist_name", "")
            track = track_meta.get("track_name", "")
            release = track_meta.get("release_name", "")
            listened_at = listen.get("listened_at", "")
            writer.writerow([artist, track, release, listened_at])

if __name__ == "__main__":
    all_listens = fetch_listens(USERNAME, USER_TOKEN, LIMIT)
    save_to_csv(all_listens, OUTPUT_FILE)
    print(f"Exported {len(all_listens)} listens to {OUTPUT_FILE}")

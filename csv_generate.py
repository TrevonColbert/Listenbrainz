import requests
import csv
import sys
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# -------------------------------
# CONFIGURATION
# -------------------------------
load_dotenv()
USERNAME = os.getenv('LISTEN_USER') # User retreiving listen history for
USER_TOKEN = os.getenv('API_KEY')  # Get from https://listenbrainz.org/profile/
OUTPUT_FILE = "listen_history.csv"
AUTH_HEADER = {"Authorization": f"Token {USER_TOKEN}"}
# -------------------------------

#TODO Function using Pandas, to remove duplicates created due to needing to use insterted_at instead of listened_at
#TODO Use Pandas df.to_csv to replace save_to_csv function

def get_listens(username, max_ts=None, count=None):

    """Gets the listen history of a given user.

    Args:
        username: User to get listen history of.
        min_ts: History before this timestamp will not be returned.
                DO NOT USE WITH max_ts.
        max_ts: History after this timestamp will not be returned.
                DO NOT USE WITH min_ts.
        count: How many listens to return. If not specified,
               uses a default from the server.

    Returns:
        A list of listen info dictionaries if there's an OK status.

    Raises:
        An HTTPError if there's a failure.
        A ValueError if the JSON in the response is invalid.
        An IndexError if the JSON is not structured as expected.
    """

    #Loop until count from JSON response <> count set
    json_output = []
    while True:
        response = requests.get(
            url=f"https://api.listenbrainz.org/1/user/{USERNAME}/listens",
            params={
                "max_ts": max_ts,
                "count": count,
            },

            headers=AUTH_HEADER,
        )
        response.raise_for_status()
        max_ts = response.json()["payload"]["listens"][-1]["inserted_at"] #Set max_ts to last song insterted_at
        json_output += response.json()["payload"]["listens"]
        if response.json()["payload"]["count"]!=count:
            break

    return json_output



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
            listened_at = datetime.fromtimestamp(listen.get("listened_at", ""))
            writer.writerow([artist, track, release, listened_at])

if __name__ == "__main__":
    listens = get_listens(
        USER_TOKEN, None, 1000)  # count=1000 is maximum listens to pull in 1 request

    save_to_csv(listens, OUTPUT_FILE)
    print(f"Exported {len(listens)} listens to {OUTPUT_FILE}")

import requests
import sys
import json
import os
from dotenv import load_dotenv
import pandas as pd

# -------------------------------
# CONFIGURATION
# -------------------------------
load_dotenv()
USERNAME = os.getenv("LISTEN_USER")  # User retreiving listen history for
USER_TOKEN = os.getenv("API_KEY")  # Get from https://listenbrainz.org/profile/
OUTPUT_FILE = "listen_history.csv"
AUTH_HEADER = {"Authorization": f"Token {USER_TOKEN}"}
# -------------------------------

# TODO Update get_genre to iterate 1000 tracks at a time since this is the maximum allowed by the API
# TODO get_genre dataframe to csv
# TODO create an artists table for each track


def get_listens(username, max_ts=None, count=None):
    """
    Gets the listen history of a given user.

    Args:
        username: User to get listen history of.
        min_ts: History before this timestamp will not be returned. (Not used in function but part of API)
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

    # Loop until count from JSON response <> count set
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
        max_ts = response.json()["payload"]["listens"][-1][
            "inserted_at"
        ]  # Set max_ts to last song inserted_at
        json_output += response.json()["payload"]["listens"]
        if response.json()["payload"]["count"] != count:
            break

    return json_output


def listens_cleanup(listens, filename=OUTPUT_FILE):
    """
    Normalizes/flattens listens JSON to a pandas dataframe
    Removes duplicates based on listened_at timestamp & recording_msid
    Generates user listen history csv

    Args:
        listens: json list supplied by get_listens function
        filename: filename to use for csv, uses OUTPUT_FILE by default (defined in configuration)

    Returns:
        dataframe of listens history
        Generates csv
    """

    df = pd.DataFrame(pd.json_normalize(listens))
    df = df.drop_duplicates(subset=["listened_at", "recording_msid"]).reset_index(
        drop=True
    )
    timestamp_cols = ["inserted_at", "listened_at"]
    df[timestamp_cols] = df[timestamp_cols].apply(pd.to_datetime, unit="s")
    df.to_csv(filename, index=True)

    return df


def get_genre(df):
    """
    Gets genre for each recording_mbid in dataframe

    Args:
        df: dataframe of listens history (provided by listens_cleanup function)

    Returns:
        dataframe of recording_mbids & genres
    """

    df = df[["track_metadata.mbid_mapping.recording_mbid"]]
    df = df.drop_duplicates().dropna()
    recordings_list = df["track_metadata.mbid_mapping.recording_mbid"].to_list()

    response = requests.post(
        url=f"https://api.listenbrainz.org/1/metadata/recording/",
        json={
            "recording_mbids": recordings_list,
            "inc": "tag",
        },
        headers=AUTH_HEADER,
    )

    df = response.json()

    track_genres = []
    for track in df:
        genres = df[track]["tag"]["artist"]
        all_genres = []
        for genre in genres:
            all_genres.append(genre["tag"])
        track_genres.append({"recording_mbid": track, "genres": all_genres})
    track_genres_df = pd.DataFrame(track_genres)

    return track_genres_df


if __name__ == "__main__":
    listens = get_listens(
        USER_TOKEN, None, 1000
    )  # count=1000 is maximum listens to pull in 1 request
    listens_df = listens_cleanup(listens, OUTPUT_FILE)
    get_genre(listens_df)
    print(f"Exported {len(listens_df)} listens to {OUTPUT_FILE}")


import requests
import csv
import sys
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

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
        max_ts = response.json()["payload"]["listens"][-1]["inserted_at"] #Set max_ts to last song inserted_at
        json_output += response.json()["payload"]["listens"]
        if response.json()["payload"]["count"]!=count:
            break

    return json_output

def listens_to_csv(listens, filename=OUTPUT_FILE):

    '''
    Normalizes/flattens listens JSON to a pandas dataframe 
    Removes duplicates based on listened_at timestamp & recording_msid 
    Generates user listen history csv

    Args:
        listens: json list supplied by get_listens function
        filename: filename to use for csv, uses OUTPUT_FILE by default (defined in configuration)
    
    Returns:
        dataframe of listens history
        Generates csv
    '''

    df = pd.DataFrame(pd.json_normalize(listens))
    df = df.drop_duplicates(subset=["listened_at", "recording_msid"]).reset_index(drop=True)
    df.to_csv(filename, index=True)

    return df

if __name__ == "__main__":
    listens = get_listens(
        USER_TOKEN, None, 1000)  # count=1000 is maximum listens to pull in 1 request

    listens_csv_df = listens_to_csv(listens,OUTPUT_FILE)
    print(f"Exported {len(listens_csv_df)} listens to {OUTPUT_FILE}")

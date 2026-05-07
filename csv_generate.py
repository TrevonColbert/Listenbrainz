import requests
import os
import time
from dotenv import load_dotenv
import pandas as pd

# -------------------------------
# CONFIGURATION
# -------------------------------
load_dotenv()
USERNAME = os.getenv('LISTEN_USER')  # User retreiving listen history for
USER_TOKEN = os.getenv('API_KEY')  # Get from https://listenbrainz.org/profile/
OUTPUT_FILE = 'listen_history.csv'
GENRES_FILE = 'genres.csv'
ARTISTS_FILE = 'artists.csv'
AUTH_HEADER = {'Authorization': f'Token {USER_TOKEN}'}
# -------------------------------


def get_listens(username, max_ts=None, count=1000,sleep=.5):
    '''
    Gets the listen history of a given user.

    Args:
        username: User to get listen history of.
        max_ts: History after this timestamp will not be returned.
                DO NOT USE WITH min_ts.
        count: How many listens to return. If not specified,
               uses a default from the server.
        sleep: time to sleep between requests, prevent rate limiting

    Returns:
        A list of listen info dictionaries if there's an OK status.

    Raises:
        An HTTPError if there's a failure.
        A ValueError if the JSON in the response is invalid.
        An IndexError if the JSON is not structured as expected.
    '''

    # Loop until count from JSON response <> count set
    json_output = []
    while True:
        response = requests.get(
            url=f'https://api.listenbrainz.org/1/user/{USERNAME}/listens',
            params={
                'max_ts': max_ts,
                'count': count,
            },
            headers=AUTH_HEADER,
        )
        response.raise_for_status()
        previous_max_ts = max_ts
        max_ts = response.json()['payload']['listens'][-1]['inserted_at']  # Set max_ts to last song inserted_at
        if previous_max_ts == max_ts:
            max_ts = response.json()['payload']['listens'][-1]['listened_at'] #Changes to listened_at for when a mass import occurs
        json_output += response.json()['payload']['listens']
        time.sleep(sleep)
        if response.json()['payload']['count'] != count:
            break
    return json_output


def listens_cleanup(listens, filename=OUTPUT_FILE):
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
    df = df.drop_duplicates(subset=['listened_at', 'recording_msid']).reset_index(
        drop=True
    )
    timestamp_cols = ['inserted_at', 'listened_at']
    df[timestamp_cols] = df[timestamp_cols].apply(lambda s: pd.to_datetime(s, unit='s', utc=True).dt.tz_convert('US/Eastern')) #Convert Epoch to EST timestamps
    df.to_csv(filename, index=True)

    return df


def get_genre(df,filename):
    '''
    Gets genre for each recording_mbid in dataframe

    Args:
        df: dataframe of listens history (provided by listens_cleanup function)

    Returns:
        dataframe of recording_mbids & genres
        Generates csv
    '''
    
    track_genres = []
    df = df[['track_metadata.mbid_mapping.recording_mbid']]
    df = df.drop_duplicates().dropna()
    recordings_list = df['track_metadata.mbid_mapping.recording_mbid'].to_list()
    chunks = len(recordings_list)//1000 #Number of chunks of 1000 to iterate through (1000 is max items allowed by API)
    
    for i in range(0,chunks+1):
        response = requests.post(
            url=f'https://api.listenbrainz.org/1/metadata/recording/',
            json={
                'recording_mbids': recordings_list[i*1000:(i+1)*1000],
                'inc': 'tag',
            },
            headers=AUTH_HEADER,
        )
        df = response.json()

        for track in df:
            track_data = df[track]
            all_genres = []
            for genre in track_data['tag']['artist']:
                    all_genres.append(genre['tag'])
            track_genres.append({'recording_mbid': track, 'genres': all_genres})

    track_genres_df = pd.DataFrame(track_genres)
    track_genres_df = track_genres_df.explode('genres')
    track_genres_df.to_csv(filename, index=True)

    return track_genres_df


# Function to extract all occurrences between delimiters for artist_credit_name
def extract_artists(lst):
    if not isinstance(lst, list):  # Handle NaN or non-list values
        return []
    results = []
    for item in lst:
        results.append(item['artist_credit_name'])
    return results


def get_artists(df,filename=ARTISTS_FILE):
    '''
    Creates artists table for each listen in dataframe using mbid

    Args:
        df: dataframe of listens history (provided by listens_cleanup function)
        filename: filename to use for csv, uses ARTISTS_FILE by default (defined in configuration)

    Returns:
        dataframe of recording_msid, recording_mbid, artists, collab, full_artists, full_track_name
        Generates csv
    '''
    df = df.drop_duplicates(subset=['recording_msid']).reset_index(drop=True)
    df['artists'] = df['track_metadata.mbid_mapping.artists'].apply(lambda x: extract_artists(x))
    df['collab'] = df['track_metadata.mbid_mapping.artists'].apply(lambda x: extract_artists_collab(x))
    df['full_artists'] = df.apply(lambda row: full_artists(row['artists'], row['collab']), axis=1)
    df['full_track_name'] = df.apply(lambda row: full_track(row['track_metadata.mbid_mapping.recording_name'],row['full_artists'], row['track_metadata.track_name'], row['track_metadata.artist_name']), axis=1)
    df = df.explode('artists')
    columns_to_keep = ['recording_msid','track_metadata.mbid_mapping.recording_mbid','artists','full_artists','full_track_name']
    df = df[columns_to_keep]
    df.to_csv(filename, index=True)
    return df

    
# Function to extract all occurrences between delimiters for join_phrase
def extract_artists_collab(lst):
    if not isinstance(lst, list):  # Handle NaN or non-list values
        return []
    results = []
    for item in lst:
        results.append(item['join_phrase'])
    return results

    
#Function to combine artists and collab into a single string
def full_artists(artists,collab):
    results = []
    if not isinstance(artists, list):  # Handle NaN or non-list values
        return ''
    if len(artists) == 1:
        return artists[0]
    for i in range(len(artists)):
        results.append(artists[i])
        results.append(collab[i])
    output = ' '.join(results)
    return output


#Function to combine full artists and track name into a single string
def full_track(track,artists,backup_track,backup_artists):
    if artists == '':
        full_track = f'{backup_track} - {backup_artists}'
        return full_track
    full_track = f'{track} - {artists}'
    return full_track


if __name__ == "__main__":
    listens = get_listens(
        USER_TOKEN, None, 1000
    )  # count=1000 is maximum listens to pull in 1 request

    listens_df = listens_cleanup(listens, OUTPUT_FILE)
    get_genre(listens_df,GENRES_FILE)
    get_artists(listens_df,ARTISTS_FILE)
    print(f'Exported {len(listens_df)} listens to {OUTPUT_FILE}')
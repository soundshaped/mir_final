import json
import requests
import os
import pandas as pd
import numpy as pd
import librosa
from mutagen.mp3 import MP3
import zipfile #might not use this
import time

def search_release(api_key, api_secret, artist_name, release_title):
    search_url = 'https://api.discogs.com/database/search'
    params = {
        'release_title': release_title,
        'artist': artist_name,
        'type': 'release'
    }
    headers = {
        'Authorization': f'Discogs key={api_key}, secret={api_secret}',
        'User-Agent': 'YourAppName/1.0'  # Replace with your app name and version
    }
    response = requests.get(search_url, headers=headers, params=params)
    return response.json()

def get_release_id(search_results):
    return search_results.get('results', [{}])[0].get('id')

def read_tags(file_path):
    """
    returns: dict with the following values if the file has relevant metadata
    {
    "artist": 'name',
    "album": 'title',
    "year": "year of release xxxx",
    'genre': 'genre if file is tagged with a genre',
    "label": "label assuming label is tagged as 'TCOP' in the MP3 metadata, some use 'TPUB'",
    "title": "track title"
    }
    """
    
    audio = MP3(file_path)
    tags = {
        'artist': None,
        'album': None,
        'year': None,
        'genre': None,
        'label': None,
        'title': None
    }

    # Directly iterate over tags
    # works for label *if* label is tagged in the metadata under copyright rather than `TPUB`
    for tag, value in audio.items():
        if tag.startswith('TPE1'):
            tags['artist'] = str(value)
        elif tag.startswith('TALB'):
            tags['album'] = str(value)
        elif tag.startswith('TDRC'):
            tags['year'] = str(value)
        elif tag.startswith('TCON'):
            tags['genre'] = str(value)
        elif tag.startswith('TCOP'):
            tags['label'] = str(value)
        elif tag.startswith('TIT2'):
            tags['title'] = str(value)

    return tags

def process_files(folder_path, default_label=None):
    data = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.mp3'):
                # Full path to the file so i can create the dfs and then process audio features separately
                full_file_path = os.path.join(root, file)

                tags = read_tags(full_file_path)

                # Use the label from the tags if available, otherwise use the default label
                label = tags['label'] if tags['label'] else default_label

                data.append({
                    "title": tags['title'],
                    "artist": tags['artist'],
                    "album": tags['album'],
                    "year": tags['year'],
                    "genre": tags['genre'],
                    "label": label,
                    "file_path": full_file_path
                })

    return pd.DataFrame(data)

def extract_features(file_path):
    """
    very basic tempo and timbre to vector analysis at the moment while i hobble together something
    Params:
    path of audio file, readable by librosa

    Returns:
    dict: keys tempo and timbre (as a vector)
    """
    y, sr = librosa.load(file_path)

    # Extract features you are interested in
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    timbre = librosa.feature.mfcc(y=y, sr=sr)

    # Other features...

    return {
        "tempo": tempo,
        "timbre": timbre.mean(axis=1)
    }
    
######
# Funcs for scraping genre information 
#####

def load_credentials(file_path):
    with open(file_path, 'r') as file:
        credentials = json.load(file)
        api_key = credentials['api_key']
        api_secret = credentials['api_secret']
        return credentials

def make_request_with_rate_limiting(url, headers, **kwargs):
    response = requests.get(url, headers=headers, **kwargs)

    if response.status_code == 429: 
        retry_after = int(response.headers.get('Retry-After', 60)) 
        print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
        return make_request_with_rate_limiting(url, headers)  # wait then call
    elif response.status_code == 200:
        remaining = int(response.headers.get('X-Discogs-Ratelimit-Remaining', 0))
        if remaining < 10:  # why not 10 left
            print(f"Approaching rate limit. Remaining requests: {remaining}. Pausing briefly.")
            time.sleep(10)  # Pause for 10 seconds
    return response

def search_release(api_key, api_secret, artist_name, track_title=None, release_title=None, year=None):
    search_url = 'https://api.discogs.com/database/search'
    params = {
        'release_title': release_title,
        'artist': artist_name,
        'type': 'release',
    }
    if year:
        params['year'] = year
    if track_title:
        params['track'] = track_title

    headers = {
        'Authorization': f'Discogs key={api_key}, secret={api_secret}',
        'User-Agent': 'YourAppName/1.0'
    }
    response = make_request_with_rate_limiting(search_url, headers, params=params)

    if response and response.status_code == 200:
        search_results = response.json()
        results = search_results.get('results', [])
        if not results:
            print(f"No results found for {artist_name} - {release_title} - {track_title}")
            return None
        return search_results
    else:
        print(f"Error in search: {response.status_code}")
        return None



def get_release_id(search_results):
    return search_results.get('results', [{}])[0].get('id')

def get_release_details(api_key, api_secret, release_id):
    url = f'https://api.discogs.com/releases/{release_id}'
    headers = {
        'Authorization': f'Discogs key={api_key}, secret={api_secret}',
        'User-Agent': 'YourAppName/1.0'
    }
    response = make_request_with_rate_limiting(url, headers)

    if response and response.status_code == 200:
        release_data = response.json()
        genres = release_data.get("genres", [])
        styles = release_data.get('styles', [])
        return genres, styles
    return [], []

# fill in genre info for dfs
def process_dataframe(df, creds):
    for index, row in df.iterrows():
        # search by release bc discogs doesn't do per track genre
        search_results = search_release(
            creds['api_key'],
            creds['api_secret'],
            artist_name=row['artist'],
            release_title=row.get('album'),  
            year=row.get('year')  # Using .get() in case 'year' column might be missing
        )

        if search_results:
            release_id = get_release_id(search_results)
            if release_id:
                # Fetch genres and styles for this release ID
                genres, styles = get_release_details(creds['api_key'], creds['api_secret'], release_id)
                # Update the DataFrame with the genres and styles
                df.at[index, 'genres'] = ', '.join(genres)
                df.at[index, 'styles'] = ', '.join(styles)
            else:
                df.at[index, 'genres'] = 'Not Found'
                df.at[index, 'styles'] = 'Not Found'
        else:
            df.at[index, 'genres'] = 'Search Failed'
            df.at[index, 'styles'] = 'Search Failed'
    
    return df

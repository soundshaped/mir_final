import os
from mutagen.mp3 import MP3
import pandas as pd

def read_tags(file_path):
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
                # Full path to the file
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

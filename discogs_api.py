import discogs_client #spent way too long not using this
from requests.exceptions import HTTPError

def get_discogs_client():
    d = discogs_client.Client("genre_style/1.0", user_token="aIrVvUyIOehkEODaVUkFSWtyCElILnQcYqLQCFvE")

    # d.set_token()
    return d

def get_release_details(discogs_client, release_id):
    try:
        release = discogs_client.release(release_id)
        genres = release.genres if hasattr(release, 'genres') else []
        styles = release.styles if hasattr(release, 'styles') else []
        return genres, styles
    except HTTPError as e:
        print(f"HTTP Error for release ID {release_id}: {e}")
        return [], []
    except Exception as e:
        print(f"General Error for release ID {release_id}: {e}")
        return [], []


def search_release(discogs_client, artist_name=None, track_title=None, release_title=None, year=None, catno=None):
    search_params = {
        'artist': artist_name,
        'track': track_title,
        'release_title': release_title,
        'year': year,
        'catno': catno
    }

    # Filter out None values
    search_params = {k: v for k, v in search_params.items() if v is not None}

    results = discogs_client.search(type='release', **search_params)
    return results

def find_label_id(discogs_client, label_name):
    results = discogs_client.search(label_name, type='label')
    if results.count > 0:
        return results[0].id
    return None

def get_label_discography(discogs_client, label_id):
    label = discogs_client.label(label_id)
    all_releases = []

    # Process the first page
    for release in label.releases.page(1):
        all_releases.append({
            'id': release.id,
            'title': release.title,
            'year': release.year
        })

    # Handling pagination - check if there are more pages
    if label.releases.pages > 1:
        for page in range(2, label.releases.pages + 1):
            for release in label.releases.page(page):
                all_releases.append({
                    'id': release.id,
                    'title': release.title,
                    'year': release.year
                })

    return all_releases

def generate_simplified_title_variations(release_title):
    # Common terms to be removed
    terms_to_remove = ["EP", "Album", "LP"]

    # Split the title by '/' and take the first part
    first_part = release_title.split('/')[0].strip()

    # Generate variations
    variations = set([first_part])

    # Remove additional descriptors like "(Version)" from the first part
    clean_first_part = re.sub(r'\(.*\)', '', first_part).strip()
    variations.add(clean_first_part)

    # Further remove common terms from the clean first part
    words = clean_first_part.split()
    for term in terms_to_remove:
        if term in words:
            new_title = ' '.join(word for word in words if word != term)
            variations.add(new_title)

    return variations

#trying to process only once per discogs/release_id

def process_dataframe(df, discogs_client):
    # Keeping track of processed IDs to avoid duplicate searches
    processed_ids = {}

    # Iterate over unique discogs_ids (release_ids)
    # for discogs, "genre" is very broad so i think all of this music is genrewise
    # "electronica", style is where the meat of differentiation is.
    for discogs_id in df['discogs_id'].unique():
        if discogs_id in processed_ids:
            genres, styles = processed_ids[discogs_id]
        else:
            genres, styles = get_release_details(discogs_client, discogs_id)
            genre_str = ', '.join(genres) if genres else 'Not Found'
            style_str = ', '.join(styles) if styles else 'Not Found'

            processed_ids[discogs_id] = (genre_str, style_str)

        df.loc[df['discogs_id'] == discogs_id, 'genres'] = genre_str
        df.loc[df['discogs_id'] == discogs_id, 'styles'] = style_str

    return df

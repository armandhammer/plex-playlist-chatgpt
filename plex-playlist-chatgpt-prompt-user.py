# This script facilitates reading a list of tracks from a text file,
# then adds those tracks to a playlist on the Plex server.

# More specifically:
# 1) it prompts for which Plex account to add the playlist to
# 2) it prompts for a name for the new playlist
# 3) it reads a text file which has a list of songs in the format ARTIST - TRACK
# with one song per line. It then searches the local Plex library for matching tracks
# and if those tracks are found, it adds them to the playlist. If no local tracks are found,
# it uses the defined PLACEHOLDER_ARTIST and PLACEHOLDER_TRACK in order to create the 
# playlist (it deletes this track later, before adding it to Plex). It then searches for
# missing tracks on Tidal, then appends those tracks to the playlist. During the search
# it excludes results which the track or album name includes a date format, e.g.
# YYYY-MM-DD or the words 'live', 'concert', or 'sbd' because I don't want live versions
# of songs in my playlists.


from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
import requests
from xml.etree import ElementTree as ET
from urllib.parse import quote
import re
from unidecode import unidecode
from fuzzywuzzy import fuzz



# Define constants
PLEX_URL = 'http://XXX.XXX.X.XXX:32400'  # Enter your server IP
PLEX_TOKEN = '[YOUR TOKEN]'
SECTION_TITLE = 'Music'     # The name of your music library
FILENAME = 'playlist.txt'   # The text file with the list of ARTIST - TRACK
ADMIN_NAME = '[ADMIN NAME]' # Enter your admin name in single quotes
ADMIN_PASS = '[ADMIN PASS]' # Enter your admin password in single quotes
FUZZ_AMT = 50               # Amount of fuzzy track matching

BATCH_SIZE = 20
PLACEHOLDER_ARTIST = 'LCD Soundsystem'    #edit with an artist and track in your local Plex library
PLACEHOLDER_TITLE = 'Dance Yrself Clean'


def initialize_plex_server(plex_url: str, plex_token: str) -> PlexServer:
    try:
        return PlexServer(plex_url, plex_token)
    except Exception as e:
        print(f"Error initializing Plex Server: {e}")
        exit()


def get_music_library(plex: PlexServer, section_title: str):
    try:
        return plex.library.section(section_title)
    except Exception as e:
        print(f"Error accessing section by Title: {e}")
        exit()


def read_songs_from_file(filename: str) -> list:
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file if ' - ' in line]
    except FileNotFoundError:
        print(f"Error: '{filename}' not found.")
        exit()


def simplify_string(input_string: str) -> str:
    input_string = input_string.lower()
    input_string = re.sub(r"[^\w\s]", "", input_string)
    input_string = unidecode(input_string)
    return input_string


def alternate_name_variation(artist_name: str) -> str:
    if " and " in artist_name:
        return artist_name.replace(" and ", " & ")
    elif " & " in artist_name:
        return artist_name.replace(" & ", " and ")
    else:
        return artist_name
        
        
def find_track_in_library(music_library, artist_name: str, track_title: str):
    artist_search = music_library.search(title=artist_name)
    for artist in artist_search:
        simplified_input_artist = simplify_string(artist_name)
        simplified_library_artist = simplify_string(artist.title)
        if fuzz.ratio(simplified_input_artist, simplified_library_artist) > FUZZ_AMT:
            for album in artist.albums():
                date_pattern = r'\d{4}[-\u2013\u2014\u2212/]\d{2}[-\u2013\u2014\u2212/]\d{2}|\d{2}[-\u2013\u2014\u2212/]\d{2}[-\u2013\u2014\u2212/]\d{4}'
                exclude_pattern = r'\b(?:live|concert|sbd)\b'
                is_date = re.search(date_pattern, album.title, re.IGNORECASE)
                is_exclude_word = re.search(exclude_pattern, album.title, re.IGNORECASE)
                
                if not is_date and not is_exclude_word:
                    for track in album.tracks():
                        is_track_exclude_word = re.search(exclude_pattern, track.title, re.IGNORECASE)
                        if is_track_exclude_word:
                            continue
                        
                        simplified_input_title = simplify_string(track_title)
                        simplified_library_title = simplify_string(track.title)
                        
                        if fuzz.ratio(simplified_input_title, simplified_library_title) > FUZZ_AMT:
                            return track
    return None


def search_tidal(plex_token: str, artist: str, title: str):
    date_pattern = r'\d{4}[-\u2013\u2014\u2212/]\d{2}[-\u2013\u2014\u2212/]\d{2}|\d{2}[-\u2013\u2014\u2212/]\d{2}[-\u2013\u2014\u2212/]\d{4}'
    exclude_keywords = ['live', 'concert', 'sbd']
    query = f"{artist} {title}"
    url = f"https://music.provider.plex.tv/hubs/search?query={quote(query)}&X-Plex-Token={plex_token}"

    response = requests.get(url)
    print(url)
    if response.status_code != 200:
        print(f"Error: Unable to search Tidal: {response.status_code}")
        return None

    tree = ET.ElementTree(ET.fromstring(response.text))
    track_hub = tree.find('./Hub[@type="track"]')

    if track_hub is not None:
        for track in track_hub.findall('./Track'):
            artist_title = track.get('grandparentTitle')
            track_title = track.get('title')
            album_title = track.get('parentTitle')

            if re.search(date_pattern, album_title) or re.search(date_pattern, track_title) or any(
                keyword.lower() in track_title.lower() or keyword.lower() in album_title.lower()
                for keyword in exclude_keywords
            ):
                continue

            simplified_input_artist = simplify_string(artist)
            simplified_input_title = simplify_string(title)
            simplified_library_artist = simplify_string(artist_title)
            simplified_library_title = simplify_string(track_title)

            if fuzz.ratio(simplified_input_artist, simplified_library_artist) > FUZZ_AMT and \
               fuzz.ratio(simplified_input_title, simplified_library_title) > FUZZ_AMT:  # Threshold can be adjusted
                tidal_id = track.get('guid').split('/')[-1]
                if tidal_id:
                    return tidal_id
    return None


def add_track_to_playlist(plex_url: str, plex_token: str, tidal_ids: list, playlist_ratingKey: str):
    if not tidal_ids:
        print("Cannot add tracks to a playlist with no Tidal IDs.")
        return
    
    for i in range(0, len(tidal_ids), BATCH_SIZE):
        batch_ids = tidal_ids[i:i + BATCH_SIZE]
        tidal_id_str = "%2C".join(batch_ids)
        add_to_playlist_url = f"{plex_url}/playlists/{playlist_ratingKey}/items?uri=provider%3A%2F%2Ftv.plex.provider.music%2Flibrary%2Fmetadata%2F{tidal_id_str}"
        
        response = requests.put(add_to_playlist_url, headers={'X-Plex-Token': plex_token})
        
        if response.status_code == 200:
            print(f"") ## (f"Tidal tracks added to the playlist successfully in batch {i//BATCH_SIZE + 1}.")
        else:
            print(f"Server says adding Tidal tracks to playlist in batch {i//BATCH_SIZE + 1}: {response.status_code}")
            print(response.text)




def main():
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    
    
    
    music_library = get_music_library(plex, SECTION_TITLE)
    songs = read_songs_from_file(FILENAME)
    playlist_name = input("Please enter the name for the new playlist: ")
    items = []
    tidal_ids = []

    for song_name in songs:
        print("-" * 10)
        artist, title = song_name.split(' - ', 1)
        print(f"Processing {artist} - {title}")
        local_track = find_track_in_library(music_library, artist, title)
        if local_track:
            print("Found in local library.")
        else:
            print("Not found in local library, searching on Tidal...")
            tidal_id = search_tidal(PLEX_TOKEN, artist, title)
            if tidal_id:
                print("Found on Tidal")
                tidal_ids.append(tidal_id)
            else:
                print("Not found on Tidal")

    placeholder_track = find_track_in_library(music_library, PLACEHOLDER_ARTIST, PLACEHOLDER_TITLE)
    if not placeholder_track:
        print("Placeholder track not found.")
        return

    try:
        local_playlist = plex.createPlaylist(playlist_name, items=[placeholder_track])
        playlist_ratingKey = local_playlist.ratingKey

        local_count = len(items)
        
        tidal_count = len(tidal_ids)
        batch_count = 0

        for track in items:
            add_track_to_playlist(PLEX_URL, PLEX_TOKEN, [track.ratingKey], playlist_ratingKey)
        for i in range(0, len(tidal_ids), BATCH_SIZE):
            batch_ids = tidal_ids[i:i + BATCH_SIZE]
            add_track_to_playlist(PLEX_URL, PLEX_TOKEN, batch_ids, playlist_ratingKey)
            batch_count += 1

        local_playlist.removeItems([placeholder_track])
        # Summary output
        print("\nPlaylist Creation Summary:")
        print("-" * 30)  # Separator line for visual clarity
        print(f"Playlist Name: {playlist_name}")
        print(f"Local Tracks Added: {local_count}")
        print(f"Tidal Tracks Added: {tidal_count}")
        print(f"Total Batches Processed: {batch_count}")
        print("-" * 30)
        print("The playlist has been created and tracks have been added successfully.")

    except Exception as e:
        print(f"Error creating the playlist or adding tracks: {e}")

if __name__ == "__main__":
    main()

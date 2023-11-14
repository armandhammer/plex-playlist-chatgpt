# This script facilitates reading a list of tracks from a text file,
# then adds those tracks to a playlist on the Plex server.

# More specifically:
# 1) it prompts for which Plex account to add the playlist to
# 2) it prompts for a name for the new playlist
# 3) it reads a text file which has a list of songs in the format ARTIST - TRACK
# with one song per line. It then searches the local Plex library for matching tracks
# and if those tracks are found, it adds them to the playlist. It then searches for
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
from tqdm import tqdm  # tqdm is a library for progress bars

from ppg_config import PLEX_URL, PLEX_TOKEN, SECTION_TITLE, ADMIN_NAME, ADMIN_PASS, FUZZ_AMT, BATCH_SIZE, PLACEHOLDER_ARTIST, PLACEHOLDER_TITLE

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    
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
        print(f"{Colors.RED}Error: '{filename}' not found.{Colors.RESET}")
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


def format_query(artist: str, title: str) -> str:
    # Remove parentheses but include the descriptor in the title
    formatted_title = re.sub(r"[()]", "", title)
    return f"{artist} {formatted_title}"
    

def search_tidal(plex_token: str, artist: str, title: str):
    date_pattern = r'\d{4}[-\u2013\u2014\u2212/]\d{2}[-\u2013\u2014\u2212/]\d{2}|\d{2}[-\u2013\u2014\u2212/]\d{2}[-\u2013\u2014\u2212/]\d{4}'
    exclude_keywords = ['live', 'concert', 'sbd']
    final_url = ""  # Initialize the final URL as an empty string
    tidal_id = None  # Initialize tidal_id as None

    def perform_search(query):
        nonlocal final_url
        encoded_query = quote(query)
        final_url = f"https://music.provider.plex.tv/hubs/search?query={encoded_query}&X-Plex-Token={plex_token}"
        response = requests.get(final_url)
        if response.status_code != 200:
            print(f"Error: Unable to search Tidal with query '{query}': {response.status_code}")
            return None
        return ET.ElementTree(ET.fromstring(response.text))
        
    def attempt_match(track, input_artist, input_title):
        artist_title = track.get('originalTitle')
        if artist_title is None or artist_title.lower() == "none":
            artist_title = track.get('grandparentTitle')

        track_title = track.get('title')
        album_title = track.get('parentTitle')

        ##print(f"grandparentTitle: {track.get('grandparentTitle')}")
        ##print(f"originalTitle: {track.get('originalTitle')}")
        ##print(f"parentTitle: {album_title}")

        if 'various artists' in artist_title.lower():
            match_artist = True  # Assume artist match in case of various artists
        else:
            match_artist = fuzz.token_set_ratio(simplify_string(input_artist), simplify_string(artist_title)) > FUZZ_AMT

        match_title = fuzz.token_set_ratio(simplify_string(input_title), simplify_string(track_title)) > FUZZ_AMT

        return match_artist and match_title, track.get('guid').split('/')[-1] if match_artist and match_title else None


        if re.search(date_pattern, album_title) or re.search(date_pattern, track_title) or any(
                keyword.lower() in track_title.lower() or keyword.lower() in album_title.lower()
                for keyword in exclude_keywords):
            return False, None

        simplified_input_artist = simplify_string(input_artist)
        simplified_input_title = simplify_string(input_title)
        simplified_library_artist = simplify_string(artist_title)
        simplified_library_title = simplify_string(track_title)

        match = (fuzz.token_set_ratio(simplified_input_artist, simplified_library_artist) > FUZZ_AMT and
                 fuzz.token_set_ratio(simplified_input_title, simplified_library_title) > FUZZ_AMT)
        return match, track.get('guid').split('/')[-1] if match else None

    # First attempt: Search with the full title, including descriptor without parentheses
    formatted_query = format_query(artist, title)
    tree = perform_search(formatted_query)
    if tree is not None and tree.getroot() is not None:
        track_hub = tree.find('./Hub[@type="track"]')
        if track_hub is not None and len(track_hub) > 0:
            for track in track_hub.findall('./Track'):
                match, temp_tidal_id = attempt_match(track, artist, title)
                if match:
                    tidal_id = temp_tidal_id
                    break  # Break the loop if a match is found

    # Second attempt: If not found, try again without the descriptor
    if not tidal_id:  # Only proceed if tidal_id is still None
        simplified_title = re.sub(r"\(.*?\)", "", title).strip()
        formatted_query = format_query(artist, simplified_title)
        tree = perform_search(formatted_query)
        if tree is not None and tree.getroot() is not None:
            track_hub = tree.find('./Hub[@type="track"]')
            if track_hub is not None and len(track_hub) > 0:
                for track in track_hub.findall('./Track'):
                    match, temp_tidal_id = attempt_match(track, artist, simplified_title)
                    if match:
                        tidal_id = temp_tidal_id
                        break  # Break the loop if a match is found

    return tidal_id, final_url  # Always return two values
    

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


def format_log_message(message, total_lines=4):
    current_lines = message.count('\n') + 1
    additional_lines = total_lines - current_lines
    return message + '\n' * additional_lines

from plexapi.exceptions import NotFound
from plexapi.myplex import MyPlexAccount

def main():
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    admin_username = ADMIN_NAME
    admin_password = ADMIN_PASS
    user_account = input("Enter the account to add the playlist to: ")
    
    FILENAME = input("Input filename (or Enter for 'playlist.txt'): ").strip()
    if not FILENAME:
        FILENAME = 'playlist.txt'
    
    music_library = get_music_library(plex, SECTION_TITLE)
    songs = read_songs_from_file(FILENAME)
    
    existing_playlists = [playlist.title for playlist in plex.playlists()]
    playlist_name = input("Please enter the name for the new playlist: ")
    
    while playlist_name in existing_playlists:
        print(f"Playlist '{playlist_name}' already exists. Please choose a different name.")
        playlist_name = input("Please enter the name for the new playlist: ")
    
    local_items = []
    tidal_ids = []
    not_found_tracks = []
    log_messages = []
    pbar = tqdm(total=len(songs), desc="Processing songs")
    
    if user_account.lower() != ADMIN_NAME:
        account = MyPlexAccount(admin_username, admin_password)  # Authenticate with MyPlexAccount
        
        try:
            user = account.user(user_account)  # Try to get non-admin user
            user_token = user.get_token(plex.machineIdentifier)
            plex = PlexServer(PLEX_URL, user_token)  # reinitialize plex with user’s token
        except NotFound:  # Catch the NotFound exception if user is not found
            print(f"Error: Unable to find user {user_account}")
            exit()
    
    for song_name in songs:
        artist, title = song_name.split(' - ', 1)
        log_message = f"{Colors.YELLOW}------------------------------{Colors.RESET}\n{Colors.BLUE}Processing {artist} - {title}{Colors.RESET}\n"

        local_track = find_track_in_library(music_library, artist, title)
        tidal_id, final_url = search_tidal(PLEX_TOKEN, artist, title)
        
        if local_track:
            log_message += f"{Colors.GREEN}Found in local library: {local_track.title}{Colors.RESET}\n\n"
            local_items.append(local_track)
        elif tidal_id:
            tidal_ids.append(tidal_id)
            log_message += f"{Colors.CYAN}Found on Tidal: {tidal_id}{Colors.RESET}\n\n"
        else:
            not_found_tracks.append({
                'artist': artist,
                'track': title,
                'tidal_url': final_url
            })
            log_message += f"{Colors.RED}Not found on Tidal or local: {artist} - {title}{Colors.RESET}\n{final_url}\n"

        formatted_message = format_log_message(log_message, total_lines=4)
        tqdm.write(formatted_message)
        pbar.update(1)

    pbar.close()


    
    try:
        if local_items:
            local_playlist = plex.createPlaylist(playlist_name, items=local_items)
        else:
            print(Colors.YELLOW + "No local tracks found. Creating a playlist with a placeholder track." + Colors.RESET)
            placeholder_track = find_track_in_library(music_library, PLACEHOLDER_ARTIST, PLACEHOLDER_TITLE)
            if placeholder_track:
                local_playlist = plex.createPlaylist(playlist_name, items=[placeholder_track])
            else:
                print(f"{Colors.RED}Error: Placeholder track not found in local library.{Colors.RESET}")
                return

        tidal_track_count = 0
        if tidal_ids:
            tidal_track_count = len(tidal_ids)
            add_track_to_playlist(PLEX_URL, PLEX_TOKEN, tidal_ids, local_playlist.ratingKey)

            if not local_items and placeholder_track:  # Remove placeholder if no local tracks were initially found
                local_playlist.removeItems([placeholder_track])  # Updated to use removeItems

        else:
            print(Colors.YELLOW + "No Tidal tracks to add." + Colors.RESET)


        if not_found_tracks:
            print(f"{Colors.BLUE}-" * 30)
            print(f"{Colors.BLUE}-" * 30)
            print(f"\nTracks not found in local library or Tidal:\n")
            for track in not_found_tracks:
                print(f"{Colors.CYAN}{track['artist']} - {track['track']}{Colors.RESET}")
                print(f"{Colors.RED}Tidal: {track['tidal_url']}\n{Colors.RESET}")
            print(f"{Colors.BLUE}-" * 30)
            print(f"{Colors.BLUE}-" * 30)
            
        # Summary output
        print(f"\n")
        print(f"{Colors.YELLOW}-" * 30)  # Separator line for visual clarity
        print(f"{Colors.YELLOW}-" * 30)  # Separator line for visual clarity
        print(f"{Colors.MAGENTA}Playlist Creation Summary:{Colors.RESET}")
        print(f"{Colors.CYAN}Playlist Name: {playlist_name}{Colors.RESET}")
        print(f"{Colors.GREEN}Local Tracks Added: {len(local_items)}{Colors.RESET}")
        print(f"{Colors.BLUE}Tidal Tracks Added: {tidal_track_count}{Colors.RESET}")
        print(f"{Colors.RED}Total Batches Processed: {len(tidal_ids) // BATCH_SIZE + (1 if len(tidal_ids) % BATCH_SIZE > 0 else 0)}{Colors.RESET}")
        print(f"{Colors.YELLOW}-" * 30)
        print(f"{Colors.YELLOW}-" * 30)  # Separator line for visual clarity
        print(f"{Colors.GREEN}The playlist has been created and tracks have been added successfully.{Colors.RESET}")

    except Exception as e:
        print(f"{Colors.RED}Error creating the playlist or adding tracks: {e}{Colors.RESET}")




if __name__ == "__main__":
    main()

# Here's a revised main() function if you don't need the ability
# to prompt for which user account to add the playlist to.
# Copy and paste the following code in place of the main() function
# in the original script.

def main():
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    
    
    
    
    FILENAME = input("Input filename (or Enter for 'playlist.txt'): ").strip()
    if not FILENAME:
        FILENAME = 'playlist.txt'

    music_library = get_music_library(plex, SECTION_TITLE)
    songs = read_songs_from_file(FILENAME)
    playlist_name = input("Please enter the name for the new playlist: ")
    local_items = []
    tidal_ids = []

    for song_name in songs:
        print(Colors.BLUE + "-" * 10 + Colors.RESET)
        artist, title = song_name.split(' - ', 1)
        print(f"Processing {artist} - {title}")
        local_track = find_track_in_library(music_library, artist, title)

        if local_track:
            print(Colors.GREEN + f"Found in local library: {local_track.title}" + Colors.RESET)
            local_items.append(local_track)
        else:
            tidal_id = search_tidal(PLEX_TOKEN, artist, title)
            if tidal_id:
                tidal_ids.append(tidal_id)
                print(Colors.CYAN + f"Found on Tidal: {tidal_id}" + Colors.RESET)
            else:
                print(Colors.RED + f"Not found on Tidal or local: {artist} - {title}" + Colors.RESET)

    try:
        if local_items:
            local_playlist = plex.createPlaylist(playlist_name, items=local_items)
            ## print(Colors.GREEN + f"Local playlist '{playlist_name}' created with {len(local_items)} tracks." + Colors.RESET)
        else:
            print(Colors.YELLOW + "No local tracks found to create a playlist." + Colors.RESET)

        tidal_track_count = 0
        if tidal_ids:
            tidal_track_count = len(tidal_ids)
            add_track_to_playlist(PLEX_URL, PLEX_TOKEN, tidal_ids, local_playlist.ratingKey)
        else:
            print(Colors.YELLOW + "No Tidal tracks to add." + Colors.RESET)

        # Summary output
        print(f"\n{Colors.MAGENTA}Playlist Creation Summary:{Colors.RESET}")
        print(f"{Colors.YELLOW}-" * 30)  # Separator line for visual clarity
        print(f"{Colors.CYAN}Playlist Name: {playlist_name}{Colors.RESET}")
        print(f"{Colors.GREEN}Local Tracks Added: {len(local_items)}{Colors.RESET}")
        print(f"{Colors.BLUE}Tidal Tracks Added: {tidal_track_count}{Colors.RESET}")
        print(f"{Colors.RED}Total Batches Processed: {len(tidal_ids) // BATCH_SIZE + (1 if len(tidal_ids) % BATCH_SIZE > 0 else 0)}{Colors.RESET}")
        print(f"{Colors.YELLOW}-" * 30)
        print(f"{Colors.GREEN}The playlist has been created and tracks have been added successfully.{Colors.RESET}")

    except Exception as e:
        print(f"{Colors.RED}Error creating the playlist or adding tracks: {e}{Colors.RESET}")


if __name__ == "__main__":
    main()

def main():
    plex = initialize_plex_server(PLEX_URL, PLEX_TOKEN)




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

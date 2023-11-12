# Here's a revised main() function if you don't need the ability
# to prompt for which user account to add the playlist to.
# Copy and paste the following code in place of the main() function
# in the original script.

def main():
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    admin_username = ADMIN_NAME
    admin_password = ADMIN_PASS
    user_account = input("Enter the account to add the playlist to: ")
    music_library = get_music_library(plex, SECTION_TITLE)
    songs = read_songs_from_file(FILENAME)
    playlist_name = input("Please enter the name for the new playlist: ")
    items = []
    tidal_ids = []
    
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

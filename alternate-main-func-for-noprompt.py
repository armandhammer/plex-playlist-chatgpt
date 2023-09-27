# Here's a revised main() function if you don't need the ability
# to prompt for which user account to add the playlist to.
# Copy and paste the following code in place of the main() function
# in the original script.

def main():
    # Initialize Plex Server with admin token
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)

    # Proceeding with the rest of the logic
    music_library = get_music_library(plex, SECTION_TITLE)
    songs = read_songs_from_file(FILENAME)
    playlist_name = input("Please enter the name for the new playlist: ")
    items = []
    tidal_ids = []

    for song_name in songs:
        artist, title = song_name.split(' - ')
        local_track = find_track_in_library(music_library, artist, title)
        if local_track:
            items.append(local_track)
            print(f"Adding to playlist (Local): Artist: {artist}, Title: {title}, Track Details: {local_track}")
        else:
            tidal_id = search_tidal(PLEX_TOKEN, artist, title)
            if tidal_id:
                tidal_ids.append(tidal_id)
                print(f"Adding to playlist (Tidal): Artist: {artist}, Title: {title}, Tidal ID: {tidal_id}")
            else:
                print(f"No local or Tidal track found for '{artist} - {title}'.")

    if items or tidal_ids:
        try:
            if items:
                local_playlist = plex.createPlaylist(playlist_name, items=items)
                local_playlist_ratingKey = local_playlist.ratingKey
                print(f"Local tracks added to the '{playlist_name}' playlist successfully.")
            if tidal_ids:
                add_track_to_playlist(PLEX_URL, PLEX_TOKEN, tidal_ids, local_playlist_ratingKey)
        except Exception as e:
            print(f"Error creating the playlist: {e}")
    else:
        print("No songs found to create a playlist.")

if __name__ == "__main__":
    main()


# Change it to reflect the local URL of your Plex server.

PLEX_URL = 'http://192.168.0.214:32400'


# I think the token is 20 characters

PLEX_TOKEN = '[YOUR PLEX TOKEN]'

SECTION_TITLE = '[PLEX MUSIC LIBRARY NAME]'  # It might just be 'Music'

ADMIN_NAME = '[PLEX ADMIN NAME]'
ADMIN_PASS = '[PLEX ADMIN PASSWORD]'


# Set how loosely the script matches tracks in your library
# or on Tidal. 60 seems to work well.

FUZZ_AMT = 60


# This splits up adding songs to the playlist in batches,
# since the Plex URL for adding songs can't hold an infinite
# amount of tracks.

BATCH_SIZE = 20


# Enter an artist and track which exists in your library.
# This is used as a placeholder to create a playlist,
# in the use case where only Tidal tracks are found.
# After creating the playlist, adding the placeholder,
# and adding Tidal tracks, the placeholder is deleted.

PLACEHOLDER_ARTIST = 'LCD Soundsystem'
PLACEHOLDER_TITLE = 'Dance Yrself Clean'




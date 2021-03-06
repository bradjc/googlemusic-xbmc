import sys
import GoogleMusicLogin
from gmusicapi.api import Api

"""
Handles all calls to the Unofficial Google Music Api
"""

class GoogleMusicApi():
    def __init__(self):
        self.xbmc       = sys.modules["__main__"].xbmc
        self.xbmcgui    = sys.modules["__main__"].xbmcgui
        self.xbmcplugin = sys.modules["__main__"].xbmcplugin

        self.settings   = sys.modules["__main__"].settings
        self.language   = sys.modules["__main__"].language
        self.dbg        = sys.modules["__main__"].dbg
        self.common     = sys.modules["__main__"].common
        self.storage    = sys.modules["__main__"].storage

        self.gmusicapi = Api()
        self.login = GoogleMusicLogin.GoogleMusicLogin(self.gmusicapi)


    """
    Returns a list of songs. Each song is a dict object with keys that match
    the unnoficial gmusic api response.
    """
    def getSongs (self, playlistid=None, selector=None):
        songs = self.storage.getSongs(playlistid=playlistid, selector=selector)

        if songs == None:
            # no songs in storage, need to request them
            self.updateSongs(playlistid=playlistid)
            songs = self.storage.getSongs(playlistid=playlistid,
                                          selector=selector)

        return songs

    """
    Returns a list of playlists.
    playlist = {
        'name': <playlist name>
        'id': <playlist id>
    }
    """
    def getPlaylists (self, playlisttype='user'):
        playlists = self.storage.getPlaylists(playlisttype)

        if playlists == None:
            # no playlists in storage, need to request
            self.updatePlaylists(playlisttype)
            playlists = self.storage.getPlaylists(playlisttype)

        return playlists
    """
        def getPlaylistSongs(self, playlist_id, forceRenew=False):
            if not self.storage.isPlaylistFetched(playlist_id) or forceRenew:
                self.updatePlaylistSongs(playlist_id)

            songs = self.storage.getPlaylistSongs(playlist_id)

            return songs

        def getPlaylistsByType(self, playlist_type, forceRenew=False):
            if forceRenew:
                self.updatePlaylists(playlist_type)

            playlists = self.storage.getPlaylistsByType(playlist_type)
            if len(playlists) == 0 and not forceRenew:
                self.updatePlaylists(playlist_type)
                playlists = self.storage.getPlaylistsByType(playlist_type)

            return playlists
    """

    """
    Return the song dict for a single song.
    """
    def getSong(self, song_id):
        return self.storage.getSong(song_id)

    """
    Query the google music api for songs.
    """
    def updateSongs (self, playlistid=None):
        self.login.login()
        if playlistid is None:
            songs = self.gmusicapi.get_all_songs()
        else:
            songs = self.gmusicapi.get_playlist_songs(playlistid)

        self.storage.storeSongs(songs, playlistid)

    """
    Query for a list of playlists.
    """
    def updatePlaylists(self, playlist_type=None):
        self.login.login()
        playlists = self.gmusicapi.get_all_playlist_ids(auto=True,
                                                        user=True,
                                                        always_id_lists=True)
        if playlist_type is None:
            self.storage.storePlaylists(playlists['auto'], 'auto')
            self.storage.storePlaylists(playlists['user'], 'user')
        else:
            self.storage.storePlaylists(playlists[playlist_type], playlist_type)

    """
    Get the current url the song can be streamed from. These aparently change
    rapidly so we won't store it.
    """
    def getSongStreamUrl(self, song_id):
        self.login.login()
        return self.gmusicapi.get_stream_url(song_id)

    """
    Returns a list of artist dicts:
    artist = {
        'name': <artist name>
    }
    """
    def getArtists (self):
        artists = self.storage.getDistinct(field='artist')
        if artists is None:
            self.updateSongs()
            artists = self.storage.getDistinct(field='artist')

        # Convert list of artists to a list of dicts. This is pretty worthless
        # now, but allows for easy additions later without breaking old code.
        ad = []
        for artist in artists:
            ad.append({'name':artist['artist']})

        return ad

    def getAlbums (self, selector):
        albums = self.storage.getDistinct(field='album', selector=selector)
        if albums is None:
            self.updateSongs()
            albums = self.storage.getDistinct(field='album', selector=selector)

        al = []
        for album in albums:
            al.append({'name':album['album']})

        return al

    def getGenres (self):
        genres = self.storage.getDistinct(field='genre')
        if genres is None:
            self.updateSongs()
            genres = self.storage.getDistinct(field='genre')

        ge = []
        for genre in genres:
            ge.append({'name':genre['genre']})

        return ge

    """
    Queries google for results related to the search string.

    Returns a tuple (songs, artists, albums).
    songs is a list of song dicts
    artists is a list of song dicts
    albums is a list of album dicts
    Each list could be empty
    album = {
        'artistName': 'The Cat Empire',
        'imageUrl': '<url>',
        'albumArtist': 'The Cat Empire',
        'albumName': 'Cities: The Cat Empire Project'
    }
    """
    def doSearch (self, search_str):
        self.login.login()
        result  = self.gmusicapi.search(search_str)
        self.common.log(result)
        songs   = result['song_hits']
        artists = result['artist_hits']
        albums  = result['album_hits']

        for i in range(len(songs)):
            songs[i] = self.fixSongDict(songs[i])

        for i in range(len(artists)):
            artists[i] = self.fixSongDict(artists[i])

        return (songs, artists, albums)

    """
    Adds in displayName and albumArtUrl keys to the song dict.
    This is not an API function and should be moved to a different class.
    """
    def fixSongDict (self, song):
        if 'displayName' not in song:
            song['displayName'] = self._getSongDisplayName(song)
        song.setdefault('albumArtUrl')
        return song

    def _getSongDisplayName(self, song):
        displayName = ''
        song_name   = song['name'].strip()
        song_artist = song['artist'].strip()

        if len(song_artist) == 0 and len(song_name) == 0:
            displayName = 'UNKNOWN'
        elif len(song_artist) > 0:
            displayName += song_artist
            if len(song_name) > 0:
                displayName += " - " + song_name
        else:
            displayName += song_name

        return displayName


    """
        def getFilterSongs(self, filter_type, filter_criteria):
            songs = self.storage.getFilterSongs(filter_type, filter_criteria)

            return songs

        def getCriteria(self, criteria):
            return self.storage.getCriteria(criteria)
    """


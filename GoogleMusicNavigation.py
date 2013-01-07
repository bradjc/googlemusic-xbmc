import os
import sys
import re
import socket
import urllib
import urllib2
import xbmc
import xbmcaddon
import GoogleMusicApi

ADDON = xbmcaddon.Addon(id='plugin.audio.googlemusic')

class GoogleMusicNavigation():
    def __init__(self, handle):
        self.xbmc       = sys.modules["__main__"].xbmc
        self.xbmcgui    = sys.modules["__main__"].xbmcgui
        self.xbmcplugin = sys.modules["__main__"].xbmcplugin
        self.xbmcvfs    = sys.modules["__main__"].xbmcvfs
        
        self.settings   = sys.modules["__main__"].settings
        self.language   = sys.modules["__main__"].language
        self.dbg        = sys.modules["__main__"].dbg
        self.common     = sys.modules["__main__"].common

        self.handle     = int(handle)

        self.api = GoogleMusicApi.GoogleMusicApi()

        self.main_menu = (
            {'title':  self.language(30201),    # All Songs
             'params': {'action':  'display',
                        'content': 'songs'}},
            {'title':  self.language(30202),    # Playlists
             'params': {'action':  'display',
                        'content': 'playlists',
                        'type':    'user'}},
            {'title':  self.language(30204),    # Insta mixes
             'params': {'action':  'display',
                        'content': 'playlists',
                        'type':    'auto'}},
            {'title':  self.language(30205),    # Artists
             'params': {'action':  'display',
                        'content': 'artists'}},
            {'title':  self.language(30206),    # Albums
             'params': {'action':  'display',
                        'content': 'albums'}},
            {'title':  self.language(30207),    # Genres
             'params': {'action':  'display',
                        'content': 'genres'}},
        )

    """ Main function for handling a URL"""
    def execute (self, params={}):

        if 'action' not in params:
            params['action'] = 'display'
            
        
        if params['action'] == 'display':
            # Something should be displayed. Figure out what is specified to
            #  determine what to display.
            content = params.get('content')

            if not content:
                # No URL was specified. Display the main menu.
                for menu_item in self.main_menu:
                    ps = menu_item['params']
                    cm = self.getContextMenu(params)
                    self.addFolderListItem(menu_item['title'], ps, cm)
            elif content == 'songs':
                self.displaySongs(artist=params.get('artist'),
                                  playlistid=params.get('playlistid'),
                                  album=params.get('album'))
            elif content == 'playlists':
                self.displayPlaylists(playlisttype=params.get('type'))
            elif content == 'artists':
                self.displayArtists()
            elif content == 'albums':
                self.displayAlbums(artist=params.get('artist'))
            elif content == 'genres':
                self.displayGenres()
            else:
                self.execute()

            self.xbmcplugin.endOfDirectory(handle=self.handle, succeeded=True)

        elif params['action'] == 'play':
            if params.get('songid'):
                self.playSong(params['songid'])
            else:
                self.playAll()

        elif params['action'] == 'update':
            content = params.get('content', 'playlists')
            if content == 'playlists':
                self.updatePlaylists(playlisttype=params.get('type'),
                                     playlistid=params.get('playlistid'))

        elif params['action'] == 'maintenance':
            mtype = params.get('type')
            if mtype == 'clearcookie':
                self.clearcookie()
            elif mtype == 'clearcache':
                self.clearCache()

        else:
            self.execute()

    """
    Return a list of context menu tuples based on the parameters in the request
    string.

    Returns [] if no context menu items are set up for the item.
    TODO: convert the ugly text strings to dicts and urllib.urlencode
    """
    def getContextMenu (self, params):
        content    = params.get('content')
        ptype      = params.get('type')
        playlistid = params.get('playlistid')

        cm = []

        if content == 'songs':
            # This item will bring up a bunch of songs.
            s = '%s?action=play%s' % (self.handle, \
                ('&playlist_id=%s' % playlistid if playlistid else ''))
            cm.append((self.language(30301), 'XBMC.RunPlugin(%s)' % s))
            s += '&shuffle=true'
            cm.append((self.language(30302), 'XBMC.RunPlugin(%s)' % s))

            if playlistid:
                cm.append((self.language(30303),
                    'XBMC.RunPlugin(%s?action=update&content=playlists&playlistid=%s)' \
                    % (self.handle, playlistid)))

        elif content == 'playlists':
            cm.append((self.language(30304),
                'XBMC.RunPlugin(%s?action=update&content=playlists&type=%s)' \
                % (self.handle, ptype)))

        return cm





"""
    def listMenu(self, params={}):
        get = params.get
        path = get("path", "root")

        if path == "root":
            ''' Show the plugin root menu. '''
            for menu_item in self.main_menu:
                params = menu_item['params']
                cm = []
                if 'playlist_id' in params:
                    cm = self.getPlayAllContextMenuItems(params['playlist_id'])
                elif 'playlist_type' in params:
                    cm = self.getPlaylistsContextMenuItems(params['playlist_type'])
                self.addFolderListItem(menu_item['title'], params, cm)
        elif path == "playlist":
            self.listPlaylistSongs(get("playlist_id"))
        elif path == "playlists":
            playlist_type = get('playlist_type')
            if playlist_type in ('auto', 'instant', 'user'):
                self.getPlaylists(playlist_type)
            else:
                self.common.log("Invalid playlist type: " + playlist_type)
        elif path == "filter":
            criteria  = get('criteria')
            #self.common.log("Filter path: " + criteria)
            self.getCriteria(criteria)
        elif path in ["genre","artist","album"]:
            filter_criteria = get('name')
            self.common.log("Genre path: " + get("path"))
            self.listFilterSongs(path,filter_criteria)
        else:
            self.common.log("Invalid path: " + get("path"))

        self.xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

    def executeAction(self, params={}):
        get = params.get
        if (get("action") == "play_all"):
            self.playAll(params)
        elif (get("action") == "play_song"):
            self.playSong(params)
        elif (get("action") == "update_playlist"):
            self.api.getPlaylistSongs(params["playlist_id"], True)
        elif (get("action") == "update_playlists"):
            self.api.getPlaylistsByType(params["playlist_type"], True)
        elif (get("action") == "clear_cache"):
            self.clearCache()
        elif (get("action") == "clear_cookie"):
            self.clearCookie()
        else:
            self.common.log("Invalid action: " + get("action"))
"""

    def addFolderListItem(self, name, params={}, contextMenu=[]):
        li = self.xbmcgui.ListItem(name)
        li.setProperty('Folder', 'true')

        url = '%s?%s' % (self.handle, urllib.urlencode(params))

        if len(contextMenu) > 0:
            li.addContextMenuItems(contextMenu, replaceItems=True)

        return self.xbmcplugin.addDirectoryItem(handle=self.handle,
                                                url=url,
                                                listitem=li,
                                                isFolder=True)

    """
    Base function for displaying a list of songs. Pass in as specific of
    parameters as necessary, or None otherwise.
    """
    def displaySongs (self, artist, playlistid, album, genre):
        self.common.log('Displaying songs: artist %s, playlist %s, album %s, \
                         genre %s' % (artist, playlistid, album, genre))

        if playlistid:
            # Display the songs in this playlist. If artist or album is set
            #  (they shouldn't be), ignore them.
            songs = self.api.getPlaylistSongs(playlistid)

        elif artist or album or genre:
            # Use the other information to display a list of songs
            selectors = {}
            if artist:
                selectors['artist'] = artist
            if album:
                selector['album'] = album
            if genre:
                selector['genre'] = genre

            songs = self.api.getSongs(selector)

        else:
            # Nothing to go off of, can't display any songs
            self.common.log('displaySongs: ERROR: NOTHING TO USE.')

        # Add all of the returned songs to the output
        for song in songs:
            songid = song['id'].encode('utf-8')
            li     = self.createSongListItem(song)
            params = {
                'action': 'play',
                'songid': songid,
            }
            url    = '%s?%s' % (self.handle, urllib.urlencode(params))
            self.xbmcplugin.addDirectoryItem(handle=self.handle,
                                             url=url,
                                             listitem=li)

    """
    Display a list of playlists. Displays either the instamixes or the users
    playlists.
    """
    def displayPlaylists (self, playlisttype):
        self.common.log('Displaying playlists: type %s' % playlisttype)

        playlists = self.api.getPlaylistsByType(playlisttype)
        for playlist in playlists:
            params = {
                'action': 'display',
                'content': 'songs',
                'playlistid': playlist['id']
            }
            cm = self.getContextMenu(params)
            self.addFolderListItem(playlist['name'], params)

    """
    Display a list of artists.
    """
    def displayArtists (self):
        self.common.logs('Displaying artists.')

        artists = self.api.getArtists():
        for artist in artists:
            params = {
                'action': 'display',
                'content': 'albums',
                'artist': artist['name']
            }
            self.addFolderListItem(artist['name'], params, [])

    """
    Display a list of albums. Leave artist None to display all albums.
    """
    def displayAlbums (self, artist):
        self.common.log('Displaying albums: artist %s.' % artist)

        selector = {}
        if artist:
            selector['artist'] = artist

        albums = self.api.getAlbums(selector)
        for album in albums:
            params = {
                'action': 'display',
                'content': 'songs',
                'album': album['name'],
            }
            if artist:
                params['artist'] = artist
            self.addFolderListItem(album['name'], params, [])

    """
    Display all the genres.
    """
    def displayGenres (self):
        self.common.log('Displaying genres.')

        genres = self.api.getGenres()
        for genre in genres:
            params = {
                'action': 'display',
                'content': 'songs',
                'genre': genre['name']
            }
            self.addFolderListItem(genre['name'], params, [])


    """
    Create a xbmc list item for a given song.
    """
    def createSongListItem (self, song):
        image_path   = xbmc.translatePath(ADDON.getAddonInfo('profile')) \
                       .decode('utf-8')
        artwork_path = self.getAlbumArt(image_path, song.get('albumArtUrl'))

        li = self.xbmcgui.ListItem(label=song['displayName'],
                                   thumbnailImage=artwork_path)
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setInfo(type='music', infoLabels=self.getInfoLabels(song))

        return li

    """
    Returns a local file path to the album artwork if the artwork exists or an
    empty string if it does not.
    """
    def getAlbumArt(self, image_path, art_url):
        if art_url is None:
            return ''

        art_url = re.sub('=s\d+-c', '=s256-c', art_url)
        uid     = re.compile('.*/([^/]+)$')

        try:
            file_path = image_path + uid.findall(art_url)[0] + '.jpg'
            if not os.path.isfile(file_path):
                # Artwork is not already downloaded, retrieve it from the
                # internets.
                self.getImage('http:' + art_url, file_path)
            return file_path
        except Exception :
            sys.exc_clear()
            return ''

    """
    Download album art from the Internet. Saves it to the path give.

    Returns True on success and False on failure.
    """
    def getImage(self, url, path):
        timeout = 10
        socket.setdefaulttimeout(timeout)

        try:
                # Set useragent, sites don't like to interact with scripts
            headers = {'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; \
                                      rv:1.9.2.8) Gecko/20100723 Ubuntu/10.04 \
                                      (lucid) Firefox/3.6.8',
                       'Accept': 'text/html,application/xhtml+xml,\
                                  application/xml;q=0.9,*/*;q=0.8',
                       'Accept-Language': 'en-us,en;q=0.5',
                       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'}
            req = urllib2.Request(url=url, headers=headers)
            f   = urllib2.urlopen(req)
            imagedata = f.read()        # Downloads imagedata

            open(path, 'wb').write(imagedata)

            # Return true
            return True
        except Exception:
            return False

    """
    Returns a dict suitable for ListItem.setInfo() from a song dict.
    """
    def getInfoLabels(self, song):
        infoLabels = {
            'tracknumber': song['track'],
            'duration': song['durationMillis'] / 1000,
            'year': song['year'],
            'genre': song['genre'].encode('utf-8'),
            'album': song['album'].encode('utf-8'),
            'artist': song['artist'].encode('utf-8'),
            'title': song['title'].encode('utf-8'),
            'playcount': song['playCount'],
        }
        return infoLabels



"""

    def getAlbumArt(self, image_path, art_url):
        if art_url is None:
            return ''

        art_url = re.sub('=s\d+-c', '=s256-c', art_url)
        uid = re.compile('.*/([^/]+)$')

        try:
            file_path = image_path + uid.findall(art_url)[0] + '.jpg'
            if (not os.path.isfile(file_path)):
                self.getImage('http:' + art_url, file_path)
            return file_path
        except Exception :
            sys.exc_clear()
            return ''


    def createSongListItem(self, song):
        artwork_path = ''
        image_path = xbmc.translatePath( ADDON.getAddonInfo('profile') ).decode('utf-8')
        artwork_path = self.getAlbumArt(image_path, song[22])

        if len(artwork_path) > 0:
            li = self.xbmcgui.ListItem(song[23], thumbnailImage=artwork_path)
        else:
            li = self.xbmcgui.ListItem(song[23])

        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setInfo(type='music', infoLabels=self.getInfoLabels(song))

        return li
"""

    def addSongItem(self, song):
        song_id = song[0].encode('utf-8')

        li = self.createSongListItem(song)

        url = '%s?action=play_song&song_id=%s' % (sys.argv[0], song_id)
        return self.xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
            url=url, listitem=li)

    def listPlaylistSongs(self, playlist_id):
        self.common.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        self.addSongsFromLibrary(songs)

    def addSongsFromLibrary(self, library):
        for song in library:
            self.addSongItem(song)

    def getPlaylists(self, playlist_type):
        self.common.log("Getting playlists of type: " + playlist_type)
        playlists = self.api.getPlaylistsByType(playlist_type)
        self.common.log(str(playlists))
        self.addPlaylistsItems(playlists)
        
    def listFilterSongs(self, filter_type, filter_criteria):
        songs = self.api.getFilterSongs(filter_type,
            urllib.unquote_plus(filter_criteria))
        self.common.log(str(songs))
        self.addSongsFromLibrary(songs)

    def getCriteria(self, criteria):
        genres = self.api.getCriteria(criteria)
        for genre in genres:
            cm = []
            self.addFolderListItem(genre[0], {'path':criteria,
                'name':genre[0].encode('utf8')}, cm)
        self.common.log(str(genres))

    def addPlaylistsItems(self, playlists):
        for playlist_id, playlist_name, playlist_type, fetched in playlists:
            cm = self.getPlayAllContextMenuItems(playlist_id)
            self.addFolderListItem(playlist_name, {'path':"playlist",
                'playlist_id':playlist_id}, cm)

    def playAll(self, params={}):
        get = params.get

        playlist_id = get('playlist_id')
        self.common.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)

        player = self.xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = self.xbmc.PlayList(self.xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        song_url = "%s?action=play_song&song_id=%s&playlist_id=" + playlist_id
        for song in songs:
            song_id = song[0].encode('utf-8')

            li = self.createSongListItem(song)
            playlist.add(song_url % (sys.argv[0], song_id), li)

        if (get("shuffle")):
            playlist.shuffle()

        self.xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def playSong(self, params={}):
        get = params.get
        song = self.api.getSong(get("song_id"))
        url = self.api.getSongStreamUrl(get("song_id"))

        li = self.createSongListItem(song)
        li.setPath(url)

        self.xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True,
            listitem=li)
"""
    def getPlayAllContextMenuItems(self, playlist):
        cm = []
        cm.append((self.language(30301),
            "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" %
            (sys.argv[0], playlist)))
        cm.append((self.language(30302), 
            "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" 
            % (sys.argv[0], playlist)))
        cm.append((self.language(30303),
         "XBMC.RunPlugin(%s?action=update_playlist&playlist_id=%s)" 
         % (sys.argv[0], playlist)))
        return cm

    def getPlaylistsContextMenuItems(self, playlist_type):
        cm = []
        cm.append((self.language(30304), 
            "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" 
            % (sys.argv[0], playlist_type)))
        return cm

    def getInfoLabels(self, song):
        infoLabels = {
            'tracknumber': song[11],
            'duration': song[21] / 1000,
            'year': song[6],
            'genre': song[14].encode('utf-8'),
            'album': song[7].encode('utf-8'),
            'artist': song[18].encode('utf-8'),
            'title': song[8].encode('utf-8'),
            'playcount': song[15]
        }
        return infoLabels
"""
    def clearCache(self):
        sqlite_db = os.path.join(self.xbmc.translatePath("special://database"),
            self.settings.getSetting('sqlite_db'))
        if self.xbmcvfs.exists(sqlite_db):
            self.xbmcvfs.delete(sqlite_db)

        self.settings.setSetting("fetched_all_songs", "")
        self.settings.setSetting('firstrun', "")

        self.clearCookie()

    def clearCookie(self):
        cookie_file = os.path.join(self.settings.getAddonInfo('path'),
            self.settings.getSetting('cookie_file'))
        if self.xbmcvfs.exists(cookie_file):
            self.xbmcvfs.delete(cookie_file)

        self.settings.setSetting('logged_in', "")

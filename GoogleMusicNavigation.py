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
    def __init__(self, root, handle):
        self.xbmc       = sys.modules["__main__"].xbmc
        self.xbmcgui    = sys.modules["__main__"].xbmcgui
        self.xbmcplugin = sys.modules["__main__"].xbmcplugin
        self.xbmcvfs    = sys.modules["__main__"].xbmcvfs

        self.settings   = sys.modules["__main__"].settings
        self.language   = sys.modules["__main__"].language
        self.dbg        = sys.modules["__main__"].dbg
        self.common     = sys.modules["__main__"].common

        self.root       = root
        self.handle     = int(handle)

        self.api = GoogleMusicApi.GoogleMusicApi()

        self.main_menu = (
            {'title':  self.language(30208),    # Search
             'params': {'action':  'search'}},
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
                    cm = self.getContextMenu(menu_item['params'])
                    self.addFolderListItem(menu_item['title'], ps, cm)
            elif content == 'songs':
                self.displaySongs(artist=params.get('artist'),
                                  playlistid=params.get('playlistid'),
                                  album=params.get('album'),
                                  genre=params.get('genre'))
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
                self.playAll(playlistid=params.get('playlistid'),
                             shuffle=params.get('shuffle'))

        elif params['action'] == 'update':
            content = params.get('content', 'playlists')
            if content == 'playlists':
                self.updatePlaylists(playlisttype=params.get('type'),
                                     playlistid=params.get('playlistid'))

        elif params['action'] == 'maintenance':
            mtype = params.get('type')
            if mtype == 'clearcookie':
                self.clearCookie()
            elif mtype == 'clearcache':
                self.clearCache()

        elif params['action'] == 'search':
            search_str = self.getUserInput(title=self.language(30105))
            self.common.log('SEARCH: "%s"' % (search_str))
            self.displaySearchResults(search_str)
            self.xbmcplugin.endOfDirectory(handle=self.handle, succeeded=True)

        else:
            self.execute()

    """
    Return a list of context menu tuples based on the parameters in the request
    string.

    Returns [] if no context menu items are set up for the item.
    """
    def getContextMenu (self, params):
        content    = params.get('content')
        ptype      = params.get('type')
        playlistid = params.get('playlistid')

        cm = []

        if content == 'songs':
            # This item will bring up a bunch of songs.
            params = {
                'action': 'play',
            }
            if playlistid:
                params['playlistid'] = playlistid
            cm.append((self.language(30301),
                   'XBMC.RunPlugin(%s?%s)' \
                    % (self.root, urllib.urlencode(self._encodeDict(params)))))
            params['shuffle'] = 'true'
            cm.append((self.language(30302),
                    'XBMC.RunPlugin(%s?%s)' \
                    % (self.root, urllib.urlencode(self._encodeDict(params)))))


            if playlistid:
                params = {
                    'action': 'update',
                    'content': 'playlists',
                    'playlistid': playlistid
                }
                cm.append((self.language(30303),
                    'XBMC.RunPlugin(%s?%s)' \
                    % (self.root, urllib.urlencode(self._encodeDict(params)))))

        elif content == 'playlists':
            params = {
                'action': 'update',
                'content': 'playlists',
                'type': ptype,
            }
            cm.append((self.language(30304),
                'XBMC.RunPlugin(%s?%s)' \
                % (self.root, urllib.urlencode(self._encodeDict(params)))))

        return cm



    def addFolderListItem(self, name, params={}, contextMenu=[]):
        li = self.xbmcgui.ListItem(name)
        li.setProperty('Folder', 'true')

        url = '%s?%s' % (self.root, urllib.urlencode(self._encodeDict(params)))

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
            songs = self.api.getSongs(playlistid=playlistid)

        elif artist or album or genre:
            # Use the other information to display a list of songs
            selector = {}
            if artist:
                selector['artist'] = artist
            if album:
                selector['album'] = album
            if genre:
                selector['genre'] = genre

            songs = self.api.getSongs(selector=selector)

        else:
            # No specifier given, display all songs
            songs = self.api.getSongs()

        if not songs:
            # no songs in this playlist
            return

        # Add all of the returned songs to the output
        for song in songs:
            songid = song['id'].encode('utf-8')
            li     = self.createSongListItem(song)
            params = {
                'action': 'play',
                'songid': songid,
            }
            url    = '%s?%s' % (self.root, urllib.urlencode(params))
            self.xbmcplugin.addDirectoryItem(handle=self.handle,
                                             url=url,
                                             listitem=li)

    """
    Display a list of playlists. Displays either the instamixes or the users
    playlists.
    """
    def displayPlaylists (self, playlisttype):
        self.common.log('Displaying playlists: type %s' % playlisttype)

        playlists = self.api.getPlaylists(playlisttype)
        for playlist in playlists:
            params = {
                'action': 'display',
                'content': 'songs',
                'playlistid': playlist['id']
            }
            cm = self.getContextMenu(params)
            self.addFolderListItem(playlist['name'], params, cm)

    """
    Display a list of artists.
    """
    def displayArtists (self):
        self.common.log('Displaying artists.')

        artists = self.api.getArtists()
        for artist in artists:
            if not artist['name']:
                continue
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
            if not album['name']:
                continue
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
            if not genre['name']:
                continue
            params = {
                'action': 'display',
                'content': 'songs',
                'genre': genre['name']
            }
            self.addFolderListItem(genre['name'], params, [])

    """
    Display the results from the gmusic search.
    """
    def displaySearchResults (self, search_str):
        songs,artists,albums = self.api.doSearch(search_str)

        for song in songs:
            params = {
                'action': 'display',
                'content': 'songs',
                'album': song['album'],
                'artist': song['artist'],
            }
            self.addFolderListItem(song['displayName'], params, [])

        # artists is a list of song dicts
        for artist in artists:
            params = {
                'action': 'display',
                'content': 'albums',
                'artist': artist['artist']
            }
            self.addFolderListItem(artist['artist'], params, [])

        for album in albums:
            params = {
                'action': 'display',
                'content': 'songs',
                'album': album['albumName'],
            }
            self.addFolderListItem(album['albumName'], params, [])


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



    def playSong (self, songid):
        song = self.api.getSong(songid)
        url  = self.api.getSongStreamUrl(songid)

        li = self.createSongListItem(song)
        li.setPath(url)

        self.xbmcplugin.setResolvedUrl(handle=self.handle,
                                       succeeded=True,
                                       listitem=li)

    def playAll (self, playlistid, shuffle):

        songs = self.api.getSongs(playlistid)

        player = self.xbmc.Player()
        if player.isPlaying():
            player.stop()

        playlist = self.xbmc.PlayList(self.xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        params = {
            'action': 'play',
            'songid': None,
        }
     #   song_url = "%s?action=play_song&song_id=%s&playlist_id=" + playlist_id
        self.common.log(playlistid)
        for song in songs:
            params['songid'] = song['id'].encode('utf-8')
            li = self.createSongListItem(song)
            playlist.add('%s?%s' % (self.root, urllib.urlencode(params)), li)

        if shuffle:
            playlist.shuffle()

        self.xbmc.executebuiltin('playlist.playoffset(music , 0)')


    def updatePlaylists (self, playlisttype, playlistid):
        if playlisttype:
            self.api.updatePlaylists(playlisttype)
        elif playlistid:
            self.api.updateSongs(playlistid)


    def clearCache(self):
    #    self.api.clearAll()
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

    # This function raises a keyboard for user input
    def getUserInput (self, title = "Input", default="", hidden=False):
        result = None

        # Fix for when this functions is called with default=None
        if not default:
            default = ""

        keyboard = xbmc.Keyboard(default, title)
        keyboard.setHiddenInput(hidden)
        keyboard.doModal()

        if keyboard.isConfirmed():
            result = keyboard.getText()

        return result

    def _encodeDict (self, in_dict):
        out_dict = {}
        for k, v in in_dict.iteritems():
            if isinstance(v, unicode):
                v = v.encode('utf8')
            elif isinstance(v, str):
                # Must be encoded in UTF-8
                v.decode('utf8')
            out_dict[k] = v
        return out_dict


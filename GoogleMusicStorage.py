import os
import sys
import sqlite3

"""
Return a SQL row as a dict of column: value key-value pairs.
"""
def dict_factory (cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class GoogleMusicStorage():
    def __init__(self):
        self.xbmc     = sys.modules["__main__"].xbmc
        self.xbmcvfs  = sys.modules["__main__"].xbmcvfs
        self.settings = sys.modules["__main__"].settings
        self.path = os.path.join(self.xbmc.translatePath("special://database"),
                                 self.settings.getSetting('sqlite_db'))

		# Make sure to initialize database when it does not exist.
        if ((not os.path.isfile(self.path)) or
            (not self.settings.getSetting("firstrun"))):
            self.initializeDatabase()
            self.settings.setSetting("firstrun", "1")

    """
    Return a list of song dicts.
    Set playlistid to None to get all songs.
    Set selector to key value pairs to restrict the value in the given column.
    """
    def getSongs (self, playlistid=None, selector=None):
        self._connect()
        self.conn.row_factory = dict_factory

        if playlistid == None:
            # get all songs
            where  = self._dictToWhere(selector)
            sql    = 'SELECT * FROM songs' + where
            result = self.curs.execute(sql)

        else:
            sql = """SELECT * FROM songs
                     INNER JOIN playlists_songs
                         ON songs.song_id = playlists_songs.song_id
                     WHERE playlists_songs.playlist_id = ?"""
            result = self.curs.execute(sql, (playlist_id,))

        songs = result.fetchall()
        self.conn.close()

        # Check if there are no songs. In that case return None instead of an
        # empty list.
        if len(songs) == 0 and self.countSongs() == 0:
            songs = None

        return songs

    """
    Return a song dict for a single song.
    """
    def getSong (self, songid):
        self._connect()
        self.conn.row_factory = dict_factory
        result = self.curs.execute("""SELECT * FROM songs
                                      WHERE id = ?
                                   """, (songid,)
                                   ).fetchone()
        self.conn.close()

        if not result and self.countSongs() == 0:
            result = None

        return result

    """
    Get list of playlist dicts. Dict is the same as the columns in the
    playlist table.
    """
    def getPlaylists (self, playlisttype):
        self._connect()
        self.conn.row_factory = dict_factory

        sql = "SELECT * FROM playlists WHERE playlists.type = ?"
        result = self.curs.execute(sql, (playlisttype,))
        playlists = result.fetchall()
        self.conn.close()

        if len(playlists) == 0 and self.countSongs() == 0:
            playlists = None

        return playlists

    """
    Returns a list of all values in the specified column of the songs table.
    Selector can be used to refine the results.
    """
    def getDistinct (self, field, selector=None):
        self._connect()

        where = self._dictToWhere(selector)
        sql = "SELECT DISTINCT ? FROM songs" + where
        result = self.curs.execute(sql, (field,))

        vals = result.fetchall()

        if len(vals) == 0 and self.countSongs() == 0:
            vals = None

        return vals

    """
    def getPlaylistSongs(self, playlist_id):
        self._connect()

        result = []
        if playlist_id == 'all_songs':
            result = self.curs.execute("SELECT * FROM songs")
        else:
            result = self.curs.execute("SELECT * FROM songs INNER JOIN playlists_songs ON songs.song_id = playlists_songs.song_id WHERE playlists_songs.playlist_id = ?", (playlist_id,))

        songs = result.fetchall()
        self.conn.close()

        return songs

    def getFilterSongs(self, filter_type, filter_criteria):
        self._connect()

        result = self.curs.execute("SELECT * FROM songs WHERE "+ filter_type +"  = ?",(filter_criteria,))
        songs = result.fetchall()

        return songs

    def getCriteria(self, criteria):
        self._connect()
        criterias = self.curs.execute("SELECT DISTINCT "+criteria+" FROM songs").fetchall()
        self.conn.close()

        return criterias

    def getPlaylistsByType(self, playlist_type):
        self._connect()
        result = self.curs.execute("SELECT * FROM playlists WHERE playlists.type = ?", (playlist_type,))
        playlists = result.fetchall()
        self.conn.close()

        return playlists
    """

    """
    Save a list of song dicts to the databse.
    """
    def storeSongs (self, songs, playlistid=None):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        # Delete the correct rows to make room for the updated data
        if playlistid == None:
            self.curs.execute("DELETE FROM songs")
        else:
            self.curs.execute("""DELETE FROM songs
                                 WHERE song_id IN
                                     (SELECT song_id FROM playlists_songs
                                      WHERE playlist_id = ?)""",
                              (playlist_id,))
            self.curs.execute("""DELETE FROM playlists_songs
                                 WHERE playlist_id = ?""",
                              (playlist_id,))
            self.curs.executemany("""INSERT INTO playlists_songs
                                         (playlist_id, song_id)
                                     VALUES (?, ?)""",
                                  [(playlistid, s['id']) for s in songs])

        def songs():
            for song in songs:
                song.setdefault('albumArtUrl')
                song['displayName'] = self._getSongDisplayName(song)
                yield song

        # Insert the songs into the database
        sql = """INSERT OR REPLACE INTO songs
                 VALUES (:id, :comment, :rating, :lastPlayed, :disc, :composer,
                         :year, :album, :title, :albumArtist, :type, :track,
                         :totalTracks, :beatsPerMinute, :genre, :playCount,
                         :creationDate, :name, :artist, :url, :totalDiscs,
                         :durationMillis, :albumArtUrl, :displayName)"""
        self.curs.executemany(sql, songs())

        # Set flags so we know what data was stored
        if playlist_id == None:
            self.settings.setSetting("fetched_all_songs", "1")
        else:
            self.curs.execute("""UPDATE playlists
                                 SET fetched = 1
                                 WHERE id = ?""", (playlist_id,))

        self.conn.commit()
        self.conn.close()

    """
    Save all of the playlists in the database.
    Understands the direct result of the get_all_playlist_ids() from the api.
    """
    def storePlaylists (self, playlists, playlist_type):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        # (deletes will not cascade due to pragma)
        self.curs.execute("DELETE FROM playlists WHERE type = ?",
                          (playlist_type,))

        # rebuild table
        def playlist_rows():
            for playlist_name, playlist_ids in playlists.iteritems():
                if isinstance(playlist_ids,str):
                    yield (playlist_name, playlist_ids, playlist_type)
                else:
                    for playlist_id in playlist_ids:
                        yield (playlist_name, playlist_id, playlist_type)

        self.curs.executemany("""INSERT INTO playlists
                                 (name, id, type, fetched)
                                 VALUES (?, ?, ?, 0)""", playlist_rows())

        # clean up dangling songs
        self.curs.execute("""DELETE FROM playlists_songs
                             WHERE playlist_id NOT
                                 IN (SELECT playlist_id FROM playlists)""")
        self.conn.commit()
        self.conn.close()

    """
    Returns true/false to indicate if a playlist's songs have been inserted
    into the playlist_songs table.
    """
    def isPlaylistFetched (self, playlistid=None):
        fetched = False
        if playlist_id == None:
            fetched = bool(self.settings.getSetting("fetched_all_songs"))
        else:
            self._connect()
            playlist = self.curs.execute("""SELECT fetched FROM playlists
                                            WHERE playlist_id = ?""",
                                         (playlist_id,)).fetchone()
            fetched = bool(playlist[0])
            self.conn.close()

        return fetched

    def countSongs (self):
        self._connect()

        sql = 'SELECT COUNT(*) FROM songs'
        result = self.curs.execute(sql).fetchone()
        count = result[0]

        self.conn.close()

        return count


    # no longer storing stream urls - they change too often
    #    def getSongStreamUrl(self, song_id):
    #        self._connect()
    #        song = self.curs.execute("SELECT stream_url FROM songs WHERE song_id = ?", (song_id,)).fetchone()
    #        stream_url = song[0]
    #        self.conn.close()
    #
    #        return stream_url
    #    def updateSongStreamUrl(self, song_id, stream_url):
    #        self._connect()
    #        self.curs.execute("UPDATE songs SET stream_url = ? WHERE song_id = ?", (stream_url, song_id))
    #        self.conn.commit()
    #        self.conn.close()

    def _connect(self):
        self.conn = sqlite3.connect(self.path)
        self.curs = self.conn.cursor()


    """
    Create the tables for storing song information.
    """
    def initializeDatabase(self):
        self._connect()

        # nearly matches the reponse from the unofficial api
        # doesn't include all fields
        self.curs.execute('''CREATE TABLE songs (
            id             VARCHAR NOT NULL PRIMARY KEY,           --# 0
            comment        VARCHAR,                                --# 1
            rating         INTEGER,                                 --# 2
            lastPlayed     INTEGER,                            --# 3
            disc           INTEGER,                                   --# 4
            composer       VARCHAR,                               --# 5
            year           INTEGER,                                   --# 6
            album          VARCHAR,                                  --# 7
            title          VARCHAR,                                  --# 8
            albumArtist    VARCHAR,                           --# 9
            type           INTEGER,                                   --# 10
            track          INTEGER,                                  --# 11
            totalTracks    INTEGER,                           --# 12
            beatsPerMinute INTEGER,                       --# 13
            genre          VARCHAR,                                  --# 14
            playCount      INTEGER,                             --# 15
            creationDate   INTEGER,                          --# 16
            name           VARCHAR,                                   --# 17
            artist         VARCHAR,                                 --# 18
            url            VARCHAR,                                    --# 19
            totalDiscs     INTEGER,                            --# 20
            durationMillis INTEGER,                        --# 21
            albumArtUrl    VARCHAR,                          --# 22
            displayName    VARCHAR                           --# 23
        )''')

        self.curs.execute('''CREATE TABLE playlists (
            id      VARCHAR NOT NULL PRIMARY KEY,
            name    VARCHAR,
            type    VARCHAR,
            fetched BOOLEAN
        )''')

        self.curs.execute('''CREATE TABLE playlists_songs (
            playlist_id VARCHAR,
            song_id     VARCHAR,
            FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
            FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
        )''')

        self.curs.execute(
            '''CREATE INDEX playlistindex ON playlists_songs(playlist_id)''')
        self.curs.execute(
            '''CREATE INDEX songindex ON playlists_songs(song_id)''')

        self.conn.commit()
        self.conn.close()

    """
    Return a nice string of Artist - Song if the fields are set.
    """
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

    def _encodeApiSong(self, api_song):
        encoding_keys = ["id", "comment", "composer", "album", "title", "albumArtist", "titleNorm", "albumArtistNorm", "genre", "name", "albumNorm", "artist", "url", "artistNorm", "albumArtUrl"]

        song = {}
        for key in api_song:
            key = key.encode('utf-8')
            if key in encoding_keys:
                song[key] = api_song[key].encode('utf-8')
            else:
                song[key] = api_song[key]

        return song


    """
    Turn a dictionary into an SQL WHERE string
    """
    def _dictToWhere (self, selector):
        where_str = ''
        if selector:
            where = []
            for col,val in selector.iteritems():
                where.append('%s=%s' % col, val)
            where_str = ' WHERE ' + ' and '.join(where)
        return where_str

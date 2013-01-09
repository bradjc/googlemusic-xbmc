import sys, xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

# plugin constants
version = "0.5.0"
plugin = "GoogleMusic-" + version

# xbmc hooks
settings = xbmcaddon.Addon(id='plugin.audio.googlemusic')
language = settings.getLocalizedString
dbg = settings.getSetting( "debug" ) == "true"
dbglevel = 3

# plugin variables
storage = ""
common = ""

if (__name__ == "__main__" ):
    if dbg:
        print plugin + " ARGV: " + repr(sys.argv)
    else:
        print plugin

    root   = sys.argv[0]
    handle = sys.argv[1]
    url    = sys.argv[2]

    import CommonFunctions
    common = CommonFunctions
    common.plugin = plugin

    import GoogleMusicStorage
    storage = GoogleMusicStorage.GoogleMusicStorage()

    import GoogleMusicNavigation
    navigation = GoogleMusicNavigation.GoogleMusicNavigation(root, handle)

    import GoogleMusicLogin

    params = common.getParameters(url)

    try:
        navigation.execute(params)
    except GoogleMusicLogin.GoogleMusicLoginException:
        # Couldn't login, just exit
        pass

#    if not url:
#        navigation.execute()
#    else:
#        params = common.getParameters(url)
#        if 'action' in params:
#            navigation.execute(params)
#        get = params.get
#        if params.get("action"):
#            navigation.executeAction(params)
#        elif (get("path")):
#            navigation.listMenu(params)
#        else:
#            print plugin + " ARGV Nothing done. Verify params " + repr(params)

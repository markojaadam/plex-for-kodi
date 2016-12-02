import xbmc
import xbmcgui
import kodigui

import busy
import videoplayer
import windowutils
import dropdown
import search

from lib import colors
from lib import util
from lib import player

from lib.util import T


class PlaylistWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-playlist.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    OPTIONS_GROUP_ID = 200
    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202
    PLAYER_STATUS_BUTTON_ID = 204

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303

    LI_AR16X9_THUMB_DIM = (178, 100)
    LI_SQUARE_THUMB_DIM = (100, 100)

    ALBUM_THUMB_DIM = (630, 630)

    PLAYLIST_LIST_ID = 101

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.playlist = kwargs.get('playlist')
        self.exitCommand = None

    def onFirstInit(self):
        self.playlistListControl = kodigui.ManagedControlList(self, self.PLAYLIST_LIST_ID, 5)
        self.setProperties()

        self.fillPlaylist()
        self.setFocusId(self.PLAYLIST_LIST_ID)

    # def onAction(self, action):
    #     try:
    #         if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
    #             if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
    #                 self.setFocusId(self.OPTIONS_GROUP_ID)
    #                 return
    #     except:
    #         util.ERROR()

    #     kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.goHome()
        elif controlID == self.PLAYLIST_LIST_ID:
            self.playlistListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playlistListClicked(no_item=True, shuffle=False)
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.playlistListClicked(no_item=True, shuffle=True)
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self))

    def playlistListClicked(self, no_item=False, shuffle=False):
        if no_item:
            mli = None
        else:
            mli = self.playlistListControl.getSelectedItem()
            if not mli:
                return
            player.PLAYER.stop()  # Necessary because if audio is already playing, it will close the window when that is stopped

        if self.playlist.playlistType == 'audio':
            self.playlist.setShuffle(shuffle)
            self.playlist.setCurrent(mli and mli.pos() or 0)
            self.showAudioPlayer(track=mli and mli.dataSource or self.playlist.current(), playlist=self.playlist)
        elif self.playlist.playlistType == 'video':
            self.playlist.setShuffle(shuffle)
            self.playlist.setCurrent(mli and mli.pos() or 0)
            videoplayer.play(play_queue=self.playlist)

    def optionsButtonClicked(self):
        options = []
        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': T(32325, 'Play Next')})

        if not options:
            return

        choice = dropdown.showDropdown(options, (440, 1020), close_direction='down', pos_is_bottom=True, close_on_playback_ended=True)
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')

    def setProperties(self):
        self.setProperty(
            'background',
            self.playlist.composite.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('playlist.thumb', self.playlist.composite.asTranscodedImageURL(*self.ALBUM_THUMB_DIM))
        self.setProperty('playlist.title', self.playlist.title)
        self.setProperty('playlist.duration', util.durationToText(self.playlist.duration.asInt()))

    def createListItem(self, pi):
        if pi.type == 'track':
            return self.createTrackListItem(pi)
        elif pi.type == 'episode':
            return self.createEpisodeListItem(pi)
        elif pi.type in ('movie', 'clip'):
            return self.createMovieListItem(pi)

    def createTrackListItem(self, track):
        label2 = u'{0} / {1}'.format(track.grandparentTitle, track.parentTitle)
        mli = kodigui.ManagedListItem(track.title, label2, thumbnailImage=track.defaultThumb.asTranscodedImageURL(*self.LI_SQUARE_THUMB_DIM), data_source=track)
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(track.duration.asInt()))
        return mli

    def createEpisodeListItem(self, episode):
        label2 = u'{0} \u2022 {1}'.format(
            episode.grandparentTitle, u'{0}{1} \u2022 {2}{3}'.format(T(32310, 'S'), episode.parentIndex, T(32311, 'E'), episode.index)
        )
        mli = kodigui.ManagedListItem(episode.title, label2, thumbnailImage=episode.thumb.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM), data_source=episode)
        mli.setProperty('track.duration', util.durationToShortText(episode.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', episode.isWatched and '1' or '')
        return mli

    def createMovieListItem(self, movie):
        mli = kodigui.ManagedListItem(movie.title, movie.year, thumbnailImage=movie.art.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM), data_source=movie)
        mli.setProperty('track.duration', util.durationToShortText(movie.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', movie.isWatched and '1' or '')
        return mli

    @busy.dialog()
    def fillPlaylist(self):
        items = []
        idx = 1
        for pi in self.playlist.unshuffledItems():
            mli = self.createListItem(pi)
            if mli:
                mli.setProperty('track.number', str(idx))
                mli.setProperty('track.ID', pi.ratingKey)
                items.append(mli)
                idx += 1

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)

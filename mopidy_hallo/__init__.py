from __future__ import unicode_literals

import glob
import logging
import os
import time
from threading import Thread, Event

import pykka
from mopidy import config, ext, core
from mopidy.audio import PlaybackState
from respeaker import Microphone, pixel_ring

__version__ = '0.1.1'

logger = logging.getLogger(__name__)


class HalloFrontend(pykka.ThreadingActor, core.CoreListener):
    def __init__(self, config, core):
        super(HalloFrontend, self).__init__()
        self.config = config
        self.core = core
        self.quit_event = Event()

    def _run(self):
        time.sleep(3)

        mic = Microphone(quit_event=self.quit_event)

        while not self.quit_event.is_set():
            try:
                if mic.wakeup('respeaker'):
                    logger.info('Wake up')
                    paused = False
                    if self.core.playback.get_state().get() == PlaybackState.PLAYING:
                        paused = True
                        # self.core.playback.pause()  # sometimes paused state can not be resumed (playing but no sound)
                        self.core.playback.stop()
                    data = mic.listen()
                    text = mic.recognize(data)
                    if text.find('play music') >= 0:
                        logger.info('Recognized as {}'.format(text))
                        if not self.core.playback.get_current_track().get():
                            for entry in self.config['hallo']['media_dirs']:
                                for mp3 in glob.glob(os.path.join(entry, '*.mp3')):
                                    logger.info('Add {} to track list'.format(mp3))
                                    mp3_uri = 'file://' + mp3
                                    self.core.tracklist.add(uri=mp3_uri)
                        self.core.playback.play()

                    if paused and self.core.playback.get_state().get() == PlaybackState.PAUSED:
                        # self.core.playback.resume()
                        self.core.playback.play()
            except Exception as e:
                logger.error(e.message)

    def on_start(self):
        thread = Thread(target=self._run)
        thread.daemon = True
        thread.start()

    def on_stop(self):
        self.quit_event.set()

    def volume_changed(self, volume):
        logger.info('Volume changed {}'.format(volume))
        pixel_ring.set_volume(volume=volume)

    def mute_changed(self, mute):
        pass


class Extension(ext.Extension):
    dist_name = 'Mopidy-Hallo'
    ext_name = 'hallo'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['media_dirs'] = config.List(optional=True)
        return schema

    def setup(self, registry):
        registry.add('frontend', HalloFrontend)

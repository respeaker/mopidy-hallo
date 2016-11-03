from __future__ import unicode_literals

import os
import logging

import pykka
from threading import Thread, Event

from mopidy import config, ext, core

from respeaker import Microphone, pixel_ring

__version__ = '0.1.0'

logger = logging.getLogger(__name__)


class HalloFrontend(pykka.ThreadingActor, core.CoreListener):
    def __init__(self, config, core):
        super(HalloFrontend, self).__init__()
        self.core = core
        self.quit_event = Event()

    def _run(self):
        mic = Microphone(quit_event=self.quit_event)

        while not self.quit_event.is_set():
            try:
                if mic.wakeup('respeaker'):
                    logger.info('Wake up')
                    self.core.playback.stop()
                    data = mic.listen()
                    text = mic.recognize(data)
                    if text.find('play music') >= 0:
                        logger.info('Recognized as {}'.format(text))
                        self.core.playback.play()
            except Exception as e:
                logger.error(e.message)

    def on_start(self):
        thread = Thread(target=self._run)
        thread.start()

    def on_stop(self):
        self.quit_event.set()

    def volume_changed(self, volume):
        logger.info('Volume changed')
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

    def setup(self, registry):
        registry.add('frontend', HalloFrontend)




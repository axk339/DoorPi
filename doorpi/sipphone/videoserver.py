import logging
from subprocess import Popen, PIPE
from typing import Iterable
import time

import doorpi
from doorpi.actions import CallbackAction

LOGGER: doorpi.DoorPiLogger = logging.getLogger(__name__)  # type: ignore


class Videoserver(object):

    def __init__(self):
        self.transcoder = None
        self.transcoder_running = False
        self.__conf = doorpi.INSTANCE.config.view('videoserver')
        self.cmd = ["ffmpeg"]
        # standard arguments for camera module
        self._input_kwargs = {}
        self._output_kwargs = {'codec:v': 'rawvideo',
                               'f': 'v4l2',
                               'pix_fmt': 'yuv420p',
                               'r': '15',
                               'y': None}

        eh = doorpi.INSTANCE.event_handler
        eh.register_action("OnShutdown", CallbackAction(self.stop))
        eh.register_action("AfterStartup", CallbackAction(self.stop_transcode))
        eh.register_action("OnCallUnanswered", CallbackAction(self.stop_transcode))
        eh.register_action("OnCallDisconnect", CallbackAction(self.stop_transcode))

    def _convert_kwargs(self, kwargs):
        """Helper function to build command line arguments out of dict."""
        if isinstance(kwargs, str):
            kwargs = self._convert_str_to_kwargs(kwargs)
        args = []
        for k in sorted(kwargs.keys()):
            v = kwargs[k]
            if isinstance(v, Iterable) and not isinstance(v, str):
                for value in v:
                    args.append('-{}'.format(k))
                    if value is not None:
                        args.append('{}'.format(value))
                continue
            args.append('-{}'.format(k))
            if v is not None:
                args.append('{}'.format(v))
        return args

    def _convert_str_to_kwargs(self, args):
        """Helper function to convert a string of comma delimited arguments into kwargs"""
        args = args.replace("{", "").replace("}", "")
        _items = args.split(",")
        if any([len(i) == 2 for j in _items for i in [j.split("=")]]):
            _delim = "="
        else:
            _delim = ":"
        _kwargs = dict()
        for i in range(len(_items)):
            _arg = _items[i].split(_delim)
            if len(_arg) == 1:
                _arg.append(None)
            elif len(_arg) == 3:
                _arg[0:2] = [':'.join(_arg[0:2])]
            k, v = _arg
            k = k.strip().replace("'", "")
            if v:
                v = v.strip()
                if not " " in v:
                    v = v.replace("'", "")
                elif not "'" in v:
                    v = f"'{v}'"
            _kwargs[k] = v

        return _kwargs

    def _init_cmd(self):
        """Helper function to init ffmpeg command either from config args or default values (camera module)"""
        infile = "-i {}".format(self.__conf['server'])
        outfile = self.__conf['device']

        cmddict = dict()
        cmddict[infile] = self.__conf['input_arguments'] or self._input_kwargs
        cmddict[outfile] = self.__conf['output_arguments'] or self._output_kwargs

        for _file, _kwargs in cmddict.items():
            fileargs = _file.split(" ")
            self.cmd.extend(self._convert_kwargs(_kwargs) + fileargs)

    def start_transcode(self):
        """Main transcoder start function"""
        if not self.transcoder_running:
            del self.cmd[1:]
            self._init_cmd()

            self.transcoder = Popen(self.cmd, stdout=PIPE, stdin=PIPE)
            LOGGER.debug("Process started with: %s", ' '.join(self.cmd))
            self.transcoder_running = True
            time.sleep(self.__conf["delay"])
        else:
            LOGGER.error("FFmpeg transcoder process running")

    def stop_transcode(self):
        """Main transcoder end function"""
        # just for safety (the calling 'OnCallDisconnect' only should fire with the main call dropped)
        if doorpi.INSTANCE.sipphone.current_call or doorpi.INSTANCE.sipphone._ringing_calls:
            return

        if self.transcoder_running:
            LOGGER.debug("Shutting down process")
            self.transcoder.terminate()
            self.transcoder.communicate()
            self.transcoder_running = False
        else:
            LOGGER.debug("No FFmpeg transcoder process is running")

    @property
    def is_transcoding(self):
        return self.transcoder_running

    def stop(self):
        """Clean up at shutdown"""
        self.stop_transcode()
        self.transcoder = None

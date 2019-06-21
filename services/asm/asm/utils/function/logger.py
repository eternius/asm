import logging


class Logger(object):

    def __init__(self, level):
        self._logger = logging.getLogger('abot')
        self._logger.setLevel(level)
        self._handlers = {}

    def set_handler(self, handler_name, file, formatter):

        # check if there's a handler by this name
        if handler_name in self._handlers:

            # log that we're removing it
            self.info_with('Replacing logger output')

            self._logger.removeHandler(self._handlers[handler_name])

        # create a stream handler from the file
        stream_handler = logging.StreamHandler(file)

        # set the formatter
        stream_handler.setFormatter(formatter)

        # add the handler to the logger
        self._logger.addHandler(stream_handler)

        # save as the named output
        self._handlers[handler_name] = stream_handler

    def debug(self, message, *args):
        self._logger.debug(message, *args)

    def info(self, message, *args):
        self._logger.info(message, *args)

    def warn(self, message, *args):
        self._logger.warning(message, *args)

    def error(self, message, *args):
        self._logger.error(message, *args)

    def debug_with(self, message, *args, **kw_args):
        self._logger.debug(message, *args, extra={'with': kw_args})

    def info_with(self, message, *args, **kw_args):
        self._logger.info(message, *args, extra={'with': kw_args})

    def warn_with(self, message, *args, **kw_args):
        self._logger.warning(message, *args, extra={'with': kw_args})

    def error_with(self, message, *args, **kw_args):
        self._logger.error(message, *args, extra={'with': kw_args})
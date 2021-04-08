#!/usr/bin/env python
# coding: utf-8

# In[ ]:





# In[ ]:


# ログ用
from logging import Logger, Handler, getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN
class KabuSLogger:
    # VERBOSE = DEBUG / 2
    def __init__(self, loggername: str=__name__,
                loglevel_logger: int=DEBUG):
        self._logger_name = loggername
        self._loglevel_logger = loglevel_logger
        self._logger = self.logger
    
    @property
    def logger(self) -> Logger:
        if '_logger' in globals():
            return self._logger
        logger = getLogger(self._logger_name)
        logger.setLevel(self._loglevel_logger)
        logger.propagate = False
        return logger
    
    def addHandler(self, handler: Handler):
        self.logger.addHandler(handler)
        
    # def verbose(self, msg, *args, **kwargs):
    #     self.log(self.VERBOSE, msg, args, kwargs)
        
    def debug(self, msg, **kwargs):
        self.log(DEBUG, msg, **kwargs)
        
    def info(self, msg, **kwargs):
        self.log(INFO, msg, **kwargs)
        
    def warn(self, msg, **kwargs):
        self.log(WARN, msg, **kwargs)
        
    def log(self, level, msg, **kwargs):
        if kwargs:
            self._logger.log(level, msg, **kwargs)
        else:
            self._logger.log(level, msg)


# In[ ]:





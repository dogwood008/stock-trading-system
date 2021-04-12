#!/usr/bin/env python
# coding: utf-8

# In[ ]:





# In[10]:


from logging import DEBUG
from backtrader.feed import DataBase
from backtrader.utils.py3 import with_metaclass

from meta_kabu_s_data import MetaKabuSData
from kabu_s_logger import KabuSLogger

class KabuSData(with_metaclass(MetaKabuSData, DataBase)): # FIXME
    def __init__(self, *args, **kwargs):
        if 'handler' in kwargs:
            logger = KabuSLogger(__class__.__name__, DEBUG)
            logger.debug(args)
            logger.debug(kwargs)
            logger.debug(f'{__class__.__name__} called.')
            logger.addHandler(kwargs['handler'])


# In[13]:


if __name__ == '__main__':
    from kabu_s_handler import KabuSHandler
    handler = KabuSHandler(DEBUG)
    kabu_s_data = KabuSData(handler=handler)


# In[ ]:





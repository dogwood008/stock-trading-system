#!/usr/bin/env python
# coding: utf-8

# In[ ]:





# In[ ]:


from logging import Handler, StreamHandler, Formatter, DEBUG, INFO, WARN
class KabuSHandler(StreamHandler):
    def __init__(self, loglevel: int=INFO):
        super().__init__()
        self.setLevel(loglevel)
        self.setFormatter(
          Formatter('[%(levelname)s] %(message)s'))
    


# In[ ]:





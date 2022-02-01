#!/usr/bin/env python
# coding: utf-8

# In[ ]:





# In[9]:


from backtrader.feed import DataBase

from kabu_s_api_store import KabuSAPIStore

class MetaKabuSData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaKabuSData, cls).__init__(name, bases, dct)

        # Register with the store
        KabuSAPIStore.DataCls = cls


# In[8]:





# In[ ]:





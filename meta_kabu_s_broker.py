#!/usr/bin/env python
# coding: utf-8

# In[ ]:





# In[2]:


from backtrader import BrokerBase
from kabu_s_api_store import KabuSAPIStore

class MetaKabuSBroker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaKabuSBroker, cls).__init__(name, bases, dct)
        KabuSAPIStore.BrokerCls = cls


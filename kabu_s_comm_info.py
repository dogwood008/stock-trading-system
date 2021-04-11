#!/usr/bin/env python
# coding: utf-8

# In[ ]:





# In[1]:


from backtrader.comminfo import CommInfoBase

class KabuSCommInfo(CommInfoBase):
    def getvaluesize(self, size, price):
        # In real life the margin approaches the price
        return abs(size) * price

    def getoperationcost(self, size, price):
        '''Returns the needed amount of cash an operation would cost'''
        # Same reasoning as above
        return abs(size) * price


# %%: Load
import dill
filepath = './rates_df.dill'
d = dill.load(open(filepath,'rb'))

# %% Show
d
# %%
d[d['code']=='9143']

# %%

d['date']

# %%

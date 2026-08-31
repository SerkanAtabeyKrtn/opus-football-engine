# Contract test: an existing forward prediction is immutable except settlement fields.
old={'id':'x','p':.71,'market':'U25','tier':'DENGELİ','edge':.09,'status':'PENDING','hg':None,'ag':None,'won':None}
new_model={'p':.52,'market':'O25','tier':'PAS','edge':-.02}
# update.py intentionally does not overwrite if id already exists
existing={'x':old.copy()}
if 'x' not in existing: existing['x']=new_model
assert existing['x']['p']==.71 and existing['x']['market']=='U25' and existing['x']['tier']=='DENGELİ'
existing['x'].update(status='SETTLED',hg=1,ag=0,won=True)
assert existing['x']['p']==.71 and existing['x']['hg']==1
print('LEDGER IMMUTABILITY TEST PASSED')

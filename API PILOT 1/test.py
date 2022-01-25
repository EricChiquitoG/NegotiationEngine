d=dict({'naim':2,'eric':{'sera':[1,2]}})
l=['naim','eric']

print((d.get('sera') for val in d.values()))
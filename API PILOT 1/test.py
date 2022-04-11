


testdict={'eric':{1:2},'kpel':2}



# def dict_flatten(in_dict, dict_out=None, parent_key=None, separator="_"):
#    if dict_out is None:
#       dict_out = {}

#    for k, v in in_dict.items():
#       k = f"{parent_key}{separator}{k}" if parent_key else k
#       if isinstance(v, dict):
#          dict_flatten(in_dict=v, dict_out=dict_out, parent_key=k)
#          continue

#       dict_out[k] = v

#    return dict_out


keys = ['eric']
dict2 = {x:testdict[x] for x in keys}
print(dict2)
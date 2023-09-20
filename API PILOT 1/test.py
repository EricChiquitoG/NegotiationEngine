
d1,d2=dict(),dict()
list1 = [{"a":1, "b":2, "c":3}]
list2 = [{1:2, 2:3, 3:4}]
d1['parent1']=list1[0]
d2['parent2']=list2[0]
d3=d1|d2
print(d3['parent2'])

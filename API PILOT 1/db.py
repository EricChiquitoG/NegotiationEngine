from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient, DESCENDING
from werkzeug.security import generate_password_hash
import uuid
import hashlib
from user import User
from string import Template
from geopy.geocoders import Nominatim
import json
from geopy.distance import geodesic
import ast
from collections import defaultdict
import os


# client = MongoClient("mongodb+srv://EricTest:test@cluster0.ozw3z.mongodb.net/myFirstDatabase?retryWrites=true&w=majority", ssl=True,ssl_cert_reqs='CERT_NONE')
client = MongoClient(os.environ.get("DATABASE_URL"))


chat_db = client.get_database("ChatDB")
users_collection = chat_db.get_collection("users")
rooms_collection = chat_db.get_collection("rooms")
room_members_collection = chat_db.get_collection("room_members")
messages_collection = chat_db.get_collection("messages")
templates_collection=chat_db.get_collection("templates")
room_details=chat_db.get_collection("room_details")

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId) or isinstance(o, datetime):
            return str(o)
        return json.JSONEncoder.default(self, o)


def add_template():
    temp_id=1
    temp_type='article'
    temp="Hereby I $buyer, declare the purchase of $quantity units of $item for the ammount of $ammount SEK on $date from $owner. \nBuyer signature $buyersign \nSeller signature $sellersign"
    templates_collection.insert_one({'_id':temp_id,'temp_type':temp_type,'template':temp})


def save_user(username, email, password,sign,location):
    password_hash = generate_password_hash(password)
    salt = uuid.uuid4().hex
    hashsign = hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt
    print(type(location),location)
    users_collection.insert_one({'type':'user','_id': ObjectId(),'username':username, 'email': email, 'password': password_hash,'sign':hashsign,'location':location})


def get_user(username):
    user_data = users_collection.find_one({'username': username})
    return User(user_data['username'], user_data['email'], user_data['password'],user_data['sign'],user_data['location']) if user_data else None

def get_sign(username):
    user_data = users_collection.find_one({'username': username})

    return user_data['sign']

def find_rooms(room_name,reference_sector,reference_type,ongoing,user ,distance):
    filtro={}


    if room_name is not None: filtro['payload.room_name.val.0'] = room_name
    if reference_sector is not None: filtro['payload.reference_sector.val.0'] = reference_sector
    if reference_type is not None: filtro['payload.reference_type.val.0'] = reference_type
    if ongoing == 'True': filtro['payload.closing_time.val.0'] = {'$gte' : datetime.now() }
    # Create a filter for the distance
    if distance is not None:
        names,todos = get_distances(user,distance)
        filtro['payload.created_by.val.0']={'$in':names}
    else:
        names,todos = get_distances(user,10000)
        filtro['payload.created_by.val.0']={'$in':names}
    auctions=list(room_details.find(filtro))

    values_of_key = [a_dict['payload']['created_by']['val'][0] for a_dict in auctions]
    
    for k in auctions:

        for j in todos:
            if k['payload']['created_by']['val'][0] in j.values():
                print(k)
                to_append={'distance':{'val':['test']}}
                k['payload'].update(to_append)
                print(k)
                k['payload']['distance']['val'][0]=j['dist']



    l=list(filter(lambda d: d['payload']['created_by']['val'][0] in values_of_key, auctions))
    return(JSONEncoder().encode(l))


## This function returns a list with the distances relative to the bidder to all the users and filters by distance
def get_distances(bidder,dist):
    base=list(users_collection.find({},{'location':0}))
    for d in base:
        d['dist']=distance_calc(bidder,d['username'])
        d.pop('location',None)
    filtered_users=[x for x in base if float(x['dist'])<=float(dist) and x['username']!=bidder]
    my_list = list(map(lambda x: x['username'], filtered_users))
    for d in filtered_users:
        d['created_by']=d.pop('username')
    #print(my_list,filtered_users)
    l=list(filter(lambda d: d['created_by'] in my_list, filtered_users))
    #print(l)
    return my_list,filtered_users


def distance_calc(bidder,owner):
    distance=geodesic(ast.literal_eval(get_distance(bidder)),ast.literal_eval(get_distance(owner))).km
    return distance

def save_room(privacy, room_name, created_by,auction_type, highest_bid,highest_bidder,closing_time,sellersign,buyersign,templatetype):
    room_id = rooms_collection.insert_one(
        {'type':'auction','_id':ObjectId(),'privacy':privacy,
        'payload':{'name': {'val':[room_name]},
                 'created_by': {'val':[created_by]}, 
                 'created_at': {'val':[datetime.now()]},
                 'auction_type':{'val':[auction_type]}, 
                 'highest_bid':{'val':[highest_bid]},
                 'highest_bidder':{'val':[highest_bidder]},
                 'closing_time':{'val':[closing_time]},
                 'sellersign':{'val':[sellersign]},
                 'buyersign':{'val':[buyersign]},
                 'templatetype':{'val':[templatetype]}}}).inserted_id
    add_room_member(room_id, room_name, created_by, created_by, is_room_admin=True)
    return room_id

def save_param(room_id,created_by,room_name,reference_sector,reference_type, quantity, articleno):
    room=rooms_collection.find_one({'_id': ObjectId(room_id)})
    room_details.insert_one(
        {'type':'details','_id': ObjectId(room_id),
        'payload':{'room_name':{'val':[room_name]},
                'created_by':{'val':[created_by]},
                'closing_time':{'val':[room['payload']['closing_time']['val'][0]]}, 
                'reference_sector':{'val':[reference_sector]},
                'reference_type':{'val':[reference_type]},
                'quantity':{'val':[quantity]},
                'articleno':{'val':[articleno]}}})

# Currently is not being used
def update_room(room_id, room_name):
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'name': room_name}})
    room_members_collection.update_many({'_id.room_id': ObjectId(room_id)}, {'$set': {'room_name': room_name}})


def get_room(room_id):
    return rooms_collection.find_one({'_id': ObjectId(room_id)})


def add_room_member(room_id, room_name, username, added_by, is_room_admin=False):
    room_members_collection.insert_one(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'room_name': room_name, 'added_by': added_by,
         'added_at': datetime.now(), 'is_room_admin': is_room_admin})


def add_room_members(room_id, room_name, usernames, added_by):
    room_members_collection.insert_many(
        [{'_id': {'room_id': ObjectId(room_id), 'username': username}, 'room_name': room_name, 'added_by': added_by,
          'added_at': datetime.now(), 'is_room_admin': False} for username in usernames])

### Get the highest bids in current auction for each active user
def get_bidders(room_id):
    safe=[]
    room=rooms_collection.find_one({'_id': ObjectId(room_id)})
    if room['payload']['auction_type']['val'][0]=="Ascending":

        hb=list(messages_collection.aggregate([ {'$unwind':'$payload.text.val'},
                                                {'$unwind':'$payload.sender.val'},
                                                {'$unwind':'$payload.created_at.val'},
                                                {'$unwind':'$payload.sign.val'},
                                                {'$unwind':'$payload.distance.val'},
                                                {'$match':{'room_id':room_id}},
                                                {'$group':{'_id':'$payload.sender.val','doc':{'$max':{
                                                                            'text':'$payload.text.val',
                                                                            'sender':'$payload.sender.val',
                                                                            'created_at':'$payload.created_at.val',
                                                                            'distance':'$payload.distance.val',
                                                                            'sign':'$payload.sign.val'
                                                                            }
                                                                        }
                                                                        }}
                                                                        ]))
    else:
        hb=list(messages_collection.aggregate([ {'$unwind':'$payload.text.val'},
                                                {'$unwind':'$payload.sender.val'},
                                                {'$unwind':'$payload.created_at.val'},
                                                {'$unwind':'$payload.sign.val'},
                                                {'$unwind':'$payload.distance.val'},
                                                {'$match':{'room_id':room_id}},
                                                {'$group':{'_id':'$payload.sender.val','doc':{'$min':{
                                                                            'text':'$payload.text.val',
                                                                            'sender':'$payload.sender.val',
                                                                            'created_at':'$payload.created_at.val',
                                                                            'distance':'$payload.distance.val',
                                                                            'sign':'$payload.sign.val'
                                                                            }
                                                                        }
                                                                        }}
                                                                        ]))
    for i in hb:
        safe.append(i['doc'])
        
    return JSONEncoder().encode(safe)


def remove_room_members(room_id, usernames):
    room_members_collection.delete_many(
        {'_id': {'$in': [{'room_id': ObjectId(room_id), 'username': username} for username in usernames]}})

###
def get_room_admin(room_id):
    room= room_members_collection.find_one({'room_name': room_id,"is_room_admin":True})
    return room['_id']['username']

def get_distance(username):
    dist=users_collection.find_one({'username':username})
    
    return dist['location']

def get_room_members(room_id):
    return list(room_members_collection.find({'_id.room_id': ObjectId(room_id)}))


def get_rooms_for_user(username):
    return list(room_members_collection.find({'_id.username': username}))


def is_room_member(room_id, username):
    return room_members_collection.count_documents({'_id': {'room_id': ObjectId(room_id), 'username': username}})


def is_room_admin(room_id, username):
    return room_members_collection.count_documents(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'is_room_admin': True})


def save_message(room_id, text, sender, sign,distance):
    messages_collection.insert_one({'type':'bid','_id':ObjectId(), 'room_id': room_id, 
                                'payload': {'text':{'val':[text]}, 
                                'sender': {'val':[sender]}, 
                                'created_at': {'val':[datetime.now()]},
                                'sign':{'val':[sign]},
                                'distance':{'val':[distance]}}})

def get_hb(room_id,username):   #Custom function that gets the highest bid value for a particular auction entry
    bidders=json.loads(get_bidders(room_id))
    print(bidders)
    output_dict = [x for x in bidders if x['sender'] == username]
    return json.dumps(output_dict)


def get_hbidder(room_id): 
    hb=rooms_collection.find_one({'_id': ObjectId(room_id)})
    valor=hb['payload']['highest_bidder']['val'][0]
    return valor

def get_template(room_id):
    hb=rooms_collection.find_one({'_id': ObjectId(room_id)})
    ph=templates_collection.find_one({'temp_type': hb['payload']['templatetype']['val'][0]})
    valor=ph['template']
    return valor


def get_t(temp_type):
    hb=templates_collection.find_one({'temp_type': temp_type})
    valor=hb['template']
    return valor

def get_closing(room_id):   #Custom function that gets the highest bid value for a particular auction entry
    hb=rooms_collection.find_one({'_id': ObjectId(room_id)})
    valort=hb['payload']['closing_time']['val'][0]
    return valort

def update_bid(room_id,highest_bid,highest_bidder,buyersign):
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'payload.highest_bid.val.0': highest_bid}})
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'payload.highest_bidder.val.0': highest_bidder}})
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'payload.buyersign.val.0': buyersign}})

def get_messages(room_id, page=0):
   
    messages = list(
        messages_collection.find({'room_id': room_id}))
    for message in messages:
        message['payload']['created_at']['val'][0] = message['payload']['created_at']['val'][0].strftime("%d %b, %H:%M:%S")
    return messages


def ended(room_id):
    
    highest_bid=get_room(room_id)['payload']['highest_bid']['val'][0]
    highest_bidder=get_hbidder(room_id)
    if highest_bidder:
        template=Template(get_template(room_id))
        room=rooms_collection.find_one({'_id': ObjectId(room_id)})
        room_d=room_details.find_one({'_id': ObjectId(room_id)})
        d=dict(buyer=room['payload']['highest_bidder']['val'][0],quantity=room_d['payload']['quantity']['val'][0], item=room_d['payload']['articleno']['val'][0],ammount=highest_bid,date=room['payload']['closing_time']['val'][0],owner=room['payload']['created_by']['val'][0],buyersign=room['payload']['buyersign']['val'][0],sellersign=room['payload']['sellersign']['val'][0])
        signed_c=template.safe_substitute(d)
        return(signed_c)
    else: return 'no winner was selected'

def get_room_details(room_id):
    return room_details.find_one({ '_id': ObjectId(room_id) })

def get_active_rooms_by_id(room_ids):
    """
    Retrieves active auctions by room ids

    By active it means that a winner has not been selected yet, however
    the closing date may have passed
    """
    return rooms_collection.find({ '_id': { '$in': room_ids }, 'payload.highest_bidder.val': '' })

def get_historical_rooms_by_id(room_ids):
    """
    Retrives historical rooms by room ids. A historical room is a room which has a winner selected.
    """
    return rooms_collection.find({ '_id': { '$in': room_ids }, 'payload.highest_bidder.val': { '$nin': [''] } })

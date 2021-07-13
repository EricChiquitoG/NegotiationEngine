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

client = MongoClient("mongodb+srv://EricTest:test@cluster0.ozw3z.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")

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
    users_collection.insert_one({'_id': username, 'email': email, 'password': password_hash,'sign':hashsign,'location':location})


def get_user(username):
    user_data = users_collection.find_one({'_id': username})
    return User(user_data['_id'], user_data['email'], user_data['password'],user_data['sign'],user_data['location']) if user_data else None

def get_sign(username):
    user_data = users_collection.find_one({'_id': username})
    return user_data['sign']

def find_rooms(room_name,reference_sector,reference_type,ongoing,user ,distance):
    filtro={}
    if room_name is not None: filtro['room_name'] = room_name
    if reference_sector is not None: filtro['reference_sector'] = reference_sector
    if reference_type is not None: filtro['reference_type'] = reference_type
    if ongoing == 'True': filtro['closing_time'] = {'$gte' : datetime.now() }
    # Create a filter for the distance
    
    if distance is not None:
        names,todos = get_distances(user,distance)
        print(todos)
        filtro['created_by']={'$in':names}
    auctions=list(room_details.find(filtro))
    return(JSONEncoder().encode(auctions))


## This function returns a list with the distances relative to the bidder to all the users and filters by distance
def get_distances(bidder,dist):
    base=list(users_collection.find({},{'location':1}))
    for d in base:
        d['dist']=distance_calc(bidder,d['_id'])
        d.pop('location',None)
    filtered_users=[x for x in base if float(x['dist'])<=float(dist) and x['_id']!=bidder]
    my_list = list(map(lambda x: x['_id'], filtered_users))
    return my_list,filtered_users


def distance_calc(bidder,owner):
    distance=geodesic(ast.literal_eval(get_distance(bidder)),ast.literal_eval(get_distance(owner))).km
    return distance

def save_room(room_name, created_by,auction_type, highest_bid,highest_bidder,closing_time,sellersign,buyersign,templatetype):
    room_id = rooms_collection.insert_one(
        {'name': room_name, 'created_by': created_by, 'created_at': datetime.now(),'auction_type':auction_type, 'highest_bid':highest_bid,'highest_bidder':highest_bidder,'closing_time':closing_time,'sellersign':sellersign,'buyersign':buyersign,'templatetype':templatetype}).inserted_id
    add_room_member(room_id, room_name, created_by, created_by, is_room_admin=True)
    return room_id

def save_param(room_id,created_by,room_name,reference_sector,reference_type, quantity, articleno):
    room=rooms_collection.find_one({'_id': ObjectId(room_id)})
    room_details.insert_one({'_id': ObjectId(room_id),'created_by':created_by,'room_name':room_name,'created_at':room['created_at'],'closing_time':room['closing_time'], 'reference_sector':reference_sector,'reference_type':reference_type,'quantity':quantity,'articleno':articleno})

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
    hb=list(messages_collection.aggregate([{'$group':{'_id':'$sender','doc':{'$max':{
                                                                        'text':'$text',
                                                                        'sender':'$sender',
                                                                        'created_at':'$created_at',
                                                                        'distance':'$distance',
                                                                        'sign':'$sign'
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
    dist=users_collection.find_one({'_id':username})
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
    messages_collection.insert_one({'room_id': room_id, 'text': text, 'sender': sender, 'created_at': datetime.now(),'sign':sign,'distance':distance})

def get_hb(room_id,username):   #Custom function that gets the highest bid value for a particular auction entry
    bidders=json.loads(get_bidders(room_id))
    output_dict = [x for x in bidders if x['_id'] == username]
    return json.dumps(output_dict)


def get_hbidder(room_id): 
    hb=rooms_collection.find_one({'_id': ObjectId(room_id)})
    valor=hb['highest_bidder']
    return valor

def get_template(room_id):
    hb=rooms_collection.find_one({'_id': ObjectId(room_id)})
    ph=templates_collection.find_one({'temp_type': hb['templatetype']})
    valor=ph['template']
    return valor


def get_t(temp_type):
    hb=templates_collection.find_one({'temp_type': temp_type})
    valor=hb['template']
    return valor

def get_closing(room_id):   #Custom function that gets the highest bid value for a particular auction entry
    hb=rooms_collection.find_one({'_id': ObjectId(room_id)})
    print(hb)
    valort=hb['closing_time']
    #valort=datetime.strptime(valor, '%Y-%m-%dT%H:%M:%S')

    return valort

def update_bid(room_id,highest_bid,highest_bidder,buyersign):
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'highest_bid': highest_bid}})
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'highest_bidder': highest_bidder}})
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'buyersign': buyersign}})

def get_messages(room_id, page=0):
   
    messages = list(
        messages_collection.find({'room_id': room_id}))
    for message in messages:
        message['created_at'] = message['created_at'].strftime("%d %b, %H:%M:%S")
    return messages


def ended(room_id):
    
    highest_bid=get_room(room_id)['highest_bid']
    highest_bidder=get_hbidder(room_id)
    if highest_bidder:
        template=Template(get_template(room_id))
        room=rooms_collection.find_one({'_id': ObjectId(room_id)})
        room_d=room_details.find_one({'_id': ObjectId(room_id)})
        d=dict(buyer=room['highest_bidder'],quantity=room_d['quantity'], item=room_d['articleno'],ammount=highest_bid,date=room['closing_time'],owner=room['created_by'],buyersign=room['buyersign'],sellersign=room['sellersign'])
        signed_c=template.safe_substitute(d)
        return(signed_c)
    else: return 'no winner was selected'



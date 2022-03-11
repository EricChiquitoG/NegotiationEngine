from codecs import ignore_errors

from datetime import datetime, date
#from turtle import distance

from bson import ObjectId
from pymongo import MongoClient, DESCENDING
from werkzeug.security import generate_password_hash
import uuid
import hashlib
#from app import neg
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
nego=chat_db.get_collection("negotiations")
nego_details=chat_db.get_collection("negotiation_details")

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, (datetime, date)):
            return o.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
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
    
    users_collection.insert_one({'type':'user','_id': ObjectId(),'username':username, 'email': email, 'password': password_hash,'sign':hashsign,'location':location})


def get_user(username):
    user_data = users_collection.find_one({'username': username})
    return User(user_data['username'], user_data['email'], user_data['password'],user_data['sign'],user_data['location']) if user_data else None

def get_sign(username):
    user_data = users_collection.find_one({'username': username})

    return user_data['sign']

# New function that returns auction ids of the public ones
def get_public():
    public=[]
    pub=list(rooms_collection.find({'privacy':"public"}))
    for i in pub:
        public.append(ObjectId(i['_id']))
    
    return public


def find_rooms(room_name,reference_sector,reference_type,ongoing,user ,distance):
    filtro={}



    if room_name is not None: filtro['payload.room_name.val.0'] = room_name
    if reference_sector is not None: filtro['payload.reference_sector.val.0'] = reference_sector
    if reference_type is not None: filtro['payload.reference_type.val.0'] = reference_type
    if ongoing == 'True': filtro['payload.closing_time.val.0'] = {'$gte' : datetime.utcnow() }
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
                to_append={'distance':{'val':['test']}}
                k['payload'].update(to_append)
                k['payload']['distance']['val'][0]=j['dist']


    pub=get_public()
    l=list(filter(lambda d: d['payload']['created_by']['val'][0] in values_of_key, auctions))
    final=list(filter(lambda d: d['_id'] in pub, l))
    return(JSONEncoder().encode(final))


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
    l=list(filter(lambda d: d['created_by'] in my_list, filtered_users))
    return my_list,filtered_users


def distance_calc(bidder,owner):
    distance=geodesic(ast.literal_eval(get_distance(bidder)),ast.literal_eval(get_distance(owner))).km
    return distance

def save_room(privacy, room_name, created_by,auction_type, highest_bid,highest_bidder,closing_time,sellersign,buyersign,templatetype):
    room_id = rooms_collection.insert_one(
        {'type':'auction','_id':ObjectId(),'privacy':privacy,
        'payload':{'name': {'val':[room_name]},
                 'created_by': {'val':[created_by]}, 
                 'created_at': {'val':[datetime.utcnow()]},
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
         'added_at': datetime.utcnow(), 'is_room_admin': is_room_admin})


def add_room_members(room_id, room_name, usernames, added_by):
    room_members_collection.insert_many(
        [{'_id': {'room_id': ObjectId(room_id), 'username': username}, 'room_name': room_name, 'added_by': added_by,
          'added_at': datetime.utcnow(), 'is_room_admin': False} for username in usernames])

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




def is_room_member(room_id, username):
    return room_members_collection.count_documents({'_id': {'room_id': ObjectId(room_id), 'username': username}})


def is_room_admin(room_id, username):
    return room_members_collection.count_documents(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'is_room_admin': True})


def save_message(room_id, text, sender, sign,distance):
    messages_collection.insert_one({'type':'bid','_id':ObjectId(), 'room_id': room_id, 
                                'payload': {'text':{'val':[text]}, 
                                'sender': {'val':[sender]}, 
                                'created_at': {'val':[datetime.utcnow()]},
                                'sign':{'val':[sign]},
                                'distance':{'val':[distance]}}})

def get_hb(room_id,username):   #Custom function that gets the highest bid value for a particular auction entry
    bidders=json.loads(get_bidders(room_id))
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
    #for message in messages:
    #    message['payload']['created_at']['val'][0] = message['payload']['created_at']['val'][0].strftime("%d %b, %H:%M:%S")
    return messages


def ended(room_id, contract_title):
    
    highest_bid=get_room(room_id)['payload']['highest_bid']['val'][0]
    highest_bidder=get_hbidder(room_id)
    if highest_bidder:
        template=Template(get_template(contract_title))
        room=rooms_collection.find_one({'_id': ObjectId(room_id)})
        room_d=room_details.find_one({'_id': ObjectId(room_id)})
        d=dict(buyer=room['payload']['highest_bidder']['val'][0],quantity=room_d['payload']['quantity']['val'][0], item=room_d['payload']['articleno']['val'][0],ammount=highest_bid,date=room['payload']['closing_time']['val'][0],owner=room['payload']['created_by']['val'][0],buyersign=room['payload']['buyersign']['val'][0],sellersign=room['payload']['sellersign']['val'][0])
        signed_c=template.safe_substitute(d)
        return(signed_c)
    else: return 'no winner was selected'

def get_rooms_for_admin(username):
    room_list=  list(room_members_collection.find({'_id.username': username, 'is_room_admin':True}))
    room_names=[]
    for i in room_list:
        room_names.append(i['_id']['room_id'])
    return room_names

def get_rooms_for_user(username):
    room_list= list(room_members_collection.find({'_id.username': username, 'is_room_admin':False}))

    room_names=[]
    for i in room_list:
        room_names.append(i['_id']['room_id'])
    return room_names


def owned_auctions(user_id,owner):
    if owner==True:
        auction_id=(get_rooms_for_admin(user_id))
    else:
        auction_id=(get_rooms_for_user(user_id))
        
    keys=['_id','name','auction_type','created_by','created_at','closing_time','highest_bid']
    owned=[]
    d={}

    auctions=list(rooms_collection.find({'_id':{'$in':auction_id}}))
    
    for i in auctions:
        d.update({'_id':i['_id']})
        d.update({'name':i['payload']['name']['val'][0]})
        d.update({'auction_type':i['payload']['auction_type']['val'][0]})
        d.update({'created_by':i['payload']['created_by']['val'][0]})
        d.update({'created_at':i['payload']['created_at']['val'][0]})
        d.update({'closing_time':i['payload']['closing_time']['val'][0]})
        d.update({'highest_bid':i['payload']['highest_bid']['val'][0]})

        d2=d.copy()
        owned.append(d2)
        

    return JSONEncoder().encode(owned)

# Negotiations____________________________________________

def get_neg(room_id):
    return nego.find_one({'_id': ObjectId(room_id)})

def save_room2(room_name, created_by,seller,highest_bidder,sellersign,buyersign,templatetype, bid,distance):
    room_id = nego.insert_one(
        {'type':'negotiation','_id':ObjectId(),'privacy':'private',
        'payload':{'name': {'val':[room_name]},
                 'created_by': {'val':[created_by]}, 
                 'seller': {'val':[seller]}, 
                 'created_at': {'val':[datetime.utcnow()]},
                 'end_date': {'val':[None]},
                 'current_offer':{'val':[bid]},
                 'offer_user':{'val':[highest_bidder]},
                 'sellersign':{'val':[sellersign]},
                 'buyersign':{'val':[buyersign]},
                 'templatetype':{'val':[templatetype]},
                 'status':{'val':['submitted']}}}).inserted_id

    # Fetching auctions fails if this is added, not sure if it is needed or not
    # but we'll keep it disabled.
    #add_room_member(room_id, room_name, created_by, created_by, is_room_admin=True)
    save_message(room_id,bid,created_by,buyersign,distance)
    return room_id

def save_param2(room_id,created_by,room_name,reference_sector,reference_type, quantity, articleno):
    nego_details.insert_one(
        {'type':'details','_id': ObjectId(room_id),
        'payload':{'room_name':{'val':[room_name]},
                'created_by':{'val':[created_by]},
                'reference_sector':{'val':[reference_sector]},
                'reference_type':{'val':[reference_type]},
                'quantity':{'val':[quantity]},
                'articleno':{'val':[articleno]}}})


# Gets the user data, used for the login system
def get_user(username):
    user_data = users_collection.find_one({'username': username})
    return User(user_data['username'], user_data['email'], user_data['password'],user_data['sign']) if user_data else None

# changes the status of the access permission depending on what is sent and who sends it.
def change_status(req_id, flag,user,offer):
    #The hard coded posibilities is the acceptance and rejection
    access_request=get_neg(req_id)
    
    if flag=='accept' and (access_request['payload']['status']['val'][0]!='accepted' and access_request['payload']['status']['val'][0]!='rejected'):
        nego.update_one({'_id':ObjectId(req_id)}, {'$set': {'payload.status.val.0': 'accepted','payload.end_date.val.0': datetime.utcnow(),'payload.sellersign.val.0':get_sign(access_request['payload']['seller']['val'][0])}})

        return(True)

    elif flag=='reject' and (access_request['payload']['status']['val'][0]!='accepted' and access_request['payload']['status']['val'][0]!='rejected'):
        nego.update_one({'_id':ObjectId(req_id)}, {'$set': {'payload.status.val.0': 'rejected','payload.end_date.val.0': datetime.utcnow()}})

        return(True)
    elif access_request['payload']['status']['val'][0]=='accepted' or access_request['payload']['status']['val'][0]=='rejected':
        return False
    else:
        if user==access_request['payload']['seller']['val'][0]:
            nego.update_one({'_id':ObjectId(req_id)}, {'$set': {'payload.status.val.0': 'counter_offer',}})
            update(req_id,offer,user)
        elif (user==access_request['payload']['created_by']['val'][0]):
            nego.update_one({'_id':ObjectId(req_id)}, {'$set': {'payload.status.val.0': 'offer'}})
            update(req_id,offer,user)

    return('finished')



# Gets the template based on the name
def get_template(temp_type):
    temp_id=templates_collection.find_one({'temp_type':temp_type})
    return temp_id['template']

# Get the signature of the user by its username
def get_sign(uid):
    user_info=users_collection.find_one({'username':uid})
    return user_info['sign']

# Updates the access permission
def update(req_id, offer,user):
    nego.update({'_id':ObjectId(req_id)},{'$set': {'payload.current_offer.val.0':offer, 
                                                                'payload.offer_user.val.0':user,
    }})

# Signs the contract and returns it 
def sign_contract(req_id):
    neg= nego.find_one({'_id':ObjectId(req_id)})
    negd=nego_details.find_one({'_id':ObjectId(req_id)})
    temp_type= "article" # currently hardcoded
    temp=Template(get_template(temp_type))
    d=dict(buyer=neg['payload']['created_by']['val'][0],
        quantity=negd['payload']['quantity']['val'][0],
        item=negd['payload']['articleno']['val'][0],
        ammount=neg['payload']['current_offer']['val'][0],
        date=neg['payload']['end_date']['val'][0],
        owner=neg['payload']['seller']['val'][0],
        buyersign=neg['payload']['buyersign']['val'][0],
        sellersign=neg['payload']['sellersign']['val'][0])
    signed_c=temp.safe_substitute(d)
    # I have the idea to no contracts be saved, but rather they are created whenever they are requested based on the parameters in the db
    #contracts_collection.insert_one({'req_id':ObjectId(req_id), 'provider':neg['provider'],'demander':neg['demander'],'creation_date': datetime.now(),'contract':signed_c})
    return signed_c

def mynegs(uid):

    owned=[]
    d={}

    auctions=list(nego.find({'$or':[{'owner':uid},{'created_by':uid}]}))
    
    for i in auctions:
        d.update({'_id':i['_id']})
        d.update({'name':i['payload']['name']['val'][0]})
        d.update({'created_by':i['payload']['created_by']['val'][0]})
        d.update({'seller':i['payload']['seller']['val'][0]})
        d.update({'created_at':i['payload']['created_at']['val'][0]})
        d.update({'end_date':i['payload']['end_date']['val'][0]})
        d.update({'current_offer':i['payload']['current_offer']['val'][0]})
        d.update({'offer_user':i['payload']['offer_user']['val'][0]})
        d.update({'status':i['payload']['status']['val'][0]})

        d2=d.copy()
        owned.append(d2)
        

    return JSONEncoder().encode(owned)

def neg_info(neg_id):
    neg= list(nego.find({'_id':ObjectId(neg_id)}))
    owned=[]
    d={}
    
    for i in neg:
        d.update({'_id':i['_id']})
        d.update({'name':i['payload']['name']['val'][0]})
        d.update({'created_by':i['payload']['created_by']['val'][0]})
        d.update({'seller':i['payload']['seller']['val'][0]})
        d.update({'created_at':i['payload']['created_at']['val'][0]})
        d.update({'end_date':i['payload']['end_date']['val'][0]})
        d.update({'current_offer':i['payload']['current_offer']['val'][0]})
        d.update({'offer_user':i['payload']['offer_user']['val'][0]})
        d.update({'status':i['payload']['status']['val'][0]})

    d2=d.copy()
    owned.append(d2)
        

    return JSONEncoder().encode(owned)

def flatten_negotiation(n, d):
    return {
        '_id': n['_id'],
        'name': n['payload']['name']['val'][0],
        'created_by': n['payload']['created_by']['val'][0],
        'seller': n['payload']['seller']['val'][0],
        'created_at': n['payload']['created_at']['val'][0],
        'end_date': n['payload']['end_date']['val'][0],
        'current_offer': n['payload']['current_offer']['val'][0],
        'offer_user': n['payload']['offer_user']['val'][0],
        'status': n['payload']['status']['val'][0],
        'reference_sector': d['payload']['reference_sector']['val'][0],
        'reference_type': d['payload']['reference_type']['val'][0],
        'quantity': d['payload']['quantity']['val'][0],
        'articleno': d['payload']['articleno']['val'][0],
        'buyersign': n['payload']['buyersign']['val'][0],
        'sellersign': n['payload']['sellersign']['val'][0],
        'contract_template': n['payload']['templatetype']['val'][0],
    }


def get_negotiation(id):
    negotiation = nego.find_one({ '_id': ObjectId(id) })
    details = nego_details.find_one({ '_id': ObjectId(id) })
    return flatten_negotiation(negotiation, details)


def get_negotiations_by_username(username, count, skip):
    negotiations = list(nego.find({
        '$or': [
            { 'payload.created_by.val.0': username },
            { 'payload.seller.val.0': username },
        ],
    }).sort('_id', 1).skip(skip).limit(count))

    ids = [n['_id'] for n in negotiations]
    details = nego_details.find({ '_id': { '$in': ids }}).sort('_id', 1)

    return [flatten_negotiation(n, d) for (n, d) in zip(negotiations, details)]


def get_rooms_by_username(username):
    """
    Returns all rooms the user is apart of
    """
    room_list = list(room_members_collection.find({ '_id.username': username }))
    room_ids = [room['_id']['room_id'] for room in room_list]
    return room_ids


def get_public_rooms(skip, count):
    rooms = list(rooms_collection.find({ "privacy": "Public"}).sort("_id", 1).skip(skip).limit(count))
    total_rooms = rooms_collection.count_documents({ "privacy": "Public" })
    return (rooms, total_rooms)


def get_room_details(room_id):
    return room_details.find_one({ '_id': ObjectId(room_id) })


def get_all_rooms_by_id(room_ids):
    """
    Retrives rooms by room ids.
    """
    return rooms_collection.find({
        '_id': { '$in': room_ids }
    })


def get_room_details_by_ids(room_ids):
    """
    Retrieves room details from a list of room ids.
    """
    return room_details.find({ '_id': { '$in': room_ids } })


def create_contract(title, body):
    """
    Creates a new contract

    Keys supported in the contract, used with ($key) are
    - title (title of the auction/negotiation)
    - owner (creator)
    - buyer (the other party)
    - quantity (amount to buy/sell)
    - item (the article number)
    - amount (the final price)
    - reference_sector
    - reference_type
    - buyersign (buyer's signature)
    - sellersign (seller's signature)
    - date (date when contract should be signed)
    """
    id = templates_collection.insert_one(
        {
            'temp_type': title,
            'template': body
        }
    ).inserted_id
    return id


def convert_contract(contract):
    """
    Map a contract from the DB format to what we want to send back
    """
    return {
        "_id": contract["_id"],
        "title": contract["temp_type"],
        "body": contract["template"],
    }


def get_contract(id):
    """
    Gets the complete information about a single contract.
    """
    contract = templates_collection.find_one({ "_id": ObjectId(id) })
    if contract is not None:
        return convert_contract(contract)
    return None


def list_contracts():
    """
    Returns a list of all contracts.
    """
    contracts = templates_collection.find({})
    return list(map(convert_contract, contracts))


def create_contract2(template, values):
    s = Template(template["body"]).safe_substitute(values)
    return {
        **values,
        "title": template["title"],
        "body": s,
    }


def sign_auction_contract(auction_id, contract_id):
    template = get_contract(contract_id)
    auction = get_room(auction_id)
    details = get_room_details(auction_id)
    
    values = dict()
    values["title"] = auction["payload"]["name"]["val"][0]
    values["owner"] = auction["payload"]["created_by"]["val"][0]
    values["buyer"] = auction["payload"]["highest_bidder"]["val"][0]
    values["date"] = auction["payload"]["closing_time"]["val"][0]
    values["item"] = details["payload"]["articleno"]["val"][0]
    values["quantity"] = details["payload"]["quantity"]["val"][0]
    values["amount"] = auction["payload"]["highest_bid"]["val"][0]
    values["reference_sector"] = details["payload"]["reference_sector"]["val"][0]
    values["reference_type"] = details["payload"]["reference_type"]["val"][0]
    values["buyersign"] = auction["payload"]["buyersign"]["val"][0]
    values["sellersign"] = auction["payload"]["sellersign"]["val"][0]

    return create_contract2(template, values)


def sign_negotiation_contract(negotiation_id, contract_id):
    template = get_contract(contract_id)
    negotiation = get_negotiation(negotiation_id)

    values = dict()
    values["title"] = negotiation["name"]
    values["owner"] = negotiation["created_by"]
    values["buyer"] = negotiation["seller"]
    values["date"] = negotiation["end_date"]
    values["item"] = negotiation["articleno"]
    values["quantity"] = negotiation["quantity"]
    values["amount"] = negotiation["current_offer"]
    values["reference_sector"] = negotiation["reference_sector"]
    values["reference_type"] = negotiation["reference_type"]
    values["buyersign"] = negotiation["buyersign"]
    values["sellersign"] = negotiation["sellersign"]
    
    return create_contract2(template, values)

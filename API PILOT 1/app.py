from datetime import datetime

from bson.json_util import dumps
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from pymongo.errors import DuplicateKeyError
from string import Template
from geopy.distance import geodesic
import ast
import json
import dateutil.parser

from db import get_bidders,find_rooms,distance_calc,ended,get_template,get_t,get_distance,get_room_admin,save_param,add_room_member,add_room_members,update_bid, get_closing,get_hb,get_sign,get_hbidder, get_messages, get_room, get_room_members, get_rooms_for_user, get_user, is_room_admin, is_room_member, remove_room_members, save_message, save_room, save_user, update_room, get_room_details, get_active_rooms_by_id, get_historical_rooms_by_id, get_room_details_by_ids
from db import JSONEncoder

app = Flask(__name__)


cors = CORS(app)
app.secret_key = "sfdjkafnk"
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# The login route receives the username and password as a POST request

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return {"message":"The user {} is already authenticated".format(current_user)},200

    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password_input = request.form.get('password')
        user = get_user(username)

        if user and user.check_password(password_input):
            login_user(user)
           
            return {"message":"User {} has been authenticated".format(str(user.username))},200
        else:
            message = 'Failed to login!'
    return message,400


# Signup function is not habilitated for the time being, users are to be created either
# by function or directly into the database

@app.route('/signup', methods=['POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    username = request.json.get('username')
    email = request.json.get('email')
    password = request.json.get('password')
    sign=request.json.get('sign')
    location=request.json.get('sign')
    try:
        save_user(username, email, password, sign, location)
        return { 'message': "User created" }, 200
    except DuplicateKeyError:
        return { 'message': "User already exists!" }, 400

##holi={"room_name":"Erics composite auction","members":"","highest_bid":"5000","auction_type":"Ascending","closing_time":"2021-07-06T10:34:20","reference_sector":"Composites","reference_type":"Electronic","quantity":"15","templatetype":"article","articleno":"23dd"}


# A request to this function will log out the user from the server

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return {'message':'the user has logged out'},200


# Use a POST request to create a new auction, user has to be logged in

@app.route('/create-room', methods=['GET', 'POST'])
#@login_required
def create_room():
    if request.method == 'POST':
        privacy= request.form.get('privacy')
        room_name = request.form.get('room_name')
        print(room_name)
        highest_bid=request.form.get('highest_bid')
        highest_bidder=''
        auction_type=request.form.get('auction_type')
        print(request.form.get('closing_time'))
        closing_time=dateutil.parser.isoparse(request.form.get('closing_time'))
        reference_sector=request.form.get('reference_sector')
        reference_type=request.form.get('reference_type')
        quantity=request.form.get('quantity')
        articleno=request.form.get('articleno')
        user=request.authorization.username
        print(user)
        sellersign=get_sign(user)
        buyersign=''
        templatetype=request.form.get('templatetype')
        print(templatetype)
        print(request.form.get('members'))
        if(request.form.get('members')):
            usernames = [username.strip() for username in request.form.get('members').split(',')]
        else: 
            print(user)
            usernames=[user]

        if len(room_name) and len(usernames):
                      
            room_id = save_room(privacy, room_name, user,auction_type,highest_bid,highest_bidder,closing_time,sellersign,buyersign,templatetype)
            save_param(room_id,user,room_name,reference_sector,reference_type,quantity,articleno)
            if user in usernames:
                usernames.remove(user)
            print(len(usernames))
            if len(usernames)>=1:
                print('hay')
                print('usernames')
                add_room_members(room_id, room_name, usernames, user)
            return {"message":"The room {} has been created id: {}".format(str(room_name),room_id)},200
        else:
            return {"message":"Unable to create room"},400


# Edit room also is not enabled but should work with little effort if needed

@app.route('/rooms/<room_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
        room_members_str = ",".join(existing_room_members)
        message = ''
        if request.method == 'POST':
            room_name = request.json.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)

            new_members = [username.strip() for username in request.json.get('members').split(',')]
            members_to_add = list(set(new_members) - set(existing_room_members))
            members_to_remove = list(set(existing_room_members) - set(new_members))
            if len(members_to_add):
                add_room_members(room_id, room_name, members_to_add, current_user.username)
            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            message = 'Room edited successfully'
            room_members_str = ",".join(new_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str, message=message)
    else:
        return "Room not found", 404


# GET request to this route has to include room_id for the room you want to join but no aditional parameters are needed

@app.route('/rooms/<room_id>/join', methods=['GET'])
#@login_required
def join_room(room_id):
    room = get_room(room_id)
    room_name=room['payload']['name']['val'][0]
    user=request.authorization.username

    existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
    if request.method == 'GET':
        new_members = user
        if new_members in list(set(existing_room_members)):
            return {"message":"You are already in a room"},200
        add_room_member(room_id, room_name, new_members, user)

        
    return {"message":"You have joined the room {}".format(str(room_name))},200




# A POST request to this route will receive parameter message_input and will generate a bid to the auction
# A GET request will show all the messages submited to this auction.

@app.route('/rooms/<room_id>', methods=['GET','POST'])
#@login_required
def chat(room_id):
    room = get_room(room_id)
    rn=room['payload']['name']['val'][0]
    closing_time=get_closing(room_id)
    user=request.authorization.username

    if room and is_room_member(room_id, user):
        
        ## The event for the timeout message could go here
        
        if request.method=='POST':
            bid=request.form.get("message_input")
            if (closing_time)>datetime.utcnow():
                print(is_room_admin(room_id,user))
                if(is_room_admin(room_id,user)==0):
                    app.logger.info("{} has summited a new bid to the room {}: {}".format(user,
                                                                            rn,
                                                                            bid))
                    sign=get_sign(user)
                    ## Calculation of distance between users done at every bid
                    print(user,get_room_admin(rn))
                    distance=distance_calc(user,get_room_admin(rn))
                    #
                    save_message(str(room['_id']),bid,user,sign,distance)                    
                else:
                    app.logger.info("Cannot bid if you are Admin")  
                    return{"message":"You cannot issue bids as room admin"},400                          
            else:
                app.logger.info("Auction time has ended")
                return {"message":"The auction {} has already ended".format(str(rn))},400
            return {"message":"You have issued the bid {}".format(str(bid))},200
        elif request.method=='GET':
            messages = get_messages(room_id)
            if room and is_room_member(room_id, user):
                
                ## Here the bids from all users are shown to the user 
                
                keys = ['sender','text', 'created_at','distance']
                d=[]
                for message in messages:
                    m_pay=message['payload']
                    filtered_d = dict((k, m_pay[k]) for k in keys if k in m_pay)
                    d.append(filtered_d)

                body = {"Bids": d}
                
                return jsonify(body),200

    else:
        return "Room not found or user is not member", 404


# A POST request to this auction is used to select the winner with the paremeter "winner" only in case no winner is selected yet
# A GET request in case the auction isnt ended will display the highest bids from all the biders
# and will show the ricardian contract in case the auction is ended

@app.route('/rooms/<room_id>/end', methods=['GET','POST'])
##@login_required
def winner(room_id):
    
    closing_time=get_closing(room_id)
    
    room = get_room(room_id)
    
    rn=room['payload']['name']['val'][0]
    
    user=request.authorization.username
## Withing this function the logic for the winner selection is specified, the admin shall input the username of the winner
    if request.method=='POST':
        
        if(is_room_admin(room_id,user)==1):
            
            if (closing_time)>datetime.utcnow(): #Auction hasnt ended
                    return{"message":"The specified auction hasnt ended"},400
            if get_hbidder(room_id)=='': ## This would mean the auction doesnt have a winner yet
                winner=request.form.get("winner") #Should be username
                wi=json.loads(get_hb(room_id,winner)) ## Get hb should be changed in case the auction is descending
                if wi:
                    for d in wi:
                        sen=d['sender']
                        bid=d['text']
                        sign=d['sign']
                    update_bid(room['_id'],bid,sen,sign)
                    return {"message":"winner has been selected"},200
                else: 
                    return {"message":"User does not participate the auction"},403
            else: 
                return {"message":"the winner for this auciton has already been selected"},200
        else: return{"message":"You are not room admin"},400
    elif request.method=='GET':
        print()
        if user == get_room_admin(rn):
            if get_hbidder(room_id)=='': #Winner hasnt been selected
                return get_bidders(room_id),200
            else: #Winner is selected
                response={'contract':ended(room_id)}
                return jsonify(response),200
        elif (user==get_hbidder(room_id)):
            response={'contract':ended(room_id)}
            return jsonify(response),200
        elif get_hbidder(room_id)=='':
            return {"message":"Winner hasnt been selected"},400
        else: 
            return {"message":"The auction has ended, the winner is {}".format(room['highest_bidder'])},400


            
# A GET request to this route is used to query auction based in the parameters listed below

@app.route('/rooms', methods=['GET'])
#@login_required
def query():
    if request.method=='GET':
        user=request.authorization.username
        room_name=request.json.get("room_name")
        reference_sector=request.json.get("reference_sector")
        reference_type=request.json.get("reference_type")
        ongoing=request.json.get("ongoing")
        distance= request.json.get("distance")
        print(distance, user)
        auctions=find_rooms(room_name,reference_sector,reference_type,ongoing,user,distance)
        return auctions,200


def combine_room_with_room_details(room, room_details):
    """
    Helper to combine a room with room details. Keeps the room mostly intact,
    merging the payload only with room details
    """
    room['payload'] = { **room['payload'], **room_details['payload'] }
    return room

@app.route('/rooms/<room_id>/info', methods=['GET'])
def get_room_info(room_id):
    """
    Returns the complete information about the auction. Combines the result of the
    room, room_details, room_members, and messages (bids) collections.

    Errors:
    - If the privacy is not set to public it checks that the user is a part of the auction,
      if not a 400 Bad Request is returned.
    """
    username = request.authorization.username
    app.logger.info("%s requesting auction %s information", username, room_id)

    room = get_room(room_id)
    if room['privacy'] != 'public' and not is_room_member(room_id, username):
        app.logger.error("%s not authorized to retrieve auction %s", username, room_id)
        return { 'message': 'Not authorized to view this auction' }, 403

    details = get_room_details(room_id)
    members = get_room_members(room_id)
    bids = get_bidders(room_id)
    
    room = combine_room_with_room_details(room, details)
    room['members'] = members
    room['bids'] = json.loads(bids)

    return JSONEncoder().encode(room), 200

@app.route('/rooms/active', methods=['GET'])
def get_active_rooms():
    """
    Returns all the active rooms the user is a part of. Only returns room and room details
    information.

    By active it means that a winner has not been selected yet.
    """
    username = request.authorization.username
    app.logger.info("%s requesting all current auctions the user is part of", username)

    # This isn't ideal since it gets ALL the rooms the user is a part of. Even historical,
    # but it should be fine for smaller amount of rooms.
    room_ids = [room['_id']['room_id'] for room in get_rooms_for_user(username)]
    rooms = list(get_active_rooms_by_id(room_ids))

    # Fetch additional information about rooms.
    active_room_ids = [room['_id'] for room in rooms]
    active_room_details = list(get_room_details_by_ids(active_room_ids))
    details_lookup = { str(room['_id']): room for room in active_room_details }

    # Combine room with details.
    rooms_with_details = [combine_room_with_room_details(room, details_lookup[str(room['_id'])]) for room in rooms ]

    return JSONEncoder().encode(rooms_with_details), 200

@app.route('/rooms/history', methods=['GET'])
def get_history():
    """
    Returns the room history for a specific user. Only returns room and room details
    information.

    The history is all rooms where a winner has been selected.
    """
    username = request.authorization.username
    app.logger.info("%s requesting all historical auctions the user is part of", username)

    room_ids = [room['_id']['room_id'] for room in get_rooms_for_user(username)]
    rooms = list(get_historical_rooms_by_id(room_ids))

    # Fetch additional information about rooms.
    active_room_ids = [room['_id'] for room in rooms]
    active_room_details = list(get_room_details_by_ids(active_room_ids))
    details_lookup = { str(room['_id']): room for room in active_room_details }

    # Combine room with details.
    rooms_with_details = [combine_room_with_room_details(room, details_lookup[str(room['_id'])]) for room in rooms ]
    
    return JSONEncoder().encode(rooms_with_details), 200

@login_manager.user_loader
def load_user(username):
    return get_user(username)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

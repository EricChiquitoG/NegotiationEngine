from datetime import datetime

from bson.json_util import dumps
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room
from pymongo.errors import DuplicateKeyError
from string import Template
from geopy.distance import geodesic
import ast


from db import find_rooms,ended,get_template,get_t,get_distance,get_room_admin,save_param,add_room_member,add_room_members,update_bid, get_closing,get_hb,get_sign,get_hbidder, get_messages, get_room, get_room_members, get_rooms_for_user, get_user, is_room_admin, is_room_member, remove_room_members, save_message, save_room, save_user, update_room

app = Flask(__name__)
app.secret_key = "sfdjkafnk"

socketio = SocketIO(app,cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


@app.route('/')
def home():
    rooms = []
    if current_user.is_authenticated():
        rooms = get_rooms_for_user(current_user.username)
    return render_template("index.html", rooms=rooms)


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
            return {"message":"User {} has been authenticated".format(user)},200
        else:
            message = 'Failed to login!'
    return message,400

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        sign=request.form.get('sign')
        location=request.form.get('sign')
        try:
            save_user(username, email, password,sign,location)
            return redirect(url_for('login'))
        except DuplicateKeyError:
            message = "User already exists!"
    return render_template('signup.html', message=message)


@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/create-room/', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        highest_bid=request.form.get('highest_bid')
        highest_bidder=''
        auction_type=request.form.get('auction_type')
        closing_time=datetime.strptime(request.form.get('closing_time'), '%Y-%m-%dT%H:%M:%S')
        reference_sector=request.form.get('reference_sector')
        reference_type=request.form.get('reference_type')
        quantity=request.form.get('quantity')
        articleno=request.form.get('articleno')
        sellersign=get_sign(current_user.username)
        buyersign=''
        templatetype=request.form.get('templatetype')
        usernames = [username.strip() for username in request.form.get('members').split(',')]

        if len(room_name) and len(usernames):
                      
            room_id = save_room(room_name, current_user.username,auction_type,highest_bid,highest_bidder,closing_time,sellersign,buyersign,templatetype)
            save_param(room_id,room_name,reference_sector,reference_type,quantity,articleno)
            if current_user.username in usernames:
                usernames.remove(current_user.username)
            print(len(usernames))
            if len(usernames)>1:
                add_room_members(room_id, room_name, usernames, current_user.username)
            return {"message":"The room {} has been created".format(str(room_name))},200
        else:
            return {"message":"Unable to create room"},400


@app.route('/rooms/<room_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
        room_members_str = ",".join(existing_room_members)
        message = ''
        if request.method == 'POST':
            room_name = request.form.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)

            new_members = [username.strip() for username in request.form.get('members').split(',')]
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

@app.route('/rooms/<room_id>/join', methods=['GET'])
@login_required
def join_room(room_id):
    room = get_room(room_id)
    room_name=room['name']
    existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
    if request.method == 'GET':
        new_members = current_user.username
        if new_members in list(set(existing_room_members)):
            return {"message":"You are already in a room"},400
        add_room_member(room_id, room_name, new_members, current_user.username)

        
    return {"message":"You have joined the room {}".format(str(room_name))},200


@app.route('/roomss/<room_id>/')
@login_required
def view_room(room_id):
    room = get_room(room_id)
    highest_bid=get_hb(room_id)
    highest_bidder=get_hbidder(room_id)
    if room and is_room_member(room_id, current_user.username):
        room_members = get_room_members(room_id)
        messages = get_messages(room_id)
        ## The event for the timeout message could go here
        return render_template('view_room.html', username=current_user.username, room=room, room_members=room_members,
                               messages=messages,highest_bid=highest_bid,highest_bidder=highest_bidder)
    else:
        return "Room not found", 404



@app.route('/rooms/<room_id>/bids', methods=['GET'])
@login_required
def messages(room_id):
    room = get_room(room_id)
    rn=room['name']
    messages = get_messages(room_id)
    if room and is_room_member(room_id, current_user.username):
        
        ## Here the bids from all users are shown to the user 
        keys = ['sender','text', 'created_at','distance']
        d=[]
        for message in messages:
            filtered_d = dict((k, message[k]) for k in keys if k in message)
            d.append(filtered_d)

        body = {"Bids": d}

        return jsonify(body),200


    else:
        return "Room not found", 404


@app.route('/rooms/<room_id>/', methods=['GET','POST'])
@login_required
def chat(room_id):
    room = get_room(room_id)
    rn=room['name']
    closing_time=get_closing(room_id)
    if room and is_room_member(room_id, current_user.username):
        
        ## The event for the timeout message could go here
        
        if request.method=='POST':
            bid=request.form.get("message_input")
            if (closing_time)>datetime.now():
                print(is_room_admin(room_id,current_user.username))
                if(is_room_admin(room_id,current_user.username)==0):
                    app.logger.info("{} has summited a new bid to the room {}: {}".format(current_user.username,
                                                                            rn,
                                                                            bid))
                    sign=get_sign(current_user.username)
                    ## Calculation of distance between users done at every bid
                    distance=geodesic(ast.literal_eval(get_distance(current_user.username)),ast.literal_eval(get_distance(get_room_admin(rn)))).km
                    print(distance)
                    #
                    save_message(str(room['_id']),bid,current_user.username,sign,distance)
                    if (int(bid)>int(get_hb(room_id))):
                        update_bid(room['_id'],bid,current_user.username,sign)
                        print('Bid is higher')                     
                else:
                    app.logger.info("Cannot bid if you are Admin")  
                    return{"message":"You cannot issue bids as room admin"},400                          
            else:
                app.logger.info("Auction time has ended")
                return {"message":"The auction {} has already ended".format(str(rn))},400
            return {"message":"You have issued the bid {}".format(str(bid))},200
        elif request.method=='GET':
            messages = get_messages(room_id)
            if room and is_room_member(room_id, current_user.username):
                
                ## Here the bids from all users are shown to the user 
                keys = ['sender','text', 'created_at','distance']
                d=[]
                for message in messages:
                    filtered_d = dict((k, message[k]) for k in keys if k in message)
                    d.append(filtered_d)

                body = {"Bids": d}
                if (closing_time)<datetime.now():
                    response={'contract':ended(room_id),'Bids':d}
                    print(is_room_member(room_id, current_user.username))
                    print(get_room_members(room_id))
                    return jsonify(response),200
                return jsonify(body),200

    else:
        return "Room not found or user is not authenticated", 404


@app.route('/rooms/', methods=['GET'])
@login_required
def query():
    if request.method=='GET':
        room_name=request.form.get("room_name")
        reference_sector=request.form.get("reference_sector")
        reference_type=request.form.get("reference_type")
        ongoing=request.form.get("ongoing")
        auctions=find_rooms(room_name,reference_sector,reference_type,ongoing)
        print(auctions)
        return auctions,200





@login_manager.user_loader
def load_user(username):
    return get_user(username)


if __name__ == '__main__':
    socketio.run(app, debug=True)

from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
import logging

from db import (
    neg_info, save_param2,sign_contract,change_status, get_neg,find_rooms,distance_calc,
    add_room_members, save_room2,
    get_sign, get_room, get_room_members, is_room_admin,
    remove_room_members, save_bid, update_room,
    get_negotiations_by_username, get_negotiation, sign_negotiation_contract,
    represented_cont, detect_broker,
)
from db import JSONEncoder
from lib.errors import NEError
from jsonschema import ValidationError

app = Flask(__name__)

from transport.user_transport import *
from transport.broker_transport import *
from transport.contract_transport import *
from transport.auction_transport import *

cors = CORS(app)
app.secret_key = "sfdjkafnk"

logging.basicConfig(level=logging.DEBUG)

@app.errorhandler(NEError)
def ne_errors(error):
    return make_response(
        jsonify({ 'message': error.message, 'code': error.code }),
        error.status_code
    )

@app.errorhandler(400)
def bad_request(error):
    if isinstance(error.description, ValidationError):
        original_error = error.description
        return make_response(jsonify({'error': original_error.message}), 400)
    return error

# Edit room also is not enabled but should work with little effort if needed

@app.route('/rooms/<room_id>/edit', methods=['GET', 'POST'])
def edit_room(room_id):
    username = request.authorization.username
    room = get_room(room_id)
    if room and is_room_admin(room_id, username):
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
                add_room_members(room_id, room_name, members_to_add, username)
            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            message = 'Room edited successfully'
            room_members_str = ",".join(new_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str, message=message)
    else:
        return "Room not found", 404


# A GET request to this route is used to query auction based in the parameters listed below
@app.route('/rooms', methods=['GET'])
#@login_required
def query():
    
    if request.method=='GET':
        user=request.authorization.username
        room_type=request.json.get("room_type")
        room_name=request.json.get("room_name")
        reference_sector=request.json.get("reference_sector")
        reference_type=request.json.get("reference_type")
        ongoing=request.json.get("ongoing")
        distance= request.json.get("distance")
        location=request.json.get("location") ##Needed
        is_broker=request.json.get('is_broker')
        broker_id=request.json.get('broker_id')
        if is_broker:
            broker_contract=represented_cont(broker_id)
            user=broker_contract['represented']
        auctions=find_rooms(room_name,reference_sector,reference_type,ongoing,user,distance,location)
        return auctions,200

# Start negotiation: 
# To be done: Verify validity of inputs, for example, x permision for y database is possible
@app.route("/negotiate", methods=['POST'])
def new_neg():
    room_name = request.form.get('room_name')
    bid=request.form.get('price')
    bidder=request.authorization.username
    seller=request.form.get('seller')
    seller_loc=request.form.get('seller_loc_id') #this parameter should be fed with the location embeded to the offers, shall this be in the url let me know
    reference_sector=request.form.get('reference_sector')
    reference_type=request.form.get('reference_type')
    quantity=request.form.get('quantity')
    articleno=request.form.get('articleno')
    user_location=request.form.get('bid_loc_id')
    buyersign=get_sign(bidder)
    sellersign=''
    templatetype=request.form.get('templatetype')
    distance=distance_calc(user_location,seller_loc)
    is_broker=request.form.get('is_broker')
    broker_id=request.form.get('broker_id')
    if is_broker:
        broker_contract=represented_cont(broker_id)
        bidder=broker_contract['represented']
    
    #The following function may be changed to iterate if multiple roles are requested
    room_id=save_room2(room_name,bidder,seller,seller_loc,sellersign,buyersign,templatetype,bid,distance)
    save_param2(room_id,bidder,room_name,reference_sector,reference_type,quantity,articleno)
    return {"message":"The negotiation with id {} has been created".format(str(room_id))},200


# This is once the negotiation has been created 
@app.route("/negotiate/<neg_id>", methods=['GET','POST'])
def neg(neg_id):
    user = request.authorization.username
    broker_represented=detect_broker(neg_id,user) #Returns name of represented user if true, false otherwise

    user=broker_represented if broker_represented else request.authorization.username
    req = get_neg(neg_id)
    name = req['payload']['name']['val'][0]

    if request.method == 'POST':
        bid = request.form.get('bid')
        creator = req['payload']['created_by']['val'][0]
        participant = req['payload']['seller']['val'][0]
        #neg_loc=req['payload']['location']['val'][0]
        status = req['payload']['status']['val'][0]

        if user in (creator, participant):
            if status not in ('accepted', 'rejected'):
                #distance = distance_calc(bidder_loc, neg_loc) No point in adding distance in every bid as is a p2p
                save_bid('negotiation',neg_id, bid, user, get_sign(user), 'na')
                change_status(neg_id, 1, user, bid)

                return { "message": "New offer submited for request with id {}".format(str(req['_id'])) }, 200
            else:
                return { "message": "The negotiation {} has concluded no more offers can be made".format(str(req['_id'])) }, 403
        else:
            return { "message": 'You are not part of the current negotiation' }, 403
    
    elif (request.method=='GET'):
        status = req['payload']['status']['val'][0]
        if user in (creator, participant):
            if status == 'accepted':
                s = sign_contract(neg_id)
                return  {"Contract": "{}".format(s)}, 200
            else:
                return(neg_info(neg_id)), 200
        else: return{'message':'Cannot access negotiation as user is not part of it'},403


# Only accesible to the owner of such resource, this route accepts the negotiation and begins the contract signing
@app.route("/negotiate/<req_id>/accept", methods=['GET'])
def accept(req_id):
    user=request.authorization.username
    req=get_neg(req_id)
    broker_represented=detect_broker(req_id,user) #Returns name of represented user if true, false otherwise
    user=broker_represented if broker_represented else request.authorization.username
    if user != req['payload']['offer_user']['val'][0]:
        if (user == req['payload']['created_by']['val'][0]) or ((user == req['payload']['seller']['val'][0])):
            flag=change_status(req_id, 'accept',user,0)
            
            ## Add function for contract writing
            if flag: 
                return  {"message":"The negotiation with id {} has been accepted.".format(str(req['_id']))},200
            else:
                return  {"message":"Could not process request, either the accepted auction is already finished or it was declined.".format(str(req['_id']))},200
        else:
            return {"message":'You are not authorized to perform this task'},403
    else:
        return {"message":'Wait for the other peer to accept or counter offer'},403


# Only accesible to the owner of such resource, this route cancels the negotiation.
@app.route("/negotiate/<req_id>/cancel", methods=['GET'])
def cancel(req_id):
    req=get_neg(req_id)
    user=request.authorization.username
    broker_represented=detect_broker(req_id,user) #Returns name of represented user if true, false otherwise

    user=broker_represented if broker_represented else request.authorization.username
    if user != req['payload']['offer_user']['val'][0]:
        if (user == req['payload']['created_by']['val'][0]) or ((user == req['payload']['seller']['val'][0])):
            flag=change_status(req_id, 'reject',user,0)

            ## Add function for contract writing
            if flag: 
                return  {"message":"The negotiation with id {} has been rejected.".format(str(req['_id']))},200
            else:
                return  {"message":"Could not process request, either the accepted auction is already finished or it was declined.".format(str(req['_id']))},200
        else:
            return {"message":'You are not authorized to perform this task'},403
    else:
        return {"message":'You are not allowed to cancel this transaction'},403


@app.route("/negotiate/<neg_id>/full", methods=["GET"])
def get_negotiation_full(neg_id):
    """
    Gets the full information of a negotiation. This includes the negotiation and
    its details.
    """
    username = request.authorization.username
    broker_represented=detect_broker(neg_id,username) #Returns name of represented user if true, false otherwise

    username=broker_represented if broker_represented else request.authorization.username
    app.logger.info("%s requesting negotiation %s", username, neg_id)

    negotiation = get_negotiation(neg_id)
    print(negotiation)
    if negotiation["status"] == "accepted":
        contract_id = negotiation["contract_template"]
        negotiation["contract"] = sign_negotiation_contract(neg_id, contract_id)
    else:
        negotiation["contract"] = ""

    return JSONEncoder().encode(negotiation), 200


@app.route("/negotiate/list", methods=["GET"])
def list_negotiations():
    """
    Gets a list of all the negotiations a user is part of.
    """
    username = request.authorization.username
    is_broker=request.form.get('is_broker')
    broker_id=request.form.get('broker_id')
    if is_broker:
        broker_contract=represented_cont(broker_id)
        username=broker_contract['represented']
    count = request.args.get('count', default=10, type=int)
    skip = request.args.get('skip', default=0, type=int)
    app.logger.info("%s requesting negotiation list, count=%s, skip=%s", username, count, skip)

    negotiations = get_negotiations_by_username(username, count, skip)
    return JSONEncoder().encode(negotiations), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

import dateutil
from datetime import datetime
from pymongo.errors import DuplicateKeyError

from lib.errors import (
    BrokerAlreadyExist,
    AlreadyJoinedAuction,
    CannotRepresentUserNotInAuction,
    CannotJoinPrivate,
    AuctionBiddingEnded,
    AuctionCannotBidAsAdmin,
    AuctionHasWinner,
    NegotiationViewNotAuthorized,
    AuctionNotEnded,
    AuctionUserNotMember,
    AuctionNotAdmin,
)
from lib.util import get_distance

from service.negotiation_service import (
    detect_broker,
    get_negotiation,
    get_negotiations,
    get_negotiations_representing,
    get_public_negotiations,
    get_member_usernames,
)
from service.broker_service import (
    get_valid_agreement,
    has_valid_contract,
    check_broker_agreement,
    has_valid_contract,
)
from service.user_service import get_signature
from service.contract_service import get_contract

from repository.negotiation_repository import (
    save_negotiation,
    save_details,
    save_member,
    save_members,
    get_member_in_negotiation,
    update_broker_for_member,
    save_bid,
    get_bids,
)
from repository.auction_repository import update_auction_winner
from db import sign_auction_contract2


def get_auction(auction_id, username, is_broker=False):
    auction = get_negotiation(
        auction_id, include_details=True, include_bids=True, include_members=True
    )

    member_usernames = get_member_usernames(auction["members"])
    if username not in member_usernames:
        if is_broker:
            # Check if the broker represents any of the members.
            if not has_valid_contract(username, member_usernames):
                raise NegotiationViewNotAuthorized
        else:
            raise NegotiationViewNotAuthorized

    if auction["payload"]["highest_bidder"]["val"][0] != "":
        # Auction has ended
        template_title = auction["payload"]["templatetype"]["val"][0]
        template = get_contract(template_title)
        auction["contract"] = sign_auction_contract2(auction, template)["body"]

    return auction


def get_auctions(username, broker_id, skip, limit):
    if broker_id != "":
        agreement = get_valid_agreement(broker_id)
        username = agreement["represented"]

    sort_by = "payload.closing_time"
    extra_filters = {"status": "active"}
    return get_negotiations(
        username,
        "auction",
        include_details=True,
        sort_by=sort_by,
        filters=extra_filters,
        skip=skip,
        limit=limit,
    )


def get_auction_representations(username, skip, limit):
    sort_by = "payload.closing_time"
    extra_filters = {"status": "active"}
    return get_negotiations_representing(
        username,
        "auction",
        include_details=True,
        sort_by=sort_by,
        filters=extra_filters,
        skip=skip,
        limit=limit,
    )


def get_auctions_ended(username, broker_id, skip, limit):
    if broker_id != "":
        agreement = get_valid_agreement(broker_id)
        username = agreement["represented"]

    extra_filters = {"status": "closed"}
    return get_negotiations(
        username,
        "auction",
        include_details=True,
        filters=extra_filters,
        skip=skip,
        limit=limit,
    )


def get_public_auctions(skip, limit):
    return get_public_negotiations("auction", include_details=True, skip=skip, limit=limit)


def create_auction(username, data):
    represented_by = ""
    if data["broker_id"] != "":
        agreement = get_valid_agreement(data["broker_id"], username)
        (username, represented_by) = (agreement["represented"], username)

    closing_time = dateutil.parser.isoparse(data["closing_time"])
    user_signature = get_signature(username)

    auction_id = save_negotiation(
        "auction",
        data["privacy"],
        {
            "name": data["room_name"],
            "created_by": username,
            "created_at": datetime.utcnow(),
            "auction_type": data["auction_type"],
            "highest_bid": 0,
            "highest_bidder": "",
            "closing_time": closing_time,
            "sellersign": user_signature,
            "buyersign": "",
            "templatetype": data["templatetype"],
            "location": data["location"],
        },
    )

    save_details(
        auction_id,
        "details",
        {
            "room_name": data["room_name"],
            "created_by": username,
            "closing_time": closing_time,
            "reference_sector": data["reference_sector"],
            "reference_type": data["reference_type"],
            "quantity": data["quantity"],
            "articleno": data["offer_id"],
        },
    )

    save_member(
        negotiation_id=auction_id,
        negotiation_name=data["room_name"],
        username=username,
        added_by=username,
        location=data["location"],
        offer_id=data["offer_id"],
        broker_agreement=data["broker_id"],
        represented_by=represented_by,
        is_admin=True,
    )

    if len(data["members"]) > 0:
        save_members(
            negotiation_id=auction_id,
            negotiation_name=data["room_name"],
            added_by=username,
            members=data["members"],
        )

    return auction_id


def join_auction(auction_id, username, location, broker_agreement):
    (username, represented_by) = check_broker_agreement(broker_agreement, username)
    negotiation = get_negotiation(auction_id)
    if negotiation["privacy"] != "public":
        raise CannotJoinPrivate

    try:
        save_member(
            negotiation_id=auction_id,
            username=username,
            room_name=negotiation["payload"]["name"]["val"][0],
            added_by=username,
            location=location,
            offer_id="",
            broker_agreement=broker_agreement,
            represented_by=represented_by,
            is_room_admin=False,
        )
    except DuplicateKeyError:
        raise AlreadyJoinedAuction


def represent_as_broker(auction_id, username, broker_agreement):
    (username, represented_by) = check_broker_agreement(broker_agreement, username)

    member = get_member_in_negotiation(auction_id, username)
    if member is None:
        raise CannotRepresentUserNotInAuction
    if member["broker_agreement"] != "":
        raise BrokerAlreadyExist

    update_broker_for_member(auction_id, username, broker_agreement, represented_by)
    return username


def place_bid(auction_id, username, bid):
    member = get_member_in_negotiation(auction_id, username, include_brokers=True)
    if member is None:
        raise AuctionUserNotMember(auction_id, username)

    # Re-map username if this is a broker.
    username = member["_id"]["username"]

    auction = get_negotiation(auction_id)
    closing_time = auction["payload"]["closing_time"]["val"][0]
    if datetime.utcnow() >= closing_time:
        raise AuctionBiddingEnded

    if member["is_room_admin"]:
        raise AuctionCannotBidAsAdmin

    source_location = auction["payload"]["location"]["val"][0]
    target_location = member["location"]
    distance = get_distance(source_location, target_location)

    user_signature = get_signature(username)
    save_bid(
        negotiation_type="auction",
        negotiation_id=auction_id,
        bid=bid,
        sender=username,
        sign=user_signature,
        distance=distance,
    )


def end_auction(auction_id, username, winner):
    (username, _) = detect_broker(auction_id, username)
    auction = get_negotiation(auction_id)

    auction_creator = auction["payload"]["created_by"]["val"][0]
    if username != auction_creator:
        raise AuctionNotAdmin

    highest_bidder = auction["payload"]["highest_bidder"]["val"][0]
    if highest_bidder != "":
        raise AuctionHasWinner(auction_id)

    closing_time = auction["payload"]["closing_time"]["val"][0]
    if datetime.utcnow() <= closing_time:
        raise AuctionNotEnded(auction_id)

    auction_type = auction["payload"]["auction_type"]["val"][0]
    bids = get_bids(auction_id, auction_type)
    winning_bid = None
    for bid in bids:
        if bid["sender"] == winner:
            winning_bid = bid
            break

    if winning_bid is None:
        raise AuctionUserNotMember(auction_id, winner)

    bid_value = winning_bid["text"]
    signature = winning_bid["sign"]
    update_auction_winner(auction_id, winner, bid_value, signature)

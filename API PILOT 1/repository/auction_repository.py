from bson import ObjectId

from lib.mongo import (
    negotiation_collection,
)


def update_auction_winner(auction_id, username, bid, signature):
    filter_by = {"_id": ObjectId(auction_id)}
    update = {
        "$set": {
            "status": "closed",
            "payload.highest_bidder.val.0": username,
            "payload.highest_bid.val.0": bid,
            "payload.buyersign.val.0": signature,
        }
    }

    negotiation_collection.update_one(filter_by, update)

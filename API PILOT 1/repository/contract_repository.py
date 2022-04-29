from bson import ObjectId

from lib.mongo import templates_collection

# Contract types.
USED_FOR_AUCTION = "auction"
USED_FOR_NEGOTATION = "negotiation"
USED_FOR_BROKER = "broker"


# Default created contracts
AUCTION_CONTRACT = "article"
BROKER_CONTRACT = "broker"


def create_contract(title, used_for, body):
    """
    Creates a new contract
    """
    return templates_collection.insert_one(
        {"title": title, "used_for": used_for, "body": body}
    ).inserted_id


def get_contract(id):
    """
    Gets the complete information about a single contract.
    """
    return templates_collection.find_one({"_id": ObjectId(id)})


def get_contract_by_title(title):
    """
    Gets the complete information about a single contract from the title.
    """
    return templates_collection.find_one({"title": title})


def list_contracts(used_for):
    return list(templates_collection.find({"used_for": used_for}))


def if_not_exists_create_initial_contracts():
    """
    Creates initial contracts unless they already exist
    """
    if get_contract_by_title(BROKER_CONTRACT) is None:
        title = BROKER_CONTRACT
        template = "broker contents"
        create_contract(title, USED_FOR_BROKER, template)

    if get_contract_by_title(AUCTION_CONTRACT) is None:
        title = AUCTION_CONTRACT
        template = "Hereby I $buyer, declare the purchase of $quantity units of $item for the ammount of $amount SEK on $date from $owner. \nBuyer signature $buyersign \nSeller signature $sellersign"
        create_contract(title, USED_FOR_AUCTION, template)


# Create intitial contracts
if_not_exists_create_initial_contracts()

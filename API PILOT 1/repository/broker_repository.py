from datetime import datetime
from bson import ObjectId

from lib.mongo import broker_collection
from lib.errors import BrokerAgreementNotFound


def get_agreement(agreement_id):
    result = broker_collection.find_one({"_id": ObjectId(agreement_id)})
    if result is None:
        raise BrokerAgreementNotFound(agreement_id)
    return result


def get_agreements(username, skip, limit):
    filter_by = {
        "$or": [
            {"representant": username},
            {"represented": username},
        ]
    }
    agreements = broker_collection.find(filter_by).sort("_id", 1).skip(skip).limit(limit)
    total = broker_collection.count_documents(filter_by)
    return (list(agreements), total)


def get_active_agreements(username, skip, limit):
    filter_by = {
        "$or": [
            {"representant": username},
            {"represented": username},
        ],
        "end_date": {"$gte": datetime.utcnow()},
        "representant_signature": {"$ne": ""},
        "represented_signature": {"$ne": ""},
    }
    agreements = broker_collection.find(filter_by).sort("_id", 1).skip(skip).limit(limit)
    total = broker_collection.count_documents(filter_by)
    return (list(agreements), total)


def get_pending_agreements(username, skip, limit):
    filter_by = {
        "$or": [
            {"representant": username, "represented_signature": ""},
            {"represented": username, "representant_signature": ""},
        ]
    }
    agreements = broker_collection.find(filter_by).sort("_id", 1).skip(skip).limit(limit)
    total = broker_collection.count_documents(filter_by)
    return (list(agreements), total)


def create_agreement(
    title,
    representant,
    represented,
    end_date,
    template_id,
    representant_signature,
    represented_signature,
):
    data = {
        "title": title,
        "status": "pending",
        "representant": representant,
        "represented": represented,
        "start_date": datetime.utcnow(),
        "end_date": end_date,
        "representant_signature": representant_signature,
        "represented_signature": represented_signature,
        "template_id": template_id,
        "contract_content": "",
    }
    return broker_collection.insert_one(data).inserted_id


def accept_agreement(agreement, contract, representant_signature, represented_signature):
    filter_by = {"_id": agreement["_id"]}
    update = {
        "status": "accepted",
        "representant_signature": representant_signature,
        "represented_signature": represented_signature,
        "contract_content": contract,
    }
    broker_collection.update_one(filter_by, {"$set": update})


def reject_agreement(agreement):
    filter_by = {"_id": agreement["_id"]}
    update = {"status": "rejected"}
    broker_collection.update_one(filter_by, {"$set": update})

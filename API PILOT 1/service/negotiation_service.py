from lib.errors import NegotiationNotFound
import repository.negotiation_repository as negotiation_repository


def get_negotiation(
    negotiation_id, include_details=False, include_bids=False, include_members=False
):
    negotiation = negotiation_repository.get_negotiation(negotiation_id)
    if negotiation is None:
        raise NegotiationNotFound

    return fill_details(negotiation, include_details, include_bids, include_members)


def get_negotiations(
    username,
    negotiation_type,
    include_details=False,
    include_bids=False,
    include_members=True,
    skip=0,
    limit=20,
):
    all_negotiation_ids = negotiation_repository.get_negotiation_membership_ids(username)
    (negotiations, total) = negotiation_repository.get_negotiations(
        all_negotiation_ids, negotiation_type, skip, limit
    )

    if include_details or include_bids or include_members:
        negotiations = [
            fill_details(n, include_details, include_bids, include_members) for n in negotiations
        ]

    return (negotiations, total)


def fill_details(negotiation, include_details=False, include_bids=False, include_members=False):
    n_id = negotiation["_id"]
    if include_details:
        details = negotiation_repository.get_details(n_id)
        negotiation["payload"] = {**details["payload"], **negotiation["payload"]}

    if include_bids:
        negotiation_type = negotiation["payload"]["auction_type"]["val"][0]
        negotiation["bids"] = negotiation_repository.get_bids(n_id, negotiation_type)

    if include_members:
        negotiation["members"] = negotiation_repository.get_members_in_negotiation(n_id)

    return negotiation


def detect_broker(negotiation_id, username):
    member = negotiation_repository.get_member_by_represented(negotiation_id, username)
    if member is None:
        return (username, "")
    else:
        represented = member["_id"]["username"]
        return (represented, username)

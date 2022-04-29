class NEError(Exception):
    status_code = 500


class NENotFound(NEError):
    status_code = 404


class NEBadRequest(NEError):
    status_code = 400


class NEUnauthorized(NEError):
    status_code = 403


# -----------------------------------------------------------------------------
# User
# -----------------------------------------------------------------------------


class NotAuthenticated(NEUnauthorized):
    def __init__(self):
        self.message = "This endpoint requires authorization with a username"
        self.code = 100


# -----------------------------------------------------------------------------
# Contracts
# -----------------------------------------------------------------------------


class ContractNotFound(NENotFound):
    def __init__(self):
        self.message = "Contract not found"
        self.code = 500


# -----------------------------------------------------------------------------
# Broker
# -----------------------------------------------------------------------------


class BrokerAgreementNotFound(NENotFound):
    def __init__(self, agreement_id):
        self.message = "Broker agreement {} not found {}".format(agreement_id)
        self.code = 600


class BrokerAgreementNotAuthorized(NEUnauthorized):
    def __init__(self):
        self.message = "Not authorized to perform this action"
        self.code = 601


class BrokerAgreementExpired(NEUnauthorized):
    def __init__(self):
        self.message = "Broker agreement expired"
        self.code = 602

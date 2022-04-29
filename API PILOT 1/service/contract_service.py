from string import Template

from lib.errors import ContractNotFound

import repository.contract_repository as contract_repository
from db import get_sign as get_signature


def get_contract(contract_id):
    contract = contract_repository.get_contract(contract_id)
    if contract is None:
        raise ContractNotFound
    return contract


def get_contracts(user_for):
    return contract_repository.list_contracts(user_for)


def create_contract(title, used_for, body):
    return contract_repository.create_contract(title, used_for, body)


def sign_contract(contract, values):
    template = contract["body"]
    return Template(template).safe_substitute(values)

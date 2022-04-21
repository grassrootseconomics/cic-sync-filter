# external imports
from eth_erc20 import ERC20
from erc20_faucet import Faucet
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.encode import TxHexNormalizer
from hexathon import add_0x

tx_normalize = TxHexNormalizer()


def parse_transfer(tx, conn, chain_spec, caller_address=ZERO_ADDRESS):
    if not tx.payload:
        return (None, None)
    r = ERC20.parse_transfer_request(tx.payload)
    transfer_data = {}
    transfer_data['to'] = tx_normalize.wallet_address(r[0])
    transfer_data['value'] = r[1]
    transfer_data['from'] = tx_normalize.wallet_address(tx.outputs[0])
    transfer_data['token_address'] = tx.inputs[0]
    return ('transfer', transfer_data)


def parse_transferfrom(tx, conn, chain_spec, caller_address=ZERO_ADDRESS):
    if not tx.payload:
        return (None, None)
    r = ERC20.parse_transfer_from_request(tx.payload)
    transfer_data = {}
    transfer_data['from'] = tx_normalize.wallet_address(r[0])
    transfer_data['to'] = tx_normalize.wallet_address(r[1])
    transfer_data['value'] = r[2]
    transfer_data['token_address'] = tx.inputs[0]
    return ('transferfrom', transfer_data)


def parse_gas(tx, conn, chain_spec, caller_address=ZERO_ADDRESS):
    r = (None, None,)
    if tx.value > 0 or len(tx.payload) == 0:
        transfer_data = {}
        transfer_data['to'] = tx_normalize.wallet_address(tx.inputs[0])
        transfer_data['from'] = tx_normalize.wallet_address(tx.outputs[0])
        transfer_data['value'] = tx.value
        transfer_data['token_address'] = None
        r = ('gas', transfer_data,)
    else:
        logg.info('value {} payload {}'.format(tx.value, tx.payload))
    return r


def parse_giftto(tx, conn, chain_spec, caller_address=ZERO_ADDRESS):
    if not tx.payload:
        return (None, None)
    r = Faucet.parse_give_to_request(tx.payload)
    transfer_data = {}
    transfer_data['to'] = tx_normalize.wallet_address(r[0])
    transfer_data['value'] = tx.value
    transfer_data['from'] = tx_normalize.wallet_address(tx.outputs[0])
    #transfer_data['token_address'] = tx.inputs[0]
    faucet_contract = tx.inputs[0]

    c = Faucet(chain_spec)

    o = c.token(faucet_contract, sender_address=caller_address)
    r = conn.do(o)
    transfer_data['token_address'] = add_0x(c.parse_token(r))

    o = c.token_amount(faucet_contract, sender_address=caller_address)
    r = conn.do(o)
    transfer_data['value'] = c.parse_token_amount(r)

    return ('tokengift', transfer_data)



def parse_register(tx, conn, chain_spec, caller_address=ZERO_ADDRESS):
    if not tx.payload:
        return (None, None)
    r = AccountRegistry.parse_add_request(tx.payload)
    transfer_data = {
        'value': None,
        'token_address': None,
            }
    transfer_data['to'] = tx_normalize.wallet_address(r)
    transfer_data['from'] = tx_normalize.wallet_address(tx.outputs[0])
    return ('account_register', transfer_data,)


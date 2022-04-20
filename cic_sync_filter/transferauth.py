# standard imports
import logging

# external imports
import celery
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainlib.eth.address import to_checksum_address
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.contract import (
        ABIContractType,
        abi_decode_single,
        )
from cic_eth_registry import CICRegistry
from erc20_transfer_authorization import TransferAuthorization

# local imports
from cic_eth.encode import tx_normalize
from .base import SyncFilter


logg = logging.getLogger(__name__)


class TransferAuthFilter(SyncFilter):

    def __init__(self, registry, chain_spec, conn, queue=None, call_address=ZERO_ADDRESS):
        self.queue = queue
        self.chain_spec = chain_spec
        registry = CICRegistry(chain_spec, conn)
        self.transfer_request_contract = registry.by_name('TransferAuthorization', sender_address=call_address)


    def filter(self, conn, block, tx, db_session): #rcpt, chain_str, session=None):

        if tx.payload == None:
            logg.debug('no payload')
            return False

        payloadlength = len(tx.payload)
        if payloadlength != 8+256:
            logg.debug('{} below minimum length for a transfer auth call'.format(payloadlength))
            logg.debug('payload {}'.format(tx.payload))
            return False

        recipient = tx.inputs[0]
        #if recipient != self.transfer_request_contract.address():
        if recipient != self.transfer_request_contract:
            logg.debug('not our transfer auth contract address {}'.format(recipient))
            return False

        r = TransferAuthorization.parse_create_request_request(tx.payload) 
          
        sender = tx_normalize.wallet_address(r[0])
        recipient = tx_normalize.wallet_address(r[1])
        token = tx_normalize.executable_address(r[2])
        value = r[3]

        token_data = {
            'address': token,
            }

        s_nonce = celery.signature(
            'cic_eth.eth.nonce.reserve_nonce',
            [
                [token_data],
                self.chain_spec.asdict(), 
                sender,
                ],
            queue=self.queue,
            )
        s_approve = celery.signature(
            'cic_eth.eth.erc20.approve',
            [
                sender,
                recipient,
                value,
                self.chain_spec.asdict(),
                ],
            queue=self.queue,
            )
        s_nonce.link(s_approve)
        t = s_nonce.apply_async()
        return t


    def __str__(self):
        return 'cic-eth transfer auth filter'

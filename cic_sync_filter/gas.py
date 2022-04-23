# standard imports
import logging

# external imports
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainlib.eth.tx import unpack
from chainqueue.db.enum import StatusBits
#from chainqueue.db.models.tx import TxCache
#from chainqueue.db.models.otx import Otx
from chainlib.eth.address import to_checksum_address
#from cic_eth.db.models.base import SessionBase
from cic_eth.queue.query import get_account_tx_local
from cic_eth.eth.gas import create_check_gas_task
from cic_eth.queue.query import get_paused_tx

# local imports
from cic_eth.encode import tx_normalize
from .base import SyncFilter

logg = logging.getLogger()


class GasFilter(SyncFilter):

    def filter(self, conn, block, tx):
        super(GasFilter, self).filter(conn, block, tx)
        if tx.value > 0 or len(tx.payload) == 0:
            tx_hash_hex = add_0x(tx.hash)

            sender_target = tx_normalize.wallet_address(tx.inputs[0])
            txc = get_account_tx_local(self.chain_spec, sender_target, as_recipient=False)

            logline = None
            if len(txc) == 0:
                logline = 'unsolicited gas refill tx {}; cannot find {} among senders'.format(tx_hash_hex, sender_target)
                logline = self.to_logline(block, tx, logline)
                logg.info(logline)
                return None

            self.register_match()

            txs = get_paused_tx(self.chain_spec, status=StatusBits.GAS_ISSUES, sender=sender_target, decoder=unpack)

            t = None
            address = to_checksum_address(sender_target)
            if len(txs) > 0:
                s = create_check_gas_task(
                        list(txs.values()),
                        self.chain_spec,
                        address,
                        0,
                        tx_hashes_hex=list(txs.keys()),
                        queue=self.queue,
                )
                t = s.apply_async()
                logline = 'resuming {} gas-in-waiting txs for {}'.format(len(txs), sender_target)
            else:
                logline = 'gas refill tx {}'.format(tx)

            logline = self.to_logline(block, tx, logline)
            logg.info(logline)
            return t


    def __str__(self):
        return 'gasfilter'

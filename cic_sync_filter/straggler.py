# standard imports
import logging

# external imports
import celery
from chainqueue.error import TxStateChangeError
from hexathon import to_int as hex_to_int
from chainlib.eth.gas import balance
from cic_eth.queue.query import get_tx_cache_local
from cic_eth.queue.state import (
        obsolete_local,
        set_fubar_local,
        )
from chainqueue.enum import StatusBits

# local imports
from .base import SyncFilter

logg = logging.getLogger()


class StragglerFilter(SyncFilter):

    gas_balance_threshold = 0

    def filter(self, conn, block, tx):
        txc = get_tx_cache_local(self.chain_spec, tx.hash)
        if txc['status_code'] & StatusBits.GAS_ISSUES > 0:
            o = balance(tx.outputs[0])
            r = conn.do(o)
            gas_balance = hex_to_int(r)

            t = None
            if gas_balance < self.gas_balance_threshold:
                logg.debug('WAITFORGAS tx ignored since gas balance {} is below threshold {}'.format(gas_balance, self.gas_balance_threshold))
                s_touch = celery.signature(
                        'cic_eth.queue.state.set_checked',
                        [
                            self.chain_spec.asdict(),
                            tx.hash,
                            ],
                        queue=self.queue,
                )
                t = s_touch.apply_async()
                return t


        try:
            obsolete_local(self.chain_spec, tx.hash, False)
        except TxStateChangeError:
            set_fubar_local(self.chain_spec, tx.hash, session=db_session)
            return False

        s_send = celery.signature(
                'cic_eth.eth.gas.resend_with_higher_gas',
                [
                    tx.hash,
                    self.chain_spec.asdict(),
                ],
                queue=self.queue,
        )
        t = s_send.apply_async()
        return t


    def __str__(self):
        return 'stragglerfilter'

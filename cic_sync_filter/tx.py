# standard imports
import logging

# external imports
import celery
from hexathon import (
        add_0x,
        )
from chainlib.status import Status
from cic_eth.queue.query import get_tx_local
from chainqueue.error import NotLocalTxError

# local imports
from .base import SyncFilter

logg = logging.getLogger(__name__)


class TxFilter(SyncFilter):

    def filter(self, conn, block, tx, db_session=None):
        super(TxFilter, self).filter(conn, block, tx, db_session=db_session)

        try:
            get_tx_local(self.chain_spec, tx.hash)
        except NotLocalTxError:
            logg.debug('tx {} not found locally'.format(tx.hash))
            return None

        self.register_match()

        s_final_state = celery.signature(
                'cic_eth.queue.state.set_final',
                [
                    self.chain_spec.asdict(),
                    add_0x(tx.hash),
                    tx.block.number,
                    tx.index,
                    tx.status == Status.ERROR,
                    ],
                queue=self.queue,
                )
        s_obsolete_state = celery.signature(
                'cic_eth.queue.state.obsolete',
                [
                    self.chain_spec.asdict(),
                    add_0x(tx.hash),
                    True,
                    ],
                queue=self.queue,
                )
        t = celery.group(s_obsolete_state, s_final_state)()

        logline = 'otx filter match on {}'.format(tx.hash)
        logline = self.to_logline(block, tx, logline)
        logg.info(logline)

        return t


    def __str__(self):
        return 'otx filter'

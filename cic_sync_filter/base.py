# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainsyncer.filter import SyncFilter as BaseSyncFilter


class SyncFilter(BaseSyncFilter):
    
    def __init__(self, chain_spec, registry, queue, caller_address=ZERO_ADDRESS):
        super(SyncFilter, self).__init__()
        self.exec_count = 0
        self.match_count = 0
        self.queue = queue
        self.chain_spec = chain_spec
        self.registry = registry
        self.caller_address = caller_address


    def filter(self, conn, block, tx):
        self.exec_count += 1


    def register_match(self):
        self.match_count += 1


    def to_logline(self, block, tx, v):
        return '{} exec {} match {} block {} tx {}: {}'.format(self, self.exec_count, self.match_count, block.number, tx.index, v)

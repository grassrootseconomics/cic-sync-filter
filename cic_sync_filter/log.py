from .base import SyncFilter


class LogFilter(SyncFilter):
    
    def filter(self, conn, block, tx):
        logg.debug('block {} tx {}'.format(block, tx))



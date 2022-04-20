from .base import SyncFilter


class LogFilter(SyncFilter):
    
    def filter(self, conn, block, tx, db_session=None):
        logg.debug('block {} tx {}'.format(block, tx))



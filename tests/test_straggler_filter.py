# standard imports
import logging

# external imports
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import (
        OverrideNonceOracle,
        RPCNonceOracle,
        )
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        Tx,
        receipt,
        )
from chainlib.eth.gas import (
        Gas,
        OverrideGasOracle,
        )
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainqueue.db.models.otx import Otx
from chainqueue.db.enum import StatusBits
from chainqueue.sql.tx import create as queue_create
from chainqueue.sql.state import (
        set_reserved,
        set_ready,
        set_sent,
        set_waitforgas,
        )

from hexathon import (
        strip_0x,
        uniform as hex_uniform,
        )

# local imports
from cic_eth.runnable.daemons.filters.straggler import StragglerFilter
from cic_eth.eth.gas import cache_gas_data
from cic_eth.queue.query import (
        get_tx_local,
        get_account_tx_local,
        )

logg = logging.getLogger()


def test_straggler_tx(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
    queue_create(
            default_chain_spec,
            42,
            agent_roles['ALICE'],
            tx_hash_hex,
            tx_signed_raw_hex,
            session=init_database,
            )
    cache_gas_data(
            tx_hash_hex,
            tx_signed_raw_hex,
            default_chain_spec.asdict(),
            )

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex, session=init_database)

    fltr = StragglerFilter(default_chain_spec, 0, queue=None)

    o = block_latest()
    r = eth_rpc.do(o)
    o = block_by_number(r, include_tx=False)
    r = eth_rpc.do(o)
    block = Block(r)
    block.txs = [tx_hash_hex]

    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx_src = unpack(tx_signed_raw_bytes, default_chain_spec)
    tx = Tx(tx_src, block=block)
    t = fltr.filter(None, block, tx, db_session=init_database)
    logg.debug('foo')
    tx_hash_hex_successor = t.get_leaf()
    logg.debug('bar')

    assert t.successful()
    assert tx_hash_hex_successor != tx_hash_hex

    otx = Otx.load(tx_hash_hex, session=init_database)
    assert otx.status & StatusBits.OBSOLETE > 0
    assert otx.status & (StatusBits.FINAL | StatusBits.QUEUED | StatusBits.RESERVED) == 0

    otx = Otx.load(tx_hash_hex_successor, session=init_database)
    assert otx.status == StatusBits.QUEUED



def test_waitforgas_tx(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        celery_session_worker,
        whoever,
        ):

    safe_gas = 1000000000000000000

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(whoever, 0)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(whoever, agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
    queue_create(
            default_chain_spec,
            0,
            whoever,
            tx_hash_hex,
            tx_signed_raw_hex,
            session=init_database,
            )
    cache_gas_data(
            tx_hash_hex,
            tx_signed_raw_hex,
            default_chain_spec.asdict(),
            )

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_waitforgas(default_chain_spec, tx_hash_hex, session=init_database)

    fltr = StragglerFilter(default_chain_spec, safe_gas, queue=None)
     
    o = block_latest()
    r = eth_rpc.do(o)
    o = block_by_number(r, include_tx=False)
    r = eth_rpc.do(o)
    block = Block(r)
    block.txs = [tx_hash_hex]

    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx_src = unpack(tx_signed_raw_bytes, default_chain_spec)
    tx = Tx(tx_src, block=block)

    t = fltr.filter(eth_rpc, block, tx, db_session=init_database)
    t.get_leaf()
    assert t.successful()

    otx = get_tx_local(default_chain_spec, tx.hash, session=init_database)
    assert otx['status'] == StatusBits.GAS_ISSUES
 
    nonce_oracle = RPCNonceOracle(agent_roles['CAROL'], conn=eth_rpc)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = c.create(agent_roles['CAROL'], whoever, safe_gas - 1)
    r = eth_rpc.do(o)

    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1


    t = fltr.filter(eth_rpc, block, tx, db_session=init_database)
    t.get_leaf()
    assert t.successful()

    otx = get_tx_local(default_chain_spec, tx.hash, session=init_database)
    assert otx['status'] == StatusBits.GAS_ISSUES
 

    nonce_oracle = RPCNonceOracle(agent_roles['CAROL'], conn=eth_rpc)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = c.create(agent_roles['CAROL'], whoever, 1)
    r = eth_rpc.do(o)

    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    init_database.commit()

    t = fltr.filter(eth_rpc, block, tx, db_session=init_database)
    t.get_leaf()
    
    otx = get_tx_local(default_chain_spec, tx.hash, session=init_database)
    assert otx['status'] & StatusBits.OBSOLETE > 0

    txs = get_account_tx_local(default_chain_spec, whoever, session=init_database)
    assert len(txs.keys()) == 2
    for k in txs.keys():
        if hex_uniform(strip_0x(tx.hash)) != hex_uniform(strip_0x(k)):
            otx = get_tx_local(default_chain_spec, k, session=init_database)
            assert otx['status'] == StatusBits.QUEUED
 

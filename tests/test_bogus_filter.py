# local imports
from cic_sync_filter.gas import GasFilter
from cic_sync_filter.transferauth import TransferAuthFilter
from cic_sync_filter.callback import CallbackFilter
from cic_sync_filter.straggler import StragglerFilter
from cic_sync_filter.tx import TxFilter
from cic_sync_filter.register import RegistrationFilter


# Hit tx mismatch paths on all filters
def test_filter_bogus(
        init_database,
        bogus_tx_block,
        default_chain_spec,
        eth_rpc,
        eth_signer,
        transfer_auth,
        cic_registry,
        contract_roles,
        register_lookups,
        account_registry,
        ):

    fltrs = [
        TransferAuthFilter(cic_registry, default_chain_spec, eth_rpc, call_address=contract_roles['CONTRACT_DEPLOYER']),
        GasFilter(default_chain_spec, queue=None),
        TxFilter(default_chain_spec, None),
        CallbackFilter(default_chain_spec, None, None, caller_address=contract_roles['CONTRACT_DEPLOYER']),
        StragglerFilter(default_chain_spec, None),
        RegistrationFilter(default_chain_spec, account_registry, queue=None),
        ]
      
    for fltr in fltrs:
        r = None
        try:
            r = fltr.filter(eth_rpc, bogus_tx_block[0], bogus_tx_block[1], db_session=init_database)
        except:
            pass
        assert not r

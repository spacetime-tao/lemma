# Lemma Reward Custody Contract

`LemmaBountyEscrow` is the custody path for Lemma proof-formalization rewards
on Bittensor EVM. It is configured for Subtensor EVM testnet and mainnet, not
Ethereum mainnet.

```bash
cd contracts
npm install
npm test
npm run export-abi
```

Network defaults match the Bittensor docs:

- testnet RPC: `https://test.chain.opentensor.ai`, chain id `945`
- mainnet RPC: `https://lite.chain.opentensor.ai`, chain id `964`

The contract has no withdraw, sweep, or manual payout method. Rewards are
released only through commitment, reveal, validator attestations, challenge
window finality, and the fixed payout address from the winning reveal.

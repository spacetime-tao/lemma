require("@nomicfoundation/hardhat-toolbox");

const TESTNET_RPC = process.env.BITTENSOR_EVM_TESTNET_RPC_URL || "https://test.chain.opentensor.ai";
const MAINNET_RPC = process.env.BITTENSOR_EVM_MAINNET_RPC_URL || "https://lite.chain.opentensor.ai";
const DEPLOYER_KEY = process.env.BITTENSOR_EVM_DEPLOYER_PRIVATE_KEY || "";

const accounts = DEPLOYER_KEY ? [DEPLOYER_KEY] : [];

module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hardhat: {},
    bittensorTestnet: {
      url: TESTNET_RPC,
      chainId: 945,
      accounts
    },
    bittensorMainnet: {
      url: MAINNET_RPC,
      chainId: 964,
      accounts
    }
  }
};

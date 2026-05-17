const hre = require("hardhat");

async function main() {
  const Escrow = await hre.ethers.getContractFactory("LemmaBountyEscrow");
  const escrow = await Escrow.deploy();
  await escrow.waitForDeployment();
  console.log(`LemmaBountyEscrow=${await escrow.getAddress()}`);
  console.log(`network=${hre.network.name} chainId=${(await hre.ethers.provider.getNetwork()).chainId}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

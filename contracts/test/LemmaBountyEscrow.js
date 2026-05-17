const { expect } = require("chai");
const { ethers, network } = require("hardhat");

const b32 = (text) => ethers.id(text);

async function mineBlocks(count) {
  for (let i = 0; i < count; i++) {
    await network.provider.send("evm_mine");
  }
}

async function deployFixture() {
  const [owner, claimant, payout, validatorA, validatorB, validatorC, stranger] = await ethers.getSigners();
  const Escrow = await ethers.getContractFactory("LemmaBountyEscrow");
  const escrow = await Escrow.deploy();
  await escrow.waitForDeployment();
  return { escrow, owner, claimant, payout, validatorA, validatorB, validatorC, stranger };
}

async function createBounty(escrow, validators, value = ethers.parseEther("1")) {
  const block = await ethers.provider.getBlockNumber();
  const tx = await escrow.createBounty(
    b32("fc.demo"),
    b32("statement"),
    b32("registry"),
    b32("policy-v1"),
    b32("toolchain-v1"),
    block + 20,
    block + 40,
    block + 50,
    2,
    validators,
    { value },
  );
  await tx.wait();
  return 1n;
}

async function commitmentFor(escrow, bountyId, claimant, payout) {
  const artifactHash = b32("artifact");
  const salt = b32("salt");
  const hotkey = b32("hotkey");
  const commitment = await escrow.commitmentOf(bountyId, claimant.address, artifactHash, salt, payout.address, hotkey);
  return { commitment, artifactHash, salt, hotkey };
}

describe("LemmaBountyEscrow", function () {
  it("funds, commits, reveals, attests, and pays the first valid commitment", async function () {
    const { escrow, claimant, payout, validatorA, validatorB, validatorC } = await deployFixture();
    const bountyId = await createBounty(escrow, [validatorA.address, validatorB.address, validatorC.address]);
    const { commitment, artifactHash, salt, hotkey } = await commitmentFor(escrow, bountyId, claimant, payout);

    await escrow.connect(claimant).commitProof(bountyId, commitment);
    await escrow.connect(claimant).revealProof(bountyId, commitment, artifactHash, salt, payout.address, hotkey);
    await escrow.connect(validatorA).attestProof(bountyId, commitment);
    await escrow.connect(validatorB).attestProof(bountyId, commitment);
    await mineBlocks(55);

    await expect(() => escrow.resolveBounty(bountyId)).to.changeEtherBalance(payout, ethers.parseEther("1"));
    const bounty = await escrow.getBounty(bountyId);
    expect(bounty.winner).to.equal(claimant.address);
    expect(bounty.paid).to.equal(true);
  });

  it("rejects invalid reveals and duplicate attestations", async function () {
    const { escrow, claimant, payout, validatorA, validatorB } = await deployFixture();
    const bountyId = await createBounty(escrow, [validatorA.address, validatorB.address]);
    const { commitment, artifactHash, salt, hotkey } = await commitmentFor(escrow, bountyId, claimant, payout);

    await escrow.connect(claimant).commitProof(bountyId, commitment);
    await expect(
      escrow.connect(claimant).revealProof(bountyId, commitment, b32("wrong"), salt, payout.address, hotkey),
    ).to.be.revertedWithCustomError(escrow, "BadReveal");

    await escrow.connect(claimant).revealProof(bountyId, commitment, artifactHash, salt, payout.address, hotkey);
    await escrow.connect(validatorA).attestProof(bountyId, commitment);
    await expect(escrow.connect(validatorA).attestProof(bountyId, commitment)).to.be.revertedWithCustomError(
      escrow,
      "AlreadyAttested",
    );
  });

  it("requires unique validators and nonzero reveal payout fields", async function () {
    const { escrow, claimant, payout, validatorA, validatorB } = await deployFixture();
    await expect(createBounty(escrow, [validatorA.address, validatorA.address])).to.be.revertedWithCustomError(
      escrow,
      "InvalidValidatorSet",
    );

    const bountyId = await createBounty(escrow, [validatorA.address, validatorB.address], ethers.parseEther("1"));
    const { commitment, artifactHash, salt, hotkey } = await commitmentFor(escrow, bountyId, claimant, payout);
    await escrow.connect(claimant).commitProof(bountyId, commitment);
    await expect(
      escrow.connect(claimant).revealProof(bountyId, commitment, artifactHash, salt, ethers.ZeroAddress, hotkey),
    ).to.be.revertedWithCustomError(escrow, "InvalidBounty");
  });

  it("does not let the owner drain or manually redirect rewards", async function () {
    const { escrow } = await deployFixture();
    const exposed = escrow.interface.fragments.map((fragment) => fragment.name).filter(Boolean);
    expect(exposed).not.to.include("withdraw");
    expect(exposed).not.to.include("sweep");
    expect(exposed).not.to.include("manualPayout");
  });

  it("pause only blocks new commitments and does not move funds", async function () {
    const { escrow, claimant, validatorA, validatorB } = await deployFixture();
    const bountyId = await createBounty(escrow, [validatorA.address, validatorB.address]);
    const { commitment } = await commitmentFor(escrow, bountyId, claimant, claimant);

    await escrow.setPaused(true);
    await expect(escrow.connect(claimant).commitProof(bountyId, commitment)).to.be.revertedWithCustomError(
      escrow,
      "PausedContract",
    );
    const bounty = await escrow.getBounty(bountyId);
    expect(bounty.amount).to.equal(ethers.parseEther("1"));
  });

  it("can roll over unsolved bounties without releasing funds", async function () {
    const { escrow, validatorA, validatorB } = await deployFixture();
    const bountyId = await createBounty(escrow, [validatorA.address, validatorB.address]);

    await mineBlocks(55);
    await escrow.rollOverUnsolved(bountyId);
    const bounty = await escrow.getBounty(bountyId);
    expect(bounty.status).to.equal(2);
    expect(bounty.amount).to.equal(ethers.parseEther("1"));
  });
});

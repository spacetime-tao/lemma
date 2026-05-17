// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

/// @title LemmaBountyEscrow
/// @notice Bittensor EVM custody for Lean-verified proof rewards.
contract LemmaBountyEscrow {
    enum BountyStatus {
        None,
        Active,
        RolledOver,
        Solved
    }

    struct Bounty {
        bytes32 theoremId;
        bytes32 theoremHash;
        bytes32 registryHash;
        bytes32 policyVersion;
        bytes32 toolchainId;
        uint256 amount;
        uint64 commitDeadlineBlock;
        uint64 revealDeadlineBlock;
        uint64 challengeDeadlineBlock;
        uint16 attestationThreshold;
        address winner;
        BountyStatus status;
        bool paid;
    }

    struct Claim {
        bytes32 commitmentHash;
        address claimant;
        address payoutAddress;
        bytes32 artifactHash;
        bytes32 salt;
        bytes32 submitterHotkeyPubkey;
        uint64 commitBlock;
        uint64 revealBlock;
        uint16 attestations;
        bool revealed;
    }

    address public immutable owner;
    bool public paused;
    uint256 public bountyCount;

    mapping(uint256 => Bounty) public bounties;
    mapping(uint256 => Claim[]) private _claims;
    mapping(uint256 => mapping(bytes32 => uint256)) private _claimIndexPlusOne;
    mapping(uint256 => mapping(address => bool)) public bountyValidators;
    mapping(uint256 => mapping(bytes32 => mapping(address => bool))) public validatorAttested;

    event Paused(bool paused);
    event BountyCreated(uint256 indexed bountyId, bytes32 indexed theoremId, uint256 amount);
    event BountyRolledOver(uint256 indexed bountyId);
    event ProofCommitted(uint256 indexed bountyId, bytes32 indexed commitmentHash, address indexed claimant);
    event ProofRevealed(
        uint256 indexed bountyId,
        bytes32 indexed commitmentHash,
        address indexed claimant,
        bytes32 artifactHash,
        address payoutAddress
    );
    event ProofAttested(uint256 indexed bountyId, bytes32 indexed commitmentHash, address indexed validator);
    event BountyResolved(uint256 indexed bountyId, bytes32 indexed commitmentHash, address indexed winner, uint256 amount);

    error OnlyOwner();
    error PausedContract();
    error InvalidBounty();
    error InvalidWindow();
    error InvalidValidatorSet();
    error NotClaimable();
    error CommitmentExists();
    error CommitmentMissing();
    error NotClaimant();
    error RevealClosed();
    error BadReveal();
    error NotValidator();
    error AlreadyAttested();
    error ChallengeWindowOpen();
    error NoValidWinner();
    error PayoutFailed();

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    function setPaused(bool value) external onlyOwner {
        paused = value;
        emit Paused(value);
    }

    function createBounty(
        bytes32 theoremId,
        bytes32 theoremHash,
        bytes32 registryHash,
        bytes32 policyVersion,
        bytes32 toolchainId,
        uint64 commitDeadlineBlock,
        uint64 revealDeadlineBlock,
        uint64 challengeDeadlineBlock,
        uint16 attestationThreshold,
        address[] calldata validators
    ) external payable returns (uint256 bountyId) {
        if (paused) revert PausedContract();
        if (
            msg.value == 0 || theoremId == bytes32(0) || theoremHash == bytes32(0) || registryHash == bytes32(0)
                || policyVersion == bytes32(0) || toolchainId == bytes32(0)
        ) {
            revert InvalidBounty();
        }
        if (attestationThreshold == 0 || validators.length < attestationThreshold) revert InvalidValidatorSet();
        if (
            (commitDeadlineBlock != 0 && revealDeadlineBlock != 0 && commitDeadlineBlock > revealDeadlineBlock)
                || (revealDeadlineBlock != 0 && challengeDeadlineBlock != 0 && revealDeadlineBlock > challengeDeadlineBlock)
        ) {
            revert InvalidWindow();
        }

        bountyId = ++bountyCount;
        bounties[bountyId] = Bounty({
            theoremId: theoremId,
            theoremHash: theoremHash,
            registryHash: registryHash,
            policyVersion: policyVersion,
            toolchainId: toolchainId,
            amount: msg.value,
            commitDeadlineBlock: commitDeadlineBlock,
            revealDeadlineBlock: revealDeadlineBlock,
            challengeDeadlineBlock: challengeDeadlineBlock,
            attestationThreshold: attestationThreshold,
            winner: address(0),
            status: BountyStatus.Active,
            paid: false
        });

        for (uint256 i = 0; i < validators.length; i++) {
            if (validators[i] == address(0)) revert InvalidValidatorSet();
            for (uint256 j = 0; j < i; j++) {
                if (validators[i] == validators[j]) revert InvalidValidatorSet();
            }
            bountyValidators[bountyId][validators[i]] = true;
        }

        emit BountyCreated(bountyId, theoremId, msg.value);
    }

    function claimCount(uint256 bountyId) external view returns (uint256) {
        return _claims[bountyId].length;
    }

    function getBounty(uint256 bountyId) external view returns (Bounty memory) {
        return bounties[bountyId];
    }

    function getClaim(uint256 bountyId, uint256 index) external view returns (Claim memory) {
        return _claims[bountyId][index];
    }

    function commitmentOf(
        uint256 bountyId,
        address claimant,
        bytes32 artifactHash,
        bytes32 salt,
        address payoutAddress,
        bytes32 submitterHotkeyPubkey
    ) public view returns (bytes32) {
        Bounty memory bounty = bounties[bountyId];
        return keccak256(
            abi.encodePacked(
                bounty.theoremId,
                claimant,
                artifactHash,
                salt,
                bounty.toolchainId,
                bounty.policyVersion,
                bounty.registryHash,
                payoutAddress,
                submitterHotkeyPubkey
            )
        );
    }

    function commitProof(uint256 bountyId, bytes32 commitmentHash) external {
        Bounty memory bounty = bounties[bountyId];
        if (paused) revert PausedContract();
        if (bounty.status != BountyStatus.Active && bounty.status != BountyStatus.RolledOver) revert NotClaimable();
        if (bounty.commitDeadlineBlock != 0 && block.number > bounty.commitDeadlineBlock) revert NotClaimable();
        if (commitmentHash == bytes32(0)) revert InvalidBounty();
        if (_claimIndexPlusOne[bountyId][commitmentHash] != 0) revert CommitmentExists();

        _claims[bountyId].push(
            Claim({
                commitmentHash: commitmentHash,
                claimant: msg.sender,
                payoutAddress: address(0),
                artifactHash: bytes32(0),
                salt: bytes32(0),
                submitterHotkeyPubkey: bytes32(0),
                commitBlock: uint64(block.number),
                revealBlock: 0,
                attestations: 0,
                revealed: false
            })
        );
        _claimIndexPlusOne[bountyId][commitmentHash] = _claims[bountyId].length;
        emit ProofCommitted(bountyId, commitmentHash, msg.sender);
    }

    function revealProof(
        uint256 bountyId,
        bytes32 commitmentHash,
        bytes32 artifactHash,
        bytes32 salt,
        address payoutAddress,
        bytes32 submitterHotkeyPubkey
    ) external {
        Bounty memory bounty = bounties[bountyId];
        uint256 indexPlusOne = _claimIndexPlusOne[bountyId][commitmentHash];
        if (indexPlusOne == 0) revert CommitmentMissing();
        if (bounty.revealDeadlineBlock != 0 && block.number > bounty.revealDeadlineBlock) revert RevealClosed();

        Claim storage claim = _claims[bountyId][indexPlusOne - 1];
        if (claim.claimant != msg.sender) revert NotClaimant();
        if (artifactHash == bytes32(0) || payoutAddress == address(0) || submitterHotkeyPubkey == bytes32(0)) {
            revert InvalidBounty();
        }
        if (
            commitmentHash
                != commitmentOf(bountyId, msg.sender, artifactHash, salt, payoutAddress, submitterHotkeyPubkey)
        ) {
            revert BadReveal();
        }
        claim.artifactHash = artifactHash;
        claim.salt = salt;
        claim.payoutAddress = payoutAddress;
        claim.submitterHotkeyPubkey = submitterHotkeyPubkey;
        claim.revealBlock = uint64(block.number);
        claim.revealed = true;
        emit ProofRevealed(bountyId, commitmentHash, msg.sender, artifactHash, payoutAddress);
    }

    function attestProof(uint256 bountyId, bytes32 commitmentHash) external {
        if (!bountyValidators[bountyId][msg.sender]) revert NotValidator();
        if (validatorAttested[bountyId][commitmentHash][msg.sender]) revert AlreadyAttested();
        uint256 indexPlusOne = _claimIndexPlusOne[bountyId][commitmentHash];
        if (indexPlusOne == 0) revert CommitmentMissing();

        Claim storage claim = _claims[bountyId][indexPlusOne - 1];
        if (!claim.revealed) revert BadReveal();
        validatorAttested[bountyId][commitmentHash][msg.sender] = true;
        claim.attestations += 1;
        emit ProofAttested(bountyId, commitmentHash, msg.sender);
    }

    function rollOverUnsolved(uint256 bountyId) external {
        Bounty storage bounty = bounties[bountyId];
        if (bounty.status != BountyStatus.Active) revert InvalidBounty();
        if (bounty.challengeDeadlineBlock != 0 && block.number <= bounty.challengeDeadlineBlock) {
            revert ChallengeWindowOpen();
        }
        bounty.status = BountyStatus.RolledOver;
        emit BountyRolledOver(bountyId);
    }

    function resolveBounty(uint256 bountyId) external {
        Bounty storage bounty = bounties[bountyId];
        if (bounty.status != BountyStatus.Active && bounty.status != BountyStatus.RolledOver) revert InvalidBounty();
        if (bounty.challengeDeadlineBlock != 0 && block.number <= bounty.challengeDeadlineBlock) {
            revert ChallengeWindowOpen();
        }

        Claim[] storage claims = _claims[bountyId];
        for (uint256 i = 0; i < claims.length; i++) {
            Claim storage claim = claims[i];
            if (claim.revealed && claim.attestations >= bounty.attestationThreshold) {
                bounty.status = BountyStatus.Solved;
                bounty.winner = claim.claimant;
                bounty.paid = true;
                uint256 amount = bounty.amount;
                bounty.amount = 0;
                (bool ok,) = claim.payoutAddress.call{value: amount}("");
                if (!ok) revert PayoutFailed();
                emit BountyResolved(bountyId, claim.commitmentHash, claim.claimant, amount);
                return;
            }
        }

        revert NoValidWinner();
    }
}

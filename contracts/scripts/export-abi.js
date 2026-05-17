const fs = require("fs");
const path = require("path");

const artifactPath = path.join(__dirname, "..", "artifacts", "contracts", "LemmaBountyEscrow.sol", "LemmaBountyEscrow.json");
const outPath = path.join(__dirname, "..", "abi", "LemmaBountyEscrow.abi.json");
const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(artifact.abi, null, 2) + "\n");
console.log(`wrote ${outPath}`);

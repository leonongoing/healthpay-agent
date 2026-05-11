/**
 * 0G Storage Bridge Script
 *
 * Node.js bridge between Python (HealthPay Agent) and 0G TypeScript SDK.
 * Called via subprocess from src/zero_g_storage.py.
 *
 * Usage:
 *   node 0g-bridge.js upload <filepath>
 *   node 0g-bridge.js download <root_hash> <output_path>
 *
 * Environment variables:
 *   ZG_PRIVATE_KEY   - Ethereum private key for signing transactions
 *   ZG_EVM_RPC       - 0G EVM RPC endpoint
 *   ZG_INDEXER_RPC   - 0G Indexer RPC endpoint
 *
 * Output: JSON to stdout (parsed by Python caller)
 * Errors: stderr + non-zero exit code
 */

const { Indexer, ZgFile } = require("@0gfoundation/0g-ts-sdk");
const { ethers } = require("ethers");
const path = require("path");
const fs = require("fs");

// --- Configuration from environment ---
const PRIVATE_KEY = process.env.ZG_PRIVATE_KEY;
const EVM_RPC = process.env.ZG_EVM_RPC || "https://evmrpc-testnet.0g.ai";
const INDEXER_RPC =
  process.env.ZG_INDEXER_RPC ||
  "https://indexer-storage-testnet-turbo.0g.ai";

/**
 * Output a JSON result to stdout and exit.
 */
function outputResult(data) {
  process.stdout.write(JSON.stringify(data) + "\n");
}

/**
 * Output an error to stderr and exit with code 1.
 */
function exitError(message) {
  process.stderr.write(`Error: ${message}\n`);
  process.exit(1);
}

/**
 * Upload a local file to 0G Storage.
 * @param {string} filePath - Path to the file to upload
 */
async function upload(filePath) {
  if (!PRIVATE_KEY) {
    exitError("ZG_PRIVATE_KEY environment variable is not set.");
  }

  const resolvedPath = path.resolve(filePath);
  if (!fs.existsSync(resolvedPath)) {
    exitError(`File not found: ${resolvedPath}`);
  }

  try {
    // Initialize provider and signer
    const provider = new ethers.JsonRpcProvider(EVM_RPC);
    const signer = new ethers.Wallet(PRIVATE_KEY, provider);

    // Initialize the Indexer client
    const indexer = new Indexer(INDEXER_RPC);

    // Create ZgFile from the file path
    const zgFile = await ZgFile.fromFilePath(resolvedPath);

    // Generate Merkle tree to get the root hash
    const [tree, treeErr] = await zgFile.merkleTree();
    if (treeErr) {
      exitError(`Merkle tree generation failed: ${treeErr}`);
    }

    const rootHash = tree.rootHash();

    // Upload the file
    const [tx, uploadErr] = await indexer.upload(zgFile, EVM_RPC, signer);

    if (uploadErr) {
      exitError(`Upload failed: ${uploadErr}`);
    }

    // Close the file handle
    await zgFile.close();

    // Output result
    outputResult({
      success: true,
      rootHash: rootHash,
      txHash: tx ? tx.txHash : null,
      filePath: resolvedPath,
      fileSize: fs.statSync(resolvedPath).size,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    exitError(`Upload exception: ${err.message}`);
  }
}

/**
 * Download a file from 0G Storage by root hash.
 * @param {string} rootHash - Merkle root hash of the file
 * @param {string} outputPath - Local path to save the downloaded file
 */
async function download(rootHash, outputPath) {
  if (!rootHash) {
    exitError("Root hash is required for download.");
  }
  if (!outputPath) {
    exitError("Output path is required for download.");
  }

  try {
    const resolvedOutput = path.resolve(outputPath);

    // Ensure output directory exists
    const outputDir = path.dirname(resolvedOutput);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Initialize the Indexer client
    const indexer = new Indexer(INDEXER_RPC);

    // Download the file with proof verification
    const err = await indexer.download(rootHash, resolvedOutput, true);

    if (err !== null) {
      exitError(`Download failed: ${err}`);
    }

    // Verify file was created
    if (!fs.existsSync(resolvedOutput)) {
      exitError("Download completed but output file was not created.");
    }

    outputResult({
      success: true,
      rootHash: rootHash,
      outputPath: resolvedOutput,
      fileSize: fs.statSync(resolvedOutput).size,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    exitError(`Download exception: ${err.message}`);
  }
}

// --- Main CLI entry point ---
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command) {
    exitError(
      "Usage:\n" +
        "  node 0g-bridge.js upload <filepath>\n" +
        "  node 0g-bridge.js download <root_hash> <output_path>"
    );
  }

  switch (command) {
    case "upload":
      if (!args[1]) exitError("upload requires a file path argument.");
      await upload(args[1]);
      break;

    case "download":
      if (!args[1] || !args[2])
        exitError("download requires <root_hash> and <output_path> arguments.");
      await download(args[1], args[2]);
      break;

    default:
      exitError(`Unknown command: ${command}. Use 'upload' or 'download'.`);
  }
}

main().catch((err) => {
  exitError(`Unhandled error: ${err.message}`);
});

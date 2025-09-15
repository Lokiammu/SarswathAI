# BLOKRAG 2.0 – GPU-Accelerated RAG with Blockchain Verification

An end-to-end Streamlit application for Retrieval-Augmented Generation (RAG) over your own documents, with optional blockchain-backed verification for document integrity and query auditing. It uses LangChain, FAISS, HuggingFace embeddings, and local LLMs via Ollama. MongoDB stores users, sessions, notebooks, files (GridFS), vector indexes, and analytics.

## Features
- Document chat with RAG
- Multiple answer modes: direct retrieval, enhanced RAG, hybrid (documents + simulated web)
- GPU acceleration when available (PyTorch + CUDA)
- Notebook-based organization of documents and chats
- MongoDB persistence with GridFS for files and analytics dashboards
- Optional blockchain verification:
  - Verify uploaded documents (store SHA-256 hash on-chain)
  - Log queries immutably
  - Built-in simulation mode when chain is unavailable

## Project Structure
- `app.py`: Streamlit entrypoint, navigation, sidebar, and blockchain settings
- `auth.py`: Login/signup, session management
- `chat.py`: Chat UI, RAG initialization, file uploads, pipeline controls
- `rag.py`: `EnhancedRAG` engine (embeddings, FAISS, pipelines, blockchain hooks)
- `database.py`: `MongoDB` wrapper (users, sessions, notebooks, GridFS, FAISS persistence, analytics)
- `notebooks.py`: Notebook CRUD, per-notebook chat, analytics, blockchain panels
- `document_viewer.py`: In-app viewers for PDF/DOCX/TXT
- `utils.py`: Session initialization, styling, helpers
- `blockchain_utils.py`: Web3 `BlockchainManager` with simulation fallback
- `RAGDocumentVerifier.sol`: Minimal Solidity contract for document hash storage

## Prerequisites
- Python 3.10+ recommended
- Ollama installed and at least one local model pulled (e.g., `llama3.2:latest`)
- MongoDB (local or managed) and connection string
- Optional blockchain setup for real verification:
  - Local Ganache/Anvil or testnet/mainnet RPC
  - Deployed `RAGDocumentVerifier` contract address
  - Private key with funds for gas (omit `0x` in UI per app prompt)

## Installation
1. Create and activate a virtual environment.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   If you don’t have a requirements file, install core libs:
   ```bash
   pip install streamlit pymongo gridfs bcrypt langchain langchain-community \
       langchain-ollama langchain-huggingface sentence-transformers faiss-cpu \
       torch torchvision torchaudio pypdf2 python-docx psutil web3 beautifulsoup4
   ```
3. Ensure Ollama is running and models are available, e.g.:
   ```bash
   ollama pull llama3.2:latest
   ollama pull sentence-transformers/all-MiniLM-L6-v2
   ```

## Environment
Set environment variables (or rely on sensible defaults):
- `MONGODB_URI` (default: `mongodb://localhost:27017/`)

You can also configure blockchain in-app via the sidebar/settings. For headless setup, the app reads these from `st.session_state` during runtime:
- `blockchain_url` (e.g., `http://localhost:7545`)
- `blockchain_contract` (deployed contract address)
- `blockchain_private_key` (without `0x` prefix)
- `blockchain_chain_id` (default `1337`)

## Run
From this folder:
```bash
streamlit run app.py
```

## Usage
1. Sign up or log in.
2. In Chat or Notebooks, initialize the system (select LLM/embedding, GPU toggles).
3. Upload documents (PDF/DOCX/TXT). The app chunks, embeds, and builds a FAISS index.
4. Choose an answer mode:
   - Direct Retrieval: fastest; uses your docs only
   - Enhanced RAG: refinement pipeline over retrieved content
   - Hybrid: combines docs with simulated web sources
5. Optional blockchain verification:
   - Toggle “Enable Blockchain Verification” in sidebar/settings
   - Provide RPC URL, contract address, private key, and chain id
   - The app can verify documents and log queries. If on-chain fails, it auto-falls-back to simulation mode and clearly labels results.

## Blockchain Contract
`RAGDocumentVerifier.sol` exposes two functions:
```solidity
function verifyDocument(string documentId, string documentHash) external;
function getDocumentHash(string documentId) external view returns (string);
```

### Deploy (example with Hardhat)
- Initialize a Hardhat project and compile the contract.
- Deploy to a local chain (e.g., Anvil/Ganache) and note the contract address.
- Paste the address in the app’s blockchain settings.

If contract access fails, the app attempts to operate in simulation mode so you can continue testing without a live chain.

## Data Persistence
- Files: GridFS
- Users/Sessions/Notebooks/Logs: MongoDB collections
- Vector Indexes: FAISS persisted in `faiss_indexes` collection (binary blobs + metadata)

## Troubleshooting
- No GPU detected: app falls back to CPU; performance will be lower.
- “Please upload and process documents first.”: build vectors via file upload or load saved notebook vectors.
- Blockchain errors: check RPC connectivity, chain ID, funded account, and contract address. The app will switch to simulation mode and annotate results.
- Ollama issues: ensure the daemon is running and models are pulled.

## License
MIT. See SPDX header in `RAGDocumentVerifier.sol`.

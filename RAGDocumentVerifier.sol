// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract RAGDocumentVerifier {
    // Mapping from document ID to document hash
    mapping(string => string) public documentHashes;
    
    // Store a document hash with its ID
    function verifyDocument(string memory documentId, string memory documentHash) public {
        documentHashes[documentId] = documentHash;
    }
    
    // Get the hash of a document by ID
    function getDocumentHash(string memory documentId) public view returns (string memory) {
        return documentHashes[documentId];
    }
} 
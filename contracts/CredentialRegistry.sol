// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title CredentialRegistry
 * @notice National academic credential verification registry for university consortium
 */
contract CredentialRegistry {
    enum Status {
        VALID,
        REVOKED
    }

    struct Credential {
        uint256 id;
        string studentName;
        address registrar;
        string documentCid;
        uint256 issueTimestamp;
        Status status;
        address owner;
    }

    address public admin;
    uint256 public credentialCount;
    mapping(uint256 => Credential) public credentials;
    mapping(address => bool) public isRegistrar;

    event CredentialIssued(
        uint256 indexed credentialId,
        string studentName,
        address indexed registrar,
        string documentCid,
        uint256 issueTimestamp
    );

    event CredentialRevoked(uint256 indexed credentialId, address indexed revokedBy);

    event CredentialTransferred(
        uint256 indexed credentialId,
        address indexed from,
        address indexed to
    );

    modifier onlyRegistrar() {
        require(isRegistrar[msg.sender], "Only registrar can perform this action");
        _;
    }

    constructor() {
        admin = msg.sender;
        isRegistrar[msg.sender] = true;
    }

    function addRegistrar(address registrar) external {
        require(msg.sender == admin, "Only admin");
        isRegistrar[registrar] = true;
    }

    function issueCredential(
        string calldata studentName,
        address registrar,
        string calldata documentCid
    ) external onlyRegistrar returns (uint256) {
        require(bytes(studentName).length > 0, "Student name required");
        require(bytes(documentCid).length > 0, "Document CID required");

        credentialCount++;
        uint256 id = credentialCount;

        credentials[id] = Credential({
            id: id,
            studentName: studentName,
            registrar: registrar,
            documentCid: documentCid,
            issueTimestamp: block.timestamp,
            status: Status.VALID,
            owner: registrar
        });

        emit CredentialIssued(id, studentName, registrar, documentCid, block.timestamp);
        return id;
    }

    function revokeCredential(uint256 credentialId) external onlyRegistrar {
        Credential storage cred = credentials[credentialId];
        require(cred.id != 0, "Credential not found");
        require(cred.status == Status.VALID, "Credential already revoked");

        cred.status = Status.REVOKED;
        emit CredentialRevoked(credentialId, msg.sender);
    }

    function transferCredentialOwnership(uint256 credentialId, address newOwner) external {
        Credential storage cred = credentials[credentialId];
        require(cred.id != 0, "Credential not found");
        require(cred.status == Status.VALID, "Cannot transfer revoked credential");
        require(msg.sender == cred.owner, "Only owner can transfer");

        address previousOwner = cred.owner;
        cred.owner = newOwner;
        emit CredentialTransferred(credentialId, previousOwner, newOwner);
    }

    function getCredential(uint256 credentialId)
        external
        view
        returns (
            uint256 id,
            string memory studentName,
            address registrar,
            string memory documentCid,
            uint256 issueTimestamp,
            Status status,
            address owner
        )
    {
        Credential storage cred = credentials[credentialId];
        require(cred.id != 0, "Credential not found");
        return (
            cred.id,
            cred.studentName,
            cred.registrar,
            cred.documentCid,
            cred.issueTimestamp,
            cred.status,
            cred.owner
        );
    }

    function verifyCredential(uint256 credentialId)
        external
        view
        returns (
            uint256 id,
            string memory studentName,
            address registrar,
            string memory documentCid,
            Status status
        )
    {
        Credential storage cred = credentials[credentialId];
        require(cred.id != 0, "Credential not found");
        require(cred.status == Status.VALID, "Credential is REVOKED and cannot be verified");
        return (cred.id, cred.studentName, cred.registrar, cred.documentCid, cred.status);
    }
}

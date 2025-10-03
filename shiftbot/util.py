def create_sha256_hash(data: bytes) -> str:
    """ Create a SHA-256 hash of the given data. """
    import hashlib
    sha256 = hashlib.sha256()
    sha256.update(data)
    return sha256.hexdigest()
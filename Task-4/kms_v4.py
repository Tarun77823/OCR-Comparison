import os

class KmsError(Exception):
    pass


class KmsV4:

    def __init__(self):
        self.keys = {}

    def ensure_key(self, obj):
        if obj not in self.keys:
            self.keys[obj] = os.urandom(32)

    def revoke_key(self, obj):
        self.keys[obj] = None

    def rotate_key(self, obj):
        self.keys[obj] = os.urandom(32)

    def encrypt(self, obj, data):
        self.ensure_key(obj)
        key = self.keys[obj]
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

    def decrypt(self, obj, data, region, home):

        if region != home:
            raise KmsError("kms_wrong_region")

        key = self.keys.get(obj)

        if key is None:
            raise KmsError("kms_key_revoked")

        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
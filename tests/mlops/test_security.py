"""
Tests for aquilia.mlops.security - signing, encryption, RBAC.
"""

import io
import tarfile

import pytest

from aquilia.mlops.security.signing import ArtifactSigner, EncryptionManager
from aquilia.mlops.security.encryption import BlobEncryptor
from aquilia.mlops.security.rbac import (
    Permission,
    Role,
    RBACManager,
    BUILTIN_ROLES,
)


class TestArtifactSigner:
    async def test_sign_and_verify(self, tmp_path):
        archive = tmp_path / "test.aquilia"
        with tarfile.open(str(archive), "w:gz") as tar:
            info = tarfile.TarInfo(name="test.txt")
            data = b"model data"
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        signer = ArtifactSigner(hmac_secret="test-key")
        sig_path = await signer.sign(str(archive))
        result = await signer.verify(str(archive), sig_path)
        assert result is True


class TestEncryptionManager:
    def test_encrypt_decrypt(self):
        mgr = EncryptionManager()
        plaintext = b"secret model weights"
        ct = mgr.encrypt(plaintext)
        assert ct != plaintext
        assert mgr.decrypt(ct) == plaintext

    def test_different_keys_fail(self):
        m1 = EncryptionManager()
        m2 = EncryptionManager()
        ct = m1.encrypt(b"data")
        with pytest.raises(Exception):
            m2.decrypt(ct)


class TestBlobEncryptor:
    def test_roundtrip(self):
        enc = BlobEncryptor()
        data = b"model blob content"
        ct = enc.encrypt(data)
        assert enc.decrypt(ct) == data

    def test_from_key(self):
        enc1 = BlobEncryptor()
        ct = enc1.encrypt(b"data")
        enc2 = BlobEncryptor.from_key(enc1.key)
        assert enc2.decrypt(ct) == b"data"


class TestRBAC:
    def test_builtin_roles_exist(self):
        assert "viewer" in BUILTIN_ROLES
        assert "developer" in BUILTIN_ROLES
        assert "deployer" in BUILTIN_ROLES
        assert "admin" in BUILTIN_ROLES

    def test_admin_has_all_permissions(self):
        admin = BUILTIN_ROLES["admin"]
        for perm in Permission:
            assert perm in admin.permissions

    def test_viewer_limited_permissions(self):
        viewer = BUILTIN_ROLES["viewer"]
        assert Permission.PACK_READ in viewer.permissions
        assert Permission.PACK_WRITE not in viewer.permissions
        assert Permission.PACK_DELETE not in viewer.permissions

    def test_rbac_manager_assign_and_check(self):
        mgr = RBACManager()
        mgr.assign_role("alice", "developer")
        assert mgr.check_permission("alice", Permission.PACK_READ)
        assert mgr.check_permission("alice", Permission.PACK_WRITE)

    def test_rbac_denies_unassigned(self):
        mgr = RBACManager()
        assert not mgr.check_permission("bob", Permission.PACK_READ)

    def test_revoke_role(self):
        mgr = RBACManager()
        mgr.assign_role("carol", "developer")
        assert mgr.check_permission("carol", Permission.PACK_READ)
        mgr.revoke_role("carol", "developer")
        assert not mgr.check_permission("carol", Permission.PACK_READ)

    def test_get_user_permissions(self):
        mgr = RBACManager()
        mgr.assign_role("dave", "deployer")
        perms = mgr.get_user_permissions("dave")
        assert Permission.PACK_PROMOTE in perms
        assert Permission.PACK_READ in perms

    def test_multiple_roles(self):
        mgr = RBACManager()
        mgr.assign_role("eve", "viewer")
        mgr.assign_role("eve", "deployer")
        perms = mgr.get_user_permissions("eve")
        assert Permission.PACK_READ in perms
        assert Permission.PACK_PROMOTE in perms

"""Unit tests for the release build and publishing helpers."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
import tarfile
import unittest

import package_release
import publish_release
import remote_build


class PackageReleaseTests(unittest.TestCase):
    def test_version_is_read_from_makefile(self) -> None:
        self.assertEqual(package_release.read_version(), "1.0.0")


class RemoteBuildTests(unittest.TestCase):
    def test_secret_labels_are_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".secrets"
            path.write_text("# builders\nMAC: ssh mac-alias\nLINUX: ssh -p 2222 linux-alias\n", encoding="utf-8")
            connections = remote_build.read_connections(path)
        self.assertEqual(set(connections), {"MAC", "LINUX"})

    def test_private_and_generated_paths_are_excluded(self) -> None:
        self.assertTrue(remote_build.is_excluded(".private/.privkey"))
        self.assertTrue(remote_build.is_excluded("build/compiler/exbasic"))
        self.assertTrue(remote_build.is_excluded("DIST/SHA256SUMS.txt"))
        self.assertFalse(remote_build.is_excluded("packaging/remote/run-linux.sh"))
        self.assertFalse(remote_build.is_excluded("third_party/mkatrgo/boot.go"))

    def test_ssh_identity_and_batch_options_are_forced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            key = Path(temporary) / "key"
            key.write_text("test", encoding="ascii")
            argv = remote_build.ssh_argv("ssh -i old-key -p 2222 builder", key)
        self.assertEqual(argv[0], "ssh")
        self.assertIn(str(key.resolve()), argv)
        self.assertIn("BatchMode=yes", argv)
        self.assertNotIn("old-key", argv)
        self.assertEqual(argv[-1], "builder")

    def test_artifact_bundle_rejects_parent_paths(self) -> None:
        member = tarfile.TarInfo("../outside")
        with self.assertRaises(remote_build.BuildError):
            remote_build.validate_bundle_member(member)

    def test_artifact_bundle_ignores_macos_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle.tar.gz"
            destination = root / "out"
            destination.mkdir()
            with tarfile.open(bundle, "w:gz") as archive:
                for name in ("artifact.zip", "._artifact.zip", "__MACOSX/._artifact.zip"):
                    payload = b"release" if name == "artifact.zip" else b"metadata"
                    member = tarfile.TarInfo(name)
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
            extracted = remote_build.extract_bundle(bundle, destination)
            self.assertEqual(extracted, [destination / "artifact.zip"])


class PublishReleaseTests(unittest.TestCase):
    def test_github_repository_is_inferred_from_https_and_ssh(self) -> None:
        self.assertEqual(publish_release.infer_repo("https://github.com/acme/widget.git"), "acme/widget")
        self.assertEqual(publish_release.infer_repo("git@github.com:acme/widget.git"), "acme/widget")

    def test_non_github_remote_is_not_inferred(self) -> None:
        self.assertIsNone(publish_release.infer_repo("ssh://git@example.test/acme/widget.git"))


if __name__ == "__main__":
    unittest.main()

"""Check the contents of npm archives staged from canonical release packages."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "codex-cli" / "scripts"))

from build_npm_package import (
    CODEX_PLATFORM_PACKAGES,
    PACKAGE_NATIVE_COMPONENTS,
    PACKAGE_VOICE_TARGETS,
)


class NpmPackageTest(unittest.TestCase):
    def test_npm_archives_preserve_cli_runtime_without_standalone_executor(
        self,
    ) -> None:
        # These are the source and destination layouts used by the current
        # fork package builder. Darwin intentionally has no prebuilt native
        # payload and is covered by its separate source-build path.
        component_layout = {
            "bwrap": ("codex-resources/bwrap", "codex-resources/bwrap"),
            "codex": ("codex/codex", "bin/codex"),
            "codex-code-mode-host": (
                "codex/codex-code-mode-host",
                "bin/codex-code-mode-host",
            ),
            "rg": ("path/rg", "codex-path/rg"),
        }
        executable = shutil.which("whoami") or sys.executable

        for package, platform in CODEX_PLATFORM_PACKAGES.items():
            components = PACKAGE_NATIVE_COMPONENTS[package]
            if not components:
                continue

            with self.subTest(package=package), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                target = platform["target_triple"]
                source = root / "vendor" / target
                original: dict[str, bytes] = {}
                expected_payload: dict[str, bytes] = {}

                for component in components:
                    source_name, destination_name = component_layout[component]
                    destination = source / source_name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(executable, destination)
                    data = destination.read_bytes()
                    original[source_name] = data
                    expected_payload[destination_name] = data

                command = [
                    sys.executable,
                    str(
                        REPO_ROOT / "codex-cli" / "scripts" / "build_npm_package.py"
                    ),
                    "--package",
                    package,
                    "--release-version",
                    "1.2.3",
                    "--vendor-src",
                    str(source.parent),
                    "--staging-dir",
                    str(root / "staged"),
                    "--pack-output",
                    str(root / "package.tgz"),
                ]

                # Desktop Linux packages must carry the matching voice runtime.
                # Use deterministic stand-ins here: this test checks archive
                # staging, not the native helper or GStreamer implementation.
                voice_target = PACKAGE_VOICE_TARGETS.get(package)
                if voice_target is not None:
                    voice_dir = root / "voice"
                    helper = voice_dir / "bin/codex-voice-host"
                    helper.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(executable, helper)
                    expected_payload[
                        "codex-resources/voice/bin/codex-voice-host"
                    ] = helper.read_bytes()

                    voice_files = {
                        "manifest.json": json.dumps({"voiceTarget": voice_target}).encode(),
                        "runtime.json": b"{}",
                        "sources.json": b"{}",
                        "NOTICE.md": b"test fixture",
                        "lib/libgstreamer-1.0.so.0": b"test runtime fixture",
                    }
                    for relative, content in voice_files.items():
                        destination = voice_dir / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(content)
                        expected_payload[
                            f"codex-resources/voice/{relative}"
                        ] = content
                    command.extend(["--voice-dir", str(voice_dir)])

                archive_path = root / "package.tgz"
                subprocess.run(command, check=True, capture_output=True)

                with tarfile.open(archive_path, "r:gz") as archive:
                    prefix = f"package/vendor/{target}/"
                    actual = {
                        member.name.removeprefix(prefix): archive.extractfile(
                            member
                        ).read()
                        for member in archive.getmembers()
                        if member.isfile() and member.name.startswith(prefix)
                    }

                manifest = json.loads(actual.pop("codex-package.json"))
                self.assertEqual(
                    manifest,
                    {
                        "layoutVersion": 1,
                        "version": "1.2.3",
                        "target": target,
                        "variant": "codex-vl",
                        "entrypoint": "bin/codex",
                        "resourcesDir": "codex-resources",
                        "pathDir": "codex-path",
                    },
                )
                self.assertEqual(actual, expected_payload)
                self.assertNotIn("bin/codex-exec-server", actual)

                # Packaging must copy, never mutate or consume, its source tree.
                self.assertEqual(
                    {
                        path.relative_to(source).as_posix(): path.read_bytes()
                        for path in source.rglob("*")
                        if path.is_file()
                    },
                    original,
                )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str]) -> bool:
    """Run a command, return True on success, False on failure."""
    print(f"\n[INFO] Running: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("[INFO] Command completed successfully.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[WARN] Command failed: {e}")
        return False


def is_ffmpeg_installed() -> bool:
    """
    Check if ffmpeg is available.

    - First, use shutil.which to see if an ffmpeg executable is visible.
    - Then, on Windows: run 'where ffmpeg' as validation.
      On Unix-like systems: run 'which ffmpeg' as validation.
    """
    exe = shutil.which("ffmpeg")
    if not exe:
        print("[INFO] ffmpeg executable not found in PATH.")
        return False

    print(f"[INFO] ffmpeg found at: {exe}")
    return True


def install_ffmpeg_windows() -> bool:
    """Try to install ffmpeg on Windows using common package managers."""
    print("[INFO] Detected OS: Windows")

    if is_ffmpeg_installed():
        return True

    # Try Chocolatey
    if shutil.which("choco"):
        print("[INFO] Trying to install ffmpeg with Chocolatey...")
        if run_cmd(["choco", "install", "-y", "ffmpeg"]):
            return True

    # Try Scoop
    if shutil.which("scoop"):
        print("[INFO] Trying to install ffmpeg with Scoop...")
        if run_cmd(["scoop", "install", "ffmpeg"]):
            return True

    # Try winget
    if shutil.which("winget"):
        print("[INFO] Trying to install ffmpeg with winget...")
        # Rely on winget to resolve the appropriate package
        if run_cmd(["winget", "install", "ffmpeg", "-h"]):
            return True

    print(
        "\n[ERROR] Could not automatically install ffmpeg on Windows.\n"
        "Please install it manually:\n"
        "  1) Download a release from: https://www.gyan.dev/ffmpeg/builds/\n"
        "  2) Extract it (e.g., to C:\\tools\\ffmpeg)\n"
        "  3) Add C:\\tools\\ffmpeg\\bin to your PATH\n"
    )
    return False


def install_ffmpeg_macos() -> bool:
    """Try to install ffmpeg on macOS using Homebrew."""
    print("[INFO] Detected OS: macOS")

    if is_ffmpeg_installed():
        return True

    if shutil.which("brew"):
        print("[INFO] Trying to install ffmpeg with Homebrew...")
        if run_cmd(["brew", "install", "ffmpeg"]):
            return is_ffmpeg_installed()

    print(
        "\n[ERROR] Could not automatically install ffmpeg on macOS.\n"
        "Please install Homebrew from https://brew.sh/ and run:\n"
        "  brew install ffmpeg\n"
    )
    return False


def detect_linux_package_manager() -> str | None:
    """Best-effort detection of Linux package manager."""
    # Explicit check by common PM names
    if shutil.which("apt-get"):
        return "apt"
    if shutil.which("apt"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("yum"):
        return "yum"
    if shutil.which("pacman"):
        return "pacman"
    if shutil.which("zypper"):
        return "zypper"
    return None


def install_ffmpeg_linux() -> bool:
    """Try to install ffmpeg on Linux using apt/dnf/pacman/etc."""
    print("[INFO] Detected OS: Linux")

    if is_ffmpeg_installed():
        return True

    pm = detect_linux_package_manager()
    if pm is None:
        print(
            "\n[ERROR] Could not detect a supported package manager.\n"
            "Please install ffmpeg using your distro's instructions.\n"
        )
        return False

    print(f"[INFO] Detected package manager: {pm}")

    # Use sudo for non-root users
    is_root = hasattr(os, "geteuid") and os.geteuid() == 0
    sudo = [] if is_root else ["sudo"]

    if pm == "apt":
        cmds = [
            sudo + ["apt-get", "update"],
            sudo + ["apt-get", "install", "-y", "ffmpeg"],
        ]
    elif pm == "dnf":
        cmds = [sudo + ["dnf", "install", "-y", "ffmpeg"]]
    elif pm == "yum":
        cmds = [sudo + ["yum", "install", "-y", "ffmpeg"]]
    elif pm == "pacman":
        cmds = [sudo + ["pacman", "-Sy", "--noconfirm", "ffmpeg"]]
    elif pm == "zypper":
        cmds = [sudo + ["zypper", "install", "-y", "ffmpeg"]]
    else:
        print(
            "\n[ERROR] Detected package manager is not handled explicitly.\n"
            "Please install ffmpeg manually.\n"
        )
        return False

    for cmd in cmds:
        if not run_cmd(cmd):
            print("[WARN] Command failed, stopping installation sequence.")
            break

    return is_ffmpeg_installed()


def main() -> int:
    print("=== ffmpeg installer & validator ===")

    if is_ffmpeg_installed():
        print("\n[OK] ffmpeg is already installed and working.")
        return 0

    system = platform.system().lower()
    success = False

    if system == "windows":
        success = install_ffmpeg_windows()
    elif system == "darwin":
        success = install_ffmpeg_macos()
    elif system == "linux":
        success = install_ffmpeg_linux()
    else:
        print(f"[ERROR] Unsupported OS: {system}. Install ffmpeg manually.")

    if success:
        print("\n[SUCCESS] ffmpeg is installed and validated.")
        return 0

    print("\n[FAIL] ffmpeg is not installed or not working correctly.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

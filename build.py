"""
File: build.py
Created Date: Monday, 16th November 2020 10:19:49 pm
Author: Tianyu Gu (macdavid313@gmail.com)
"""


import os
import subprocess
import sys
from pathlib import Path
from shutil import which
from string import Template


def find_wheel() -> Path:
    dist_folder = Path(__file__).parent.joinpath("dist")
    return list(dist_folder.glob("*whl"))[0].absolute()


def gen_bzl():
    wheel_path = str(find_wheel())
    with Path(__file__).parent.joinpath("pyoxidizer.bzl.template").open("r") as fp:
        bzl_tmpl = Template(fp.read())
    bzl = Path(__file__).parent.joinpath("pyoxidizer.bzl")
    with bzl.open("w") as fp:
        fp.write(bzl_tmpl.substitute(wheel_path=wheel_path))
    return bzl


def gen_rust_flags():
    if not which("curl-config"):
        sys.exit("curl-config is not available")
    with subprocess.Popen(
        ["curl-config", "--static-libs"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as out:
        stdout, _ = out.communicate()
        flags = " ".join(
            f"-C link-arg={flag}" for flag in stdout.decode("utf-8").split()
        )
        if sys.platform == "darwin":
            flags += " -C link-arg=-undefined -C link-arg=dynamic_lookup"
        return flags


def pyoxidize():
    if not which("pyoxidizer"):
        sys.exit("pyoxidizer is not available")
    with subprocess.Popen(
        ["pyoxidizer", "build", "--release", "install"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as out:
        stdout, stderr = out.communicate()
        if stderr:
            sys.exit(stderr)
        sys.stdout.write(stdout.decode("utf-8"))


if __name__ == "__main__":
    bzl = gen_bzl()
    os.environ["RUSTFLAGS"] = gen_rust_flags()
    pyoxidize()
    os.remove(bzl)

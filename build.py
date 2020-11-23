"""
File: build.py
Created Date: Monday, 16th November 2020 10:19:49 pm
Author: Tianyu Gu (gty@franz.com)
"""


import os
import stat
import subprocess
import sys
import tarfile
from pathlib import Path
from shutil import copyfile, which
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


def poetry_build():
    if not which("poetry"):
        sys.exit("poetry is not available")
    os.system("poetry install")
    dist_path = Path(__file__).parent.joinpath("dist")
    if dist_path.exists():
        dist_path.rmdir()
    os.system("poetry build")


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


def make_archive():
    target_folder = list(Path(__file__).parent.joinpath("build").glob("x86_64*"))[0]
    bin = target_folder.joinpath("release", "install", "ag_transe_cli")
    copyfile(bin, "dist/ag-transe-cli")
    os.chmod(
        "dist/ag-transe-cli",
        stat.S_IRUSR
        | stat.S_IWUSR
        | stat.S_IXUSR
        | stat.S_IRGRP
        | stat.S_IWGRP
        | stat.S_IROTH,
    )
    with tarfile.open(
        f"ag_transe_cli-{sys.platform}-x86_64-dist.tar.gz", "w:gz"
    ) as tar:
        for file in Path(__file__).parent.joinpath("dist").iterdir():
            tar.add(file)


if __name__ == "__main__":
    poetry_build()
    bzl = gen_bzl()
    os.environ["RUSTFLAGS"] = gen_rust_flags()
    pyoxidize()
    os.remove(bzl)
    make_archive()

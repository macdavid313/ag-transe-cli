"""
File: cli.py
Created Date: Monday, 16th November 2020 7:07:35 pm
Author: Tianyu Gu (macdavid313@gmail.com)
"""


import sys

import plac


def main():
    if sys.argv[1] == "import":
        from ag_transe_cli.import_data import import_data

        plac.call(import_data, sys.argv[2:])
    else:
        raise Exception(f"Unknow subcommand: {sys.argv[1]}")

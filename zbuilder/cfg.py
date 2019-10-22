import os

from pathlib import Path
from zbuilder.helpers import load_yaml, dump_yaml

CONFIG_PATH = "~/.config/zbuilder/zbuilder.yaml"
CONFIG_EMPTY = """# ZBuilder configuration
providers: {}
"""


def load(touch=False):
    fname = os.path.expanduser(CONFIG_PATH)
    if not os.path.exists(fname) and touch:
        Path(fname).parent.mkdir(parents=True, exist_ok=True)
        Path(fname).touch()
        Path(fname).open('w').write(CONFIG_EMPTY)
    return load_yaml(fname)


def view(cfg):
    dump_yaml(cfg)


def save(cfg):
    fname = os.path.expanduser(CONFIG_PATH)
    with open(fname, 'w') as fp:
        dump_yaml(cfg, fp)

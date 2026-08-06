"""Bundled calculator icons loaded as Tk PhotoImages."""

from __future__ import annotations

from importlib import resources
from typing import Mapping

import tkinter as tk

_RESOURCE_PACKAGE = "golden_glory_lab.desktop.icons"

SLOT_ICON_NAMES: Mapping[str, str] = {
    "Helmet": "helmet",
    "Body Armour": "body_armour",
    "Gloves": "gloves",
    "Boots": "boots",
    "Main Hand": "main_hand",
    "Off Hand": "off_hand",
    "Amulet": "amulet",
    "Ring 1": "ring",
    "Ring 2": "ring",
    "Belt": "belt",
    "Passive Tree / Ascendancy": "passive_tree",
    "Other / Misc": "other",
}

JEWEL_ICON_NAME = "jewel"


def load_icon(master: tk.Misc, name: str) -> tk.PhotoImage | None:
    """Return the bundled PNG as a PhotoImage, or None when unavailable."""

    try:
        resource = resources.files(_RESOURCE_PACKAGE).joinpath(f"{name}.png")
    except (FileNotFoundError, ModuleNotFoundError, TypeError, AttributeError):
        return None
    try:
        with resources.as_file(resource) as path:
            return tk.PhotoImage(master=master, file=str(path))
    except (FileNotFoundError, OSError, tk.TclError):
        return None


def load_slot_photo(master: tk.Misc, slot_label: str) -> tk.PhotoImage | None:
    name = SLOT_ICON_NAMES.get(slot_label)
    if name is None:
        return None
    return load_icon(master, name)


def load_jewel_photo(master: tk.Misc) -> tk.PhotoImage | None:
    return load_icon(master, JEWEL_ICON_NAME)

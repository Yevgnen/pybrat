# -*- coding: utf-8 -*-

from __future__ import annotations

import glob
import itertools
import os
from collections.abc import Iterable
from typing import Union


def iter_file_groups(
    dirname: Union[str, bytes, os.PathLike],
    exts: Union[str, Iterable[str]],
    missing: str = "error",
) -> Iterable[tuple[str, list[str]]]:
    def _format_ext(ext):
        return f'.{ext.lstrip(".")}'

    def _iter_files(dirname):
        for dirpath, _, filenames in os.walk(dirname):
            for filename in filenames:
                if os.path.splitext(filename)[1] in exts:
                    yield os.path.join(dirpath, filename)

    if isinstance(dirname, bytes):
        dirname = dirname.decode()  # type: ignore

    missings = {"error", "ignore"}
    if missing not in missings:
        raise ValueError(f"Param `missing` should be in {missings}")

    if isinstance(exts, str):
        return glob.iglob(
            os.path.join(dirname, f"**/*{_format_ext(exts)}"), recursive=True
        )

    exts = {*map(_format_ext, exts)}
    num_exts = len(exts)
    files = _iter_files(dirname)
    for key, group in itertools.groupby(
        sorted(files), key=lambda x: os.path.splitext(os.path.relpath(x, dirname))[0]
    ):
        sorted_group = sorted(group, key=lambda x: os.path.splitext(x)[1])
        if len(sorted_group) != num_exts and missing == "error":
            raise RuntimeError(f"Missing files: {key!s}.{exts}")

        yield key, sorted_group

# -*- coding: utf-8 -*-

import glob
import itertools
import os
from typing import Iterable, Tuple, Union


def iter_file_groups(
    dirname: str,
    exts: Union[str, Iterable[str]],
    with_key: bool = False,
    missing: str = "error",
) -> Union[
    Iterable[str], Iterable[Tuple[str, ...]], Tuple[str, Iterable[Tuple[str, ...]]]
]:
    def _format_ext(ext):
        return f'.{ext.lstrip(".")}'

    def _iter_files(dirname):
        for dirpath, _, filenames in os.walk(dirname):
            for filename in filenames:
                if os.path.splitext(filename)[1] in exts:
                    yield os.path.join(dirpath, filename)

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
        group = sorted(group, key=lambda x: os.path.splitext(x)[1])
        if len(group) != num_exts and missing == "error":
            raise RuntimeError(f"Missing files: {key}.{exts}")

        yield (key, group) if with_key else group

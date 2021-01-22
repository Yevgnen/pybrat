# -*- coding: utf-8 -*-

import dataclasses
import re
from typing import Iterable, List, Optional, Union

from pybrat.utils import iter_file_groups


@dataclasses.dataclass(frozen=True)
class Entity(object):
    token: str
    tag: str
    start: int
    end: int
    id: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Relationship(object):
    relationship: str
    head: Entity
    tail: Entity
    id: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Example(object):
    text: Union[str, Iterable[str]]
    entities: dataclasses.field(default_factory=set)
    relationships: dataclasses.field(default_factory=set)
    id: Optional[str] = None


class BratParser(object):
    def __init__(self, seps: str = "。", ignores: str = "\n 　", error: str = "raise"):
        self.seps = set(seps)
        self.ignores = set(ignores)
        self.error = error
        self.exts = {".ann", ".txt"}

    def _raise(self, error):
        if self.error == "raise":
            raise error

    def _raise_invalid_line_error(self, line):
        self._raise(RuntimeError(f"Invalid line: {line}"))

    def _parse_entity(self, line):
        regex = re.compile(
            r"""(?P<id>T\d+)
                \t(?P<tag>[^ ]+)
                \ (?P<start>\d+)
                \ (?P<end>\d+)
                \t(?P<token>.+)""",
            re.X,
        )
        match = re.match(regex, line)
        if not match:
            self._raise_invalid_line_error(line)

        return match.group

    def _parse_relationship(self, line):
        regex = re.compile(
            r"""(?P<id>R\d+)
                \t(?P<relationship>[^ ]+)
                \ Arg[12]:(?P<head>T\d+)
                \ Arg[12]:(?P<tail>T\d+)""",
            re.X,
        )
        match = re.match(regex, line)
        if not match:
            self._raise_invalid_line_error(line)

        return match.group

    def _parse_ann(self, ann):
        entities = {}
        relationship_matches = []
        with open(ann, mode="r") as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue

                if line.startswith("T"):
                    match = self._parse_entity(line)
                    entities[match("id")] = Entity(
                        token=match("token"),
                        tag=match("tag"),
                        start=int(match("start")),
                        end=int(match("end")),
                        id=match("id"),
                    )
                elif line.startswith("R"):
                    match = self._parse_relationship(line)
                    relationship_matches += [match]
                else:
                    self._raise_invalid_line_error(line)

        relationships = set()
        for rel in relationship_matches:
            head_id, tail_id = rel("head"), rel("tail")
            head = entities.get(head_id)
            tail = entities.get(tail_id)
            if not head or not tail:
                self._raise(
                    KeyError(f"Missing entity: {head_id if not head else tail_id}")
                )

            relationships.add(
                Relationship(
                    relationship=rel("relationship"), head=head, tail=tail, id=rel("id")
                )
            )
        entities = set(entities.values())

        return {"entities": entities, "relationships": relationships}

    def _parse_text(self, txt):  # pylint: disable=no-self-use
        with open(txt, mode="r") as f:
            return f.read()

    def parse(self, dirname: str) -> List[Example]:
        examples = []
        for key, (ann, txt) in iter_file_groups(
            dirname,
            self.exts,
            with_key=True,
            missing="error" if self.error == "raise" else "ignore",
        ):
            text = self._parse_text(txt)
            ann = self._parse_ann(ann)
            examples += [Example(text=text, **ann, id=key)]

        examples.sort(key=lambda x: x.id)

        return examples

# -*- coding: utf-8 -*-

import dataclasses
import itertools
import re
from typing import FrozenSet, Iterable, List, Optional, Union

from pybrat.utils import iter_file_groups


@dataclasses.dataclass(frozen=True)
class Entity(object):
    mention: str
    type: str
    start: int
    end: int
    id: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Relation(object):
    type: str
    arg1: Entity
    arg2: Entity
    id: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Event(object):
    @dataclasses.dataclass(frozen=True)
    class Argument(object):
        rule: str
        entity: Entity

    type: str
    trigger: Entity
    arguments: FrozenSet[Argument] = dataclasses.field(default_factory=frozenset)
    id: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Example(object):
    text: Union[str, Iterable[str]]
    entities: FrozenSet[Entity] = dataclasses.field(default_factory=frozenset)
    relations: FrozenSet[Relation] = dataclasses.field(default_factory=frozenset)
    events: FrozenSet[Event] = dataclasses.field(default_factory=frozenset)
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
                \t(?P<type>[^ ]+)
                \ (?P<start>\d+)
                \ (?P<end>\d+)
                \t(?P<mention>.+)""",
            re.X,
        )
        match = re.match(regex, line)
        if not match:
            self._raise_invalid_line_error(line)

        return match

    def _parse_relation(self, line):
        regex = re.compile(
            r"""(?P<id>R\d+)
                \t(?P<type>[^ ]+)
                \ Arg[12]:(?P<arg1>T\d+)
                \ Arg[12]:(?P<arg2>T\d+)""",
            re.X,
        )
        match = re.match(regex, line)
        if not match:
            self._raise_invalid_line_error(line)

        return match

    def _parse_equivalence_relations(self, line):
        regex = re.compile(r"\*\tEquiv((?: T\d+)+)")
        match = re.match(regex, line)
        if not match:
            self._raise_invalid_line_error(line)

        entities = match.group(1).strip().split()

        return (
            {"type": "Equiv", "arg1": arg1, "arg2": arg2, "id": f"Equiv:{arg1}-{arg2}"}
            for arg1, arg2 in itertools.combinations(entities, 2)
        )

    def _parse_event(self, line):
        regex = re.compile(
            r"""(?P<id>E\d+)
                \t(?P<type>[^:]+):(?P<trigger>T\d+)
                (?P<args>(?:\ [^:]+:T\d+)+)""",
            re.X,
        )
        match = re.match(regex, line)
        if not match:
            self._raise_invalid_line_error(line)

        args = [x.split(":") for x in match["args"].strip().split()]

        return {
            "id": match["id"],
            "type": match["type"],
            "trigger": match["trigger"],
            "args": [{"role": x[0], "entity": x[1]} for x in args],
        }

    def _parse_ann(self, ann):
        # Parser entities and store required data for parsing relations
        # and events.
        entities = {}
        relation_matches = []
        event_matches = []
        with open(ann, mode="r") as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue

                if line.startswith("T"):
                    match = self._parse_entity(line)
                    entities[match["id"]] = Entity(
                        mention=match["mention"],
                        type=match["type"],
                        start=int(match["start"]),
                        end=int(match["end"]),
                        id=match["id"],
                    )
                elif line.startswith("R"):
                    match = self._parse_relation(line)
                    relation_matches += [match]
                elif line.startswith("*"):
                    match = self._parse_equivalence_relations(line)
                    relation_matches += list(match)
                elif line.startswith("E"):
                    match = self._parse_event(line)
                    event_matches += [match]
                else:
                    self._raise_invalid_line_error(line)

        # Parse relations.
        relations = set()
        for rel in relation_matches:
            arg1_id, arg2_id = rel["arg1"], rel["arg2"]
            arg1 = entities.get(arg1_id)
            arg2 = entities.get(arg2_id)
            if not arg1 or not arg2:
                self._raise(
                    KeyError(
                        f"Missing relation arg: {arg1_id if not arg1 else arg2_id}"
                    )
                )

            relations.add(
                Relation(type=rel["type"], arg1=arg1, arg2=arg2, id=rel["id"])
            )

        # Parser events.
        events = set()
        arguments = set()
        for match in event_matches:
            trigger = entities.get(match["trigger"])
            if not trigger:
                self._raise(KeyError(f"Missing event trigger: {trigger}"))

            for arg in match["args"]:
                arg_entity = entities.get(arg["entity"])
                if not arg_entity:
                    self._raise(KeyError(f'Missing event arg: {arg["id"]}'))
                arguments.add(arg_entity)
            event = Event(
                type=match["type"],
                trigger=trigger,
                arguments=frozenset(arguments),
                id=match["id"],
            )
            events.add(event)

        return {
            "entities": frozenset(entities.values()),
            "relations": frozenset(relations),
            "events": frozenset(events),
        }

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

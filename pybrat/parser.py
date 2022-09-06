# -*- coding: utf-8 -*-

from __future__ import annotations

import collections
import dataclasses
import itertools
import os
import re
from collections.abc import Iterable
from typing import Optional, Union

from pybrat.utils import iter_file_groups


@dataclasses.dataclass
class Reference(object):
    rid: str
    eid: str
    entry: str
    id: Optional[str] = None


@dataclasses.dataclass
class Span(object):
    start: int
    end: int

    def __hash__(self):
        return hash((self.start, self.end))


@dataclasses.dataclass
class Entity(object):
    mention: str
    type: str
    spans: list[Span]
    references: list[Reference] = dataclasses.field(default_factory=list)
    id: Optional[str] = None

    @property
    def start(self):
        if len(self.spans) == 1:
            return self.spans[0].start

        raise RuntimeError("`start` property only work for continuous enitty")

    @property
    def end(self):
        if len(self.spans) == 1:
            return self.spans[0].end

        raise RuntimeError("`end` property only work for continuous enitty")


@dataclasses.dataclass
class Relation(object):
    type: str
    arg1: Entity
    arg2: Entity
    id: Optional[str] = None


@dataclasses.dataclass
class Event(object):
    @dataclasses.dataclass
    class Argument(object):
        rule: str
        entity: Entity

    type: str
    trigger: Entity
    arguments: list[Argument] = dataclasses.field(default_factory=list)
    id: Optional[str] = None


@dataclasses.dataclass
class Example(object):
    text: Union[str, Iterable[str]]
    entities: list[Entity] = dataclasses.field(default_factory=list)
    relations: list[Relation] = dataclasses.field(default_factory=list)
    events: list[Event] = dataclasses.field(default_factory=list)
    id: Optional[str] = None


class BratParser(object):
    """Parser for brat rapid annotation tool (Brat).

    Args:
        ignore_types (Optional[Iterable[str]]): Optional annotation
            types to ignore, should be in {"T", "R", "*", "E", "N", "AM"}.
            (default: None)
        error (str): Error handling, should be in {"raise", "ignore"}.
            (default: "raise")
    """

    def __init__(
        self, ignore_types: Optional[Iterable[str]] = None, error: str = "raise"
    ):
        self.types = {"T", "R", "*", "E", "N", "AM"}

        self.re_ignore_types: Optional[re.Pattern] = None
        if ignore_types:
            unknown_types = set(ignore_types) - self.types
            if unknown_types:
                raise ValueError(f"Unknown types: {unknown_types!r}")
            self.re_ignore_types = re.compile(
                r"|".join(re.escape(x) for x in ignore_types)
            )

        errors = {"raise", "ignore"}
        if error not in errors:
            raise ValueError(f"`error` should be in {errors!r}")
        self.error = error

        self.exts = {".ann", ".txt"}

    def _should_ignore_line(self, line):
        if self.re_ignore_types:
            return re.match(self.re_ignore_types, line)

        return False

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
                (?P<optional_spans>(?:;\d+\ \d+)*)
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
                (?P<args>(?:\ [^:]+:[TE]\d+)+)?""",  # argument could be entity or event
            re.X,
        )
        match = re.match(regex, line)
        if not match:
            self._raise_invalid_line_error(line)

        if not match["args"]:
            args = []
        else:
            args = [x.split(":") for x in match["args"].strip().split()]

        return {
            "id": match["id"],
            "type": match["type"],
            "trigger": match["trigger"],
            "args": [
                {
                    "role": x[0],
                    "id": x[1],
                    "type": "entity" if x[1].startswith("T") else "event",
                }
                for x in args
            ],
        }

    def _parse_reference(self, line):
        regex = re.compile(
            r"""(?P<id>N\d+)
                \tReference
                \ (?P<entity>T\d+)
                \ (?P<rid>[^:]+):(?P<eid>[^\t]+)
                \t(?P<entry>.+)""",
            re.X,
        )
        match = re.match(regex, line)
        if not match:
            self._raise_invalid_line_error(line)

        return match

    def _format_entities(
        self, entity_matches, references
    ):  # pylint: disable=no-self-use
        def _format_entity(match):
            spans = [Span(start=int(match["start"]), end=int(match["end"]))]
            if match["optional_spans"]:
                spans += [
                    Span(*map(int, splits.split(" ")))
                    for splits in filter(None, match["optional_spans"].split(";"))
                ]

            return Entity(
                mention=match["mention"],
                type=match["type"],
                spans=spans,
                references=references[match["id"]],
                id=match["id"],
            )

        return {match["id"]: _format_entity(match) for match in entity_matches}

    def _format_relations(self, relation_matches, entities):
        relations = []
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

            relations += [
                Relation(type=rel["type"], arg1=arg1, arg2=arg2, id=rel["id"])
            ]

        return relations

    def _format_events(self, event_matches, entities):
        adjacent = {
            e["id"]: [x["id"] for x in e["args"] if x["type"] == "event"]
            for e in event_matches
        }
        sorted_event_ids = collections.OrderedDict()
        while adjacent:
            adjacent = sorted(adjacent.items(), key=lambda x: len(x[1]))
            for node, neighbors in adjacent:
                if neighbors:
                    break

                sorted_event_ids[node] = None

            updated_adjacent = {}
            for node, neighbors in adjacent:
                if node not in sorted_event_ids:
                    updated_adjacent[node] = [
                        x for x in neighbors if x not in sorted_event_ids
                    ]
            adjacent = updated_adjacent
        event_index = dict(zip(sorted_event_ids, range(len(sorted_event_ids))))

        events = dict()
        for match in sorted(event_matches, key=lambda x: event_index[x["id"]]):
            arguments = []
            trigger = entities.get(match["trigger"])
            if not trigger:
                self._raise(KeyError(f"Missing event trigger: {trigger}"))

            for arg in match["args"]:
                if arg["type"] == "entity":
                    arg_object = entities.get(arg["id"])
                elif arg["type"] == "event":
                    arg_object = events.get(arg["id"])
                    if not arg_object:
                        self._raise(KeyError(f'Missing event arg: {arg["id"]}'))
                else:
                    self._raise(RuntimeError(f'Unknown event arg: {arg["id"]}'))

                arguments += [arg_object]

            event = Event(
                type=match["type"], trigger=trigger, arguments=arguments, id=match["id"]
            )
            events[event.id] = event

        return events

    def _check_entities(self, entities):  # pylint: disable=no-self-use
        pool = {}
        for entity in entities:
            id_ = pool.setdefault(tuple(entity.spans), entity.id)
            if id_ != entity.id:
                self._raise(
                    RuntimeError(
                        "Detected identical span for"
                        f" different entities: [{id_}, {entity.id}]"
                    )
                )

    def _parse_ann(self, ann, encoding):
        # Parser entities and store required data for parsing relations
        # and events.
        entity_matches, relation_matches, event_matches = [], [], []
        references = collections.defaultdict(list)

        with open(ann, mode="r") as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith("#") or self._should_ignore_line(line):
                    continue

                if line.startswith("T"):
                    if match := self._parse_entity(line):
                        entity_matches += [match]
                elif line.startswith("R"):
                    if match := self._parse_relation(line):
                        relation_matches += [match]
                elif line.startswith("*"):
                    if match := self._parse_equivalence_relations(line):
                        relation_matches += list(match)
                elif line.startswith("E"):
                    if match := self._parse_event(line):
                        event_matches += [match]
                elif line.startswith("N"):
                    if match := self._parse_reference(line):
                        references[match["entity"]] += [
                            Reference(
                                rid=match["rid"],
                                eid=match["eid"],
                                entry=match["entry"],
                                id=match["id"],
                            )
                        ]
                elif line.startswith("AM"):
                    raise NotImplementedError()

        # Format entities.
        entities = self._format_entities(entity_matches, references)
        self._check_entities(entities.values())

        # Format relations.
        relations = self._format_relations(relation_matches, entities)

        # Format events.
        events = self._format_events(event_matches, entities)

        return {
            "entities": list(entities.values()),
            "relations": relations,
            "events": list(events.values()),
        }

    def _parse_text(self, txt, encoding):  # pylint: disable=no-self-use
        with open(txt, mode="r", encoding=encoding) as f:
            return f.read()

    def parse(
        self, dirname: Union[str, bytes, os.PathLike], encoding: str = "utf-8"
    ) -> list[Example]:
        """Parse examples in given directory.

        Args:
            dirname (Union[str, bytes, os.PathLike]): Directory
                containing brat examples.
            encoding (str): Encoding for reading text files and
                ann files

        Returns:
            examples (list[Example]): Parsed examples.
        """

        examples = []

        file_groups = iter_file_groups(
            dirname,
            self.exts,
            missing="error" if self.error == "raise" else "ignore",
        )

        for key, (ann_file, txt_file) in file_groups:
            txt = self._parse_text(txt_file, encoding=encoding)
            ann = self._parse_ann(ann_file, encoding=encoding)
            examples += [Example(text=txt, **ann, id=key)]

        examples.sort(key=lambda x: x.id if x.id is not None else "")

        return examples

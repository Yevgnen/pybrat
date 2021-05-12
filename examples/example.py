# -*- coding: utf-8 -*-

import dataclasses

from pybrat.parser import BratParser, Entity, Event, Example, Relation

# Initialize a parser.
brat = BratParser(error="ignore")
examples = brat.parse("brat/example-data/corpora/BioNLP-ST_2011")

# The praser returns dataclasses.
assert len(examples) == 80
assert all(isinstance(x, Example) for x in examples)
assert all(isinstance(e, Entity) for x in examples for e in x.entities)
assert all(isinstance(e, Relation) for x in examples for e in x.relations)
assert all(isinstance(e, Event) for x in examples for e in x.events)

id_ = "BioNLP-ST_2011_EPI/PMID-19377285"
example = next(x for x in examples if x.id == id_)
print(example.text)
print(len(example.entities), next(iter(example.entities)))
print(len(example.relations), next(iter(example.relations)))
print(len(example.events), next(iter(example.events)))

# Use dataclasses.asdict to convert examples to dictionaries.
examples = [*map(dataclasses.asdict, examples)]
assert all(isinstance(x, dict) for x in examples)
assert all(isinstance(e, dict) for x in examples for e in x["entities"])
assert all(isinstance(e, dict) for x in examples for e in x["relations"])
assert all(isinstance(e, dict) for x in examples for e in x["events"])

print(examples[0])

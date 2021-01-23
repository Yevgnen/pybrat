# Introduction

`pybrat` is a reader/parser for reading/parsing data annotated by
[brat](https://brat.nlplab.org/index.html).

# Usages

## Fetch sample data

``` bash
git clone https://github.com/nlplab/brat.git
```

## Use `pybrat` to parse annotated data

``` python
# -*- coding: utf-8 -*-

from pybrat.parser import BratParser, Entity, Event, Example, Relation

brat = BratParser()
examples = brat.parse("brat/example-data/corpora/BioNLP-ST_2011")

assert len(examples) == 80
assert all(isinstance(x, Example) for x in examples)
assert all(isinstance(e, Entity) for x in examples for e in x.entities)
assert all(isinstance(e, Relation) for x in examples for e in x.relations)
assert all(isinstance(e, Event) for x in examples for e in x.events)

id_ = "BioNLP-ST_2011_EPI/PMID-19377285"
example = next(x for x in examples if x.id == "BioNLP-ST_2011_EPI/PMID-19377285")
print(example.text)
print(len(example.entities), next(iter(example.entities)))
print(len(example.relations), next(iter(example.relations)))
print(len(example.events), next(iter(example.events)))
```

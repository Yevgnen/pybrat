# Table of Contents <span class="tag" tag-name="TOC"><span class="smallcaps">TOC</span></span>

-   [Introduction](#introduction)
-   [Installation](#installation)
    -   [From pip](#from-pip)
    -   [From source](#from-source)
-   [Usages](#usages)
    -   [Fetch sample data](#fetch-sample-data)
    -   [Parse annotated data](#parse-annotated-data)
-   [Contribution](#contribution)
    -   [Formatting Code](#formatting-code)

# Introduction

`pybrat` is a reader/parser for reading/parsing data annotated by
[brat](https://brat.nlplab.org/index.html).

# Installation

## From pip

``` bash
pip install pybrat
```

## From source

``` bash
pip install git+https://github.com/Yevgnen/pybrat
```

# Usages

## Fetch sample data

``` bash
git clone https://github.com/nlplab/brat.git
```

## Parse annotated data

Below is an [example](/Users/Maximin/git/pybrat/examples/example.py) of
parsing
[BioNLP-ST\_2011](https://github.com/nlplab/brat/tree/master/example-data/corpora/BioNLP-ST_2011)
data:

``` python
# -*- coding: utf-8 -*-

import dataclasses

from pybrat.parser import BratParser, Entity, Event, Example, Relation

# Initialize a parser.
brat = BratParser()
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
```

# Contribution

## Formatting Code

To ensure the codebase complies with a style guide, please use
[flake8](https://github.com/PyCQA/flake8),
[black](https://github.com/psf/black) and
[isort](https://github.com/PyCQA/isort) tools to format and check
codebase for compliance with PEP8.

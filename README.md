# ag-transe-cli

A command line tool for importing data into or exporting data from AllegroGraph.

## Install

Users have 2 ways to install `ag-transe-cli`:

1. use the pre-compiled standalone executable directly: `ag-transe-cli`
2. install by its *wheel* file: `pip install ag_transe_cli-0.0.1-py3-none-any.whl`

The second way will install an executable script to your current environment. **Using a virtual environment is highly recommended.**

## Import

To import triples into AllegroGraph from the training data directory, use `import` subcommand.

```bash
> ag-transe-cli import -h
usage: ag-transe-cli [-h] [-training-data-dir TRAINING_DATA_DIR] [-repo REPO] [-ag-env AG_ENV] [-save-ntriples-to SAVE_NTRIPLES_TO]
                     [-compress] [-entity-uri-prefix ENTITY_URI_PREFIX] [-relation-uri-prefix RELATION_URI_PREFIX]
                     [-entity-type ENTITY_TYPE] [-relation-type RELATION_TYPE]

optional arguments:
  -h, --help            show this help message and exit
  -training-data-dir TRAINING_DATA_DIR
                        Path to training data where it must contain 'entity2id.txt', 'relation2id.txt', 'train2id.txt',
                        'valid2id.txt', 'test2id.txt'
  -repo REPO            Name of the repository to be populated; The repository will be re-newed if it already exists and will conflict
                        with 'save_ntriples_to' if both given
  -ag-env AG_ENV        A text file that has environment varibles for connecting to AllegroGraph, e.g. 'AGRAPH_HOST', 'AGRAPH_PORT'
  -save-ntriples-to SAVE_NTRIPLES_TO
                        Path to save a serialization of all triples in NTriples format; It will conflict with 'repo' if both given
  -compress             If given, the saved ntriples serialization will be compressed; Only meaningful when 'save_ntriples_to' is
                        valid
  -entity-uri-prefix ENTITY_URI_PREFIX
                        Namespace for entities; Only applied when entities from 'entity2id.txt' are not URIs
  -relation-uri-prefix RELATION_URI_PREFIX
                        Namespace for relations; Only applied when relations from 'relation2id.txt' are not URIs
  -entity-type ENTITY_TYPE
                        Type of entities, default to rdfs:Class if not given; Must be a valid uri
  -relation-type RELATION_TYPE
                        Type of relations, default to rdf:Property if not given; Must be a valid uri
```

To connect to AllegroGraph, users must provide a set of environment variables, if not given, `ag-transe-cli` will use these values by default:

```bash
AGRAPH_HOST=localhost
AGRAPH_PORT=10035
AGRAPH_CATALOG=""
AGRAPH_USER=""
AGRAPH_PASSWORD=""
```

For exmaple:

```bash
> AGRAPH_HOST="192.168.0.100" AGRAPH_USER="user" AGRAPH_PASSWORD="password" ./ag-transe-cli import ...
```

Users can also write these variables to a text file and provide it by `-ag-env` argument:

```bash
> cat ag.env
AGRAPH_HOST=192.168.0.100
AGRAPH_PORT=10035
AGRAPH_CATALOG=""
AGRAPH_USER=user
AGRAPH_PASSWORD=password

> ag-transe-cli import -ag-env ag.env ...
```

Please note that, **if the specified repository already exists, then `ag-transe-cli` will clear all current triples and initialize a fresh repository.** This implies the `AGRAPH_USER` must have the **WRITE** permission.

### Examples of importing

* import data to 'foobar' repository

```bash
> ./ag-transe-cli import -training-data-dir OpenKE/benchmarks/FB15K237/ -repo foobar -ag-env ag.env -entity-uri-prefix "http://example.org/" -relation-uri-prefix "http://example.org/Property#"
INFO - 18:17:21: Repo 'foobar' does not exist, creating ...
INFO - 18:17:22: 'foobar' has been successfully initialized
INFO - 18:17:22: Adding all triples to 'foobar'
INFO - 18:17:27: All triples successfully loaded to 'foobar'
```

* import data to disk

```bash
> ./ag-transe-cli import -training-data-dir OpenKE/benchmarks/FB15K237/ -save-ntriples-to /tmp/foo.nt -entity-uri-prefix "http://example.org/" -relation-uri-prefix "http://example.org/Property#"
INFO - 18:18:53: Writing all triples to '/tmp/foo.nt'
INFO - 18:18:54: All triples have been successfully written to '/tmp/foo.nt'

> head -n 10 /tmp/foo.nt
<http://example.org//m/027rn> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2000/01/rdf-schema#Class> .
<http://example.org//m/027rn> <http://example.org/embeddings#hasID> "0"^^<http://www.w3.org/2001/XMLSchema#integer> .
<http://example.org//m/06cx9> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2000/01/rdf-schema#Class> .
<http://example.org//m/06cx9> <http://example.org/embeddings#hasID> "1"^^<http://www.w3.org/2001/XMLSchema#integer> .
<http://example.org//m/017dcd> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2000/01/rdf-schema#Class> .
<http://example.org//m/017dcd> <http://example.org/embeddings#hasID> "2"^^<http://www.w3.org/2001/XMLSchema#integer> .
<http://example.org//m/06v8s0> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2000/01/rdf-schema#Class> .
<http://example.org//m/06v8s0> <http://example.org/embeddings#hasID> "3"^^<http://www.w3.org/2001/XMLSchema#integer> .
<http://example.org//m/07s9rl0> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2000/01/rdf-schema#Class> .
<http://example.org//m/07s9rl0> <http://example.org/embeddings#hasID> "4"^^<http://www.w3.org/2001/XMLSchema#integer> .
```

Users can upload `foo.nt` directly by using `WebView` or `agload` later.

* import and compress data to disk

```bash
> ./ag-transe-cli import -training-data-dir OpenKE/benchmarks/FB15K237/ -save-ntriples-to /tmp/foo.nt -compress -entity-uri-prefix "http://example.org/" -relation-uri-prefix "http://example.org/Property#"
INFO - 18:18:53: Writing all triples to '/tmp/foo.nt'
INFO - 18:21:02: All triples have been successfully written and archived to '/tmp/foo.nt.bz2'
```

Users can upload `foo.nt.bz2` directly by using `WebView` or `agload` later.

## Export data

To export training data  from a AllegroGraph repository, use `export` subcommand.

```bash
> ag-transe-cli export -h
usage: ag-transe-cli [-h] [-output-dir OUTPUT_DIR] [-repo REPO] [-ag-env AG_ENV] [-train-size TRAIN_SIZE]
                     [-validate-size VALIDATE_SIZE] [-random-state RANDOM_STATE] [-entity-type ENTITY_TYPE]
                     [-relation-type RELATION_TYPE]

optional arguments:
  -h, --help            show this help message and exit
  -output-dir OUTPUT_DIR
                        The directory for writing 'entity2id.txt', 'relation2id.txt', 'train2id.txt', 'valid2id.txt', 'test2id.txt'
  -repo REPO            Name of the repository to be populated
  -ag-env AG_ENV        A text file that has environment varibles for connecting to AllegroGraph, e.g. 'AGRAPH_HOST', 'AGRAPH_PORT'
  -train-size TRAIN_SIZE
                        A float defines the ratio of trainning dataset; default to be 0.6
  -validate-size VALIDATE_SIZE
                        A float defines the ratio of trainning dataset; default to be 0.2
  -random-state RANDOM_STATE
                        An integer to intialize the random state which will be using during splitting data; it's usually used for
                        reproducibility
  -entity-type ENTITY_TYPE
                        Type of entities, default to rdfs:Class if not given; Must be a valid uri
  -relation-type RELATION_TYPE
                        Type of relations, default to rdf:Property if not given; Must be a valid uri
```

To connect to AllegroGraph, users can use either enviroment variables or the `ag-env` argument as mentioned earlier.

`train-size` and `validate-size` are `0.6` and `0.2` by default, `test-size` will be calculated accordingly e.g. `1.0 - train-size - validate-size`.

`-entity-type` and `-relation-type` are important, as they restrict the types of entities and relations that are extracted from the knowledge graph.

### Examples of exporting

* export training data to `/tmp/foo` from `foobar` repo

```bash
> ./ag-transe-cli export -output-dir /tmp/foo -repo foobar -ag-env ag.env -train-size 0.7 -validate-size 0.15
INFO - 18:37:23: 'entity2id.txt' has been written
INFO - 18:37:23: 'relation2id.txt' has been written
INFO - 18:37:37: 'train2id.txt' has been written
INFO - 18:37:37: 'validate2id.txt' has been written
INFO - 18:37:37: 'test2id.txt' has been written

> ls /tmp/foo
entity2id.txt    relation2id.txt  test2id.txt      train2id.txt     validate2id.txt
```

* reproduce training data by using `-random-state`

```bash
> ./ag-transe-cli export -output-dir /tmp/foo -repo foobar -ag-env ag.env -train-size 0.7 -validate-size 0.15 -random-state 42
INFO - 18:37:23: 'entity2id.txt' has been written
INFO - 18:37:23: 'relation2id.txt' has been written
INFO - 18:37:37: 'train2id.txt' has been written
INFO - 18:37:37: 'validate2id.txt' has been written
INFO - 18:37:37: 'test2id.txt' has been written

> ./ag-transe-cli export -output-dir /tmp/bar -repo foobar -ag-env ag.env -train-size 0.7 -validate-size 0.15 -random-state 42
INFO - 18:37:23: 'entity2id.txt' has been written
INFO - 18:37:23: 'relation2id.txt' has been written
INFO - 18:37:37: 'train2id.txt' has been written
INFO - 18:37:37: 'validate2id.txt' has been written
INFO - 18:37:37: 'test2id.txt' has been written

> diff -q /tmp/foo/train2id.txt /tmp/bar/train2id.txt
# no output
```

As indicated by `diff`, the produced `train2id.txt` files are identical.

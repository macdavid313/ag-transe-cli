"""
File: export_data.py
Created Date: Tuesday, 17th November 2020 3:44:50 am
Author: Tianyu Gu (gty@franz.com)
"""


import logging
import random
import sys
from pathlib import Path
from typing import List, Optional

import plac
import validators
from bidict import bidict
from dotenv import load_dotenv
from franz.openrdf.model.value import URI
from franz.openrdf.query.query import QueryLanguage
from franz.openrdf.vocabulary import RDF, RDFS

from ag_transe_cli.connection import AG_CONN

logging.basicConfig(
    format="%(levelname)s - %(asctime)s: %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)


def get_entity2id(repo: str, entity_type: URI) -> bidict[URI, int]:
    entity2id = {}
    with AG_CONN(repo) as conn:
        query = f"""SELECT ?ent ?id WHERE {{
  ?ent a {entity_type.toNTriples()} ;
         <http://example.org/embeddings#hasID> ?id .
}}"""
        tuple_query = conn.prepareTupleQuery(QueryLanguage.SPARQL, query)
        with tuple_query.evaluate() as res:
            for bindings in res:
                ent = bindings.getValue("ent")
                i = bindings.getValue("id").intValue()
                entity2id[ent] = i
    return bidict(entity2id)


def get_relation2id(repo: str, relation_type: URI) -> bidict[URI, int]:
    relation2id = {}
    with AG_CONN(repo) as conn:
        query = f"""SELECT ?ent ?id WHERE {{
  ?ent a {relation_type.toNTriples()} ;
         <http://example.org/embeddings#hasID> ?id .
}}"""
        tuple_query = conn.prepareTupleQuery(QueryLanguage.SPARQL, query)
        with tuple_query.evaluate() as res:
            for bindings in res:
                ent = bindings.getValue("ent")
                i = bindings.getValue("id").intValue()
                relation2id[ent] = i
    return bidict(relation2id)


def write_entity2id_relation2id(
    output_dir: Path, entity2id: bidict[URI, int], relation2id: bidict[URI, int]
):
    def _writer(fname: str, d: bidict[URI, int]):
        with output_dir.joinpath(fname).open("w") as fp:
            fp.write(f"{len(d)}\n")
            for i in range(0, len(d)):
                ent = d.inverse[i]
                fp.write(f"{ent.getURI()}\t{i}\n")
        logging.info("'%s' has been written", fname)

    _writer("entity2id.txt", entity2id)
    _writer("relation2id.txt", relation2id)


def load_all_triple_ids(
    repo: str,
    entity2id: bidict[URI, int],
    relation2id: bidict[URI, int],
    entity_type: URI,
    relation_type: URI,
) -> List[List[int]]:
    all_triple_ids = []
    with AG_CONN(repo) as conn:
        query = f"""SELECT DISTINCT ?ent1 ?ent2 ?rel WHERE {{
  ?ent1 a {entity_type.toNTriples()} .
  ?ent2 a {entity_type.toNTriples()} .
  ?rel a {relation_type.toNTriples()} .
  ?ent1 ?rel ?ent2 .
}}"""
        tuple_query = conn.prepareTupleQuery(QueryLanguage.SPARQL, query)
        with tuple_query.evaluate() as res:
            for bindings in res:
                ent1 = bindings.getValue("ent1")
                ent2 = bindings.getValue("ent2")
                rel = bindings.getValue("rel")
                if ent1 in entity2id and ent2 in entity2id and rel in relation2id:
                    all_triple_ids.append(
                        [entity2id[ent1], entity2id[ent2], relation2id[rel]]
                    )
    return all_triple_ids


def split_triples(
    triple_ids: List[List[int]],
    train_size: float,
    validate_size: float,
    random_state: Optional[int],
):
    total = len(triple_ids)
    train_offset = int(total * train_size)
    validate_offset = int(total * (train_size + validate_size))

    if random_state:
        random.seed(random_state)

    random.shuffle(triple_ids)
    return (
        triple_ids[0:train_offset],
        triple_ids[train_offset:validate_offset],
        triple_ids[validate_offset:],
    )


def write_triples(output_dir: Path, fname: str, triple_ids: List[List[int]]):
    with output_dir.joinpath(fname).open("w") as fp:
        fp.write(f"{len(triple_ids)}\n")
        for ids in triple_ids:
            fp.write(f"{ids[0]}\t{ids[1]}\t{ids[2]}\n")
    logging.info("'%s' has been written", fname)


@plac.annotations(
    output_dir=(
        "The directory for writing 'entity2id.txt', 'relation2id.txt', 'train2id.txt', 'valid2id.txt', 'test2id.txt'",
        "option",
    ),
    repo=(
        "Name of the repository to be populated",
        "option",
    ),
    ag_env=(
        "A text file that has environment varibles for connecting to AllegroGraph, e.g. 'AGRAPH_HOST', 'AGRAPH_PORT'",
        "option",
    ),
    train_size=(
        "A float defines the ratio of trainning dataset; default to be 0.6",
        "option",
    ),
    validate_size=(
        "A float defines the ratio of trainning dataset; default to be 0.2",
        "option",
    ),
    random_state=(
        "An integer to intialize the random state which will be using during splitting data; it's usually used for reproducibility",
        "option",
    ),
    entity_type=(
        "Type of entities, default to rdfs:Class if not given; Must be a valid uri",
        "option",
    ),
    relation_type=(
        "Type of relations, default to rdf:Property if not given; Must be a valid uri",
        "option",
    ),
)
def export_data(
    output_dir: str,
    repo: str,
    ag_env: Optional[str],
    train_size: Optional[float],
    validate_size: Optional[float],
    random_state: Optional[int],
    entity_type: Optional[str],
    relation_type: Optional[str],
):
    if not output_dir:
        sys.exit("'output_dir' is not given")
    output_dir = Path(output_dir).absolute()
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    if output_dir.exists() and not output_dir.is_dir():
        sys.exit(f"'output_dir' is not a directory: '{output_dir}'")

    if not repo:
        sys.exit("Name of the repository is required")

    if ag_env:
        ag_env = Path(ag_env)
        if not ag_env.exists():
            sys.exit(f"ag_env file doesn't exist: '{ag_env.absolute()}''")
        try:
            load_dotenv(ag_env, verbose=True)
        except Exception as _:
            logging.warning(
                f"Cannot load environment variables from ag_env file: '{ag_env.absolute()}'"
            )

    if not train_size:
        train_size = 0.6
    elif isinstance(train_size, str):
        try:
            train_size = float(train_size)
            if train_size < 0.0 or train_size > 1.0:
                sys.exit(f"train_size must be a valid float number: {train_size}")
        except Exception as _:
            sys.exit(f"train_size must be a valid float number: {train_size}")

    if not validate_size:
        validate_size = 0.2
    elif isinstance(validate_size, str):
        try:
            validate_size = float(validate_size)
            if validate_size < 0.0 or validate_size > 1.0:
                sys.exit(f"validate_size must be a valid float number: {validate_size}")
        except Exception as _:
            sys.exit(f"validate_size must be a valid float number: {validate_size}")

    test_size = 1.0 - train_size - validate_size
    if test_size < 0.0 or test_size > 1.0:
        sys.exit(f"test_size must be a valid float number: {test_size}")

    if train_size + validate_size + test_size > 1.0:
        sys.exit(
            f"Illegal train_size and validate_size: '{train_size}', '{validate_size}'"
        )

    if random_state:
        try:
            random_state = int(random_state)
        except Exception as _:
            sys.exit(f"random_state must be an integer: {random_state}")

    if not entity_type:
        entity_type = RDFS.CLASS
    elif validators.url(entity_type):
        entity_type = URI(entity_type)
    else:
        sys.exit(f"'entity_type' is not a valid uri: '{entity_type}'")

    if not relation_type:
        relation_type = RDF.PROPERTY
    elif validators.url(relation_type):
        relation_type = URI(relation_type)
    else:
        sys.exit(f"'relation_type' is not a valid uri: '{relation_type}'")

    entity2id = get_entity2id(repo, entity_type)
    relation2id = get_relation2id(repo, relation_type)
    write_entity2id_relation2id(output_dir, entity2id, relation2id)

    all_triple_ids = load_all_triple_ids(
        repo, entity2id, relation2id, entity_type, relation_type
    )
    train, validate, test = split_triples(
        all_triple_ids, train_size, validate_size, random_state
    )
    write_triples(output_dir, "train2id.txt", train)
    write_triples(output_dir, "valid2id.txt", validate)
    write_triples(output_dir, "test2id.txt", test)


if __name__ == "__main__":
    plac.call(export_data)

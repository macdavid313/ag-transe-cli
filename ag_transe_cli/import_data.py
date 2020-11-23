"""
File: ag_transe_import.py
Created Date: Monday, 16th November 2020 7:06:43 pm
Author: Tianyu Gu (gty@franz.com)
"""


import bz2
import logging
import os
import sys
import urllib.parse
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from typing import Generator, Optional, Tuple

import plac
import validators
from bidict import bidict
from dotenv import load_dotenv
from franz.openrdf.model.value import URI
from franz.openrdf.repository.repository import RepositoryConnection
from franz.openrdf.vocabulary import RDF, RDFS

from ag_transe_cli.connection import AG_CONN

logging.basicConfig(
    format="%(levelname)s - %(asctime)s: %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)


def get_entity2id_relation2id(
    dir: Path, ent_prefix: Optional[str], rel_prefix: Optional[str]
) -> Tuple[bidict[str, int], bidict[str, int]]:
    def _read_file(path: Path, nm: Optional[str]):
        d = {}
        with path.open("r") as f:
            f.readline()
            for line in f:
                s, i = line.split("\t")
                if validators.url(urllib.parse.quote(s, safe="~@#$&()*!+=:;,.?/'")):
                    s = urllib.parse.quote(s, safe="~@#$&()*!+=:;,.?/'")
                    d[s] = int(i)
                else:
                    if not nm:
                        sys.exit(
                            f"Content does not contain valid URIs, but namespace are not given: '{path}'"
                        )
                    d[URI(namespace=nm, localname=s).getURI()] = int(i)
        return bidict(d)

    return (
        _read_file(dir.joinpath("entity2id.txt"), ent_prefix),
        _read_file(dir.joinpath("relation2id.txt"), rel_prefix),
    )


def read_triples_iter(
    path: Path, entity2id: bidict[str, int], relation2id: bidict[str, int]
) -> Generator[str, None, None]:
    with path.open("r") as f:
        f.readline()
        for line in f:
            e1_id, e2_id, rel_id = line.split()
            yield f"<{entity2id.inverse[int(e1_id)]}> <{relation2id.inverse[int(rel_id)]}> <{entity2id.inverse[int(e2_id)]}> .\n"


def load_all_triples(
    conn: Optional[RepositoryConnection],
    save_to: Optional[Path],
    training_data_dir: Path,
    entity2id: bidict[str, int],
    relation2id: bidict[str, int],
    entity_type: URI,
    relation_type: URI,
) -> None:
    with TemporaryDirectory() as tmp_dir:
        nt_file = Path(tmp_dir).joinpath("triples.nt")
        with nt_file.open("w") as fp:
            pred = URI("http://example.org/embeddings#hasID")
            for ent, i in entity2id.items():
                fp.write(
                    f"<{ent}> {RDF.TYPE.toNTriples()} {entity_type.toNTriples()} .\n"
                )
                fp.write(
                    f'<{ent}> {pred.toNTriples()} "{i}"^^<http://www.w3.org/2001/XMLSchema#integer> .\n'
                )
            for rel, i in relation2id.items():
                fp.write(
                    f"<{rel}> {RDF.TYPE.toNTriples()} {relation_type.toNTriples()} .\n"
                )
                fp.write(
                    f'<{rel}> {pred.toNTriples()} "{i}"^^<http://www.w3.org/2001/XMLSchema#integer> .\n'
                )
            for fname in ("train2id.txt", "test2id.txt", "valid2id.txt"):
                for triple in read_triples_iter(
                    training_data_dir.joinpath(fname), entity2id, relation2id
                ):
                    fp.write(triple)
        if conn:
            conn.addFile(str(nt_file), format="application/n-triples")
            conn.commit()
        else:
            copyfile(nt_file, save_to)


@plac.annotations(
    training_data_dir=(
        "Path to training data where it must contain 'entity2id.txt', 'relation2id.txt', 'train2id.txt', 'valid2id.txt', 'test2id.txt'",
        "option",
    ),
    repo=(
        "Name of the repository to be populated; The repository will be re-newed if it already exists and will conflict with 'save_ntriples_to' if both given",
        "option",
    ),
    ag_env=(
        "A text file that has environment varibles for connecting to AllegroGraph, e.g. 'AGRAPH_HOST', 'AGRAPH_PORT'",
        "option",
    ),
    save_ntriples_to=(
        "Path to save a serialization of all triples in NTriples format; It will conflict with 'repo' if both given",
        "option",
    ),
    compress=(
        "If given, the saved ntriples serialization will be compressed; Only meaningful when 'save_ntriples_to' is valid",
        "flag",
    ),
    entity_uri_prefix=(
        "Namespace for entities; Only applied when entities from 'entity2id.txt' are not URIs",
        "option",
    ),
    relation_uri_prefix=(
        "Namespace for relations; Only applied when relations from 'relation2id.txt' are not URIs",
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
def import_data(
    training_data_dir: str,
    repo: str,
    ag_env: str,
    save_ntriples_to: str,
    compress: bool,
    entity_uri_prefix: str,
    relation_uri_prefix: str,
    entity_type: Optional[str],
    relation_type: Optional[str],
):
    training_data_dir = Path(training_data_dir)
    if not training_data_dir.exists():
        sys.exit(f"Training Data folder does not exist: {training_data_dir}")
    if not training_data_dir.is_dir():
        sys.exit(f"Training Data folder is not a folder: {training_data_dir}")
    else:
        filenames = [f.name for f in training_data_dir.glob("*.txt")]
        for file in (
            "entity2id.txt",
            "relation2id.txt",
            "train2id.txt",
            "valid2id.txt",
            "test2id.txt",
        ):
            if file not in filenames:
                sys.exit(
                    f"Cannot find '{file}' in Training Data folder: {training_data_dir}"
                )

    if entity_uri_prefix and not validators.url(entity_uri_prefix):
        sys.exit(f"Illegal prefix for entity URIs: '{entity_uri_prefix}'")
    if relation_uri_prefix and not validators.url(relation_uri_prefix):
        sys.exit(f"Illegal prefix for relation URIs: '{relation_uri_prefix}'")

    if entity_uri_prefix and relation_uri_prefix:
        ENT_PREFIX = entity_uri_prefix
        REL_PREFIX = relation_uri_prefix
        entity2id, relation2id = get_entity2id_relation2id(
            training_data_dir, ENT_PREFIX, REL_PREFIX
        )
    else:
        entity2id, relation2id = get_entity2id_relation2id(
            training_data_dir, None, None
        )

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

    if repo and not save_ntriples_to:
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

        AG_CONN.renew_or_create(repo)

        with AG_CONN(repo) as conn:
            logging.info("Adding all triples to '%s'", repo)
            load_all_triples(
                conn,
                None,
                training_data_dir,
                entity2id,
                relation2id,
                entity_type,
                relation_type,
            )
            logging.info("All triples successfully loaded to '%s'", repo)
    elif save_ntriples_to and not repo:
        save_ntriples_to = Path(save_ntriples_to).absolute()
        if save_ntriples_to.exists() and not save_ntriples_to.is_file():
            sys.exit(
                f"Path for saving triples (NTriples format) is not a file: '{save_ntriples_to}'"
            )
        logging.info("Writing all triples to '%s'", save_ntriples_to)
        load_all_triples(
            None,
            save_ntriples_to,
            training_data_dir,
            entity2id,
            relation2id,
            entity_type,
            relation_type,
        )
        if compress:
            with bz2.open(f"{save_ntriples_to}.bz2", "w") as out:
                with save_ntriples_to.open("rb") as fp:
                    content = fp.read()
                out.write(content)
            os.remove(save_ntriples_to)
            logging.info(
                "All triples have been successfully written and archived to '%s.bz2'",
                save_ntriples_to,
            )
        else:
            logging.info(
                "All triples have been successfully written to '%s'", save_ntriples_to
            )
    else:
        sys.exit("One and only one of 'repo' and 'save_ntriples_to' must be given")

#! /usr/local/bin/python

import argparse
import json
import os

from hazard_options import create_menu_options, create_menu_options_local


def parse_arguments():
    """
    Parses command-line arguments for the request.

    Returns:
        argparse.Namespace: An object that holds the parsed arguments as
        attributes.
    """
    parser = argparse.ArgumentParser(description="Make a request.")
    parser.add_argument("--catalog_url", type=str, help="Link to the catalog")
    return parser.parse_args()


def get_hazard_options(catalog_url: str):
    haz_options = create_menu_options(catalog_url)
    return haz_options

def get_catalog() -> dict:
    return {
        "stac_version": "1.0.0",
        "id": "asset-vulnerability-catalog",
        "type": "Catalog",
        "description": "OS-C physrisk asset vulnerability catalog",
        "links": [
            {"rel": "self", "href": "./catalog.json"},
            {"rel": "root", "href": "./catalog.json"},
        ],
    }


if __name__ == "__main__":
    print("STARTING THE PROCESS")
    args = parse_arguments()
    print(args)
    hazard_options = get_hazard_options(args.catalog_url)
    # Make a stac catalog.json file to satitsfy the process runner
    os.makedirs("asset_output", exist_ok=True)
    with open("./asset_output/catalog.json", "w",encoding="utf8") as f:
        catalog = get_catalog()
        catalog["data"] = hazard_options
        json.dump(catalog, f)
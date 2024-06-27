"""
This module contains a function to generate menu options for a user interface.
"""

import itertools
import json
import logging
import re
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from s3pathlib import S3Path

# Set up logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


def download_from_s3(s3_url: str) -> dict:
    """
    Downloads a file from S3 and returns its content as a dictionary.

    Parameters:
    s3_url (str): The S3 URL of the file to download.

    Returns:
    dict: The content of the file as a dictionary.
    """
    logger.debug("Downloading from S3: %s", s3_url)
    # Parse the S3 URL
    s3_path = S3Path(s3_url)
    s3_bucket, s3_key = s3_path.bucket, s3_path.key

    logger.debug("Bucket: %s, Key: %s", s3_bucket, s3_key)

    # Create an S3 client
    s3 = boto3.client("s3", aws_access_key_id="", aws_secret_access_key="")
    s3._request_signer.sign = lambda *args, **kwargs: None

    try:
        obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        data = obj["Body"].read()
        # parse json object
        data = json.loads(data)
        return data
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except ClientError as e:
        print(f"Error downloading from S3: {e}")
        return False


def get_item_links(catalog_url: str) -> list[str]:
    """
    Returns a list of item links from a STAC catalog.

    Parameters:
    catalog_url (str): The URL of the STAC catalog.

    Returns:
    List[str]: A list of item links.
    """
    catalog_data = download_from_s3(catalog_url)
    base_url = S3Path(catalog_url).parent
    items = [
        (base_url / Path(link["href"]).as_posix()).uri
        for link in catalog_data["links"]
        if link["rel"] == "item"
    ]
    return items


def get_hazard_types(data: dict) -> list[dict]:
    """
    This function generates hazard type options from the provided data.

    Parameters:
    data (dict): A dictionary containing properties and scenarios.

    Returns:
    list[dict]: A list of dictionaries containing hazard type options.
    """
    hazard_type = data["properties"]["osc-hazard:hazard_type"]
    hazard_type_list = [
        {"label": re.sub(r"(?<!^)(?=[A-Z])", " ", hazard_type), "value": hazard_type}
    ]
    return dedupe_dict(hazard_type_list)


def get_climate_model_options(params: dict) -> list[dict]:
    """
    This function generates climate model options from the provided parameters.

    Parameters:
    params (dict): A dictionary containing parameters.

    Returns:
    list[dict]: A list of dictionaries containing climate model options.
    """
    if "gcm" in params:
        return [{"value": gcm, "label": "CMIP6: " + gcm} for gcm in params["gcm"]]
    else:
        return []


def get_scenario_options(scenarios: dict) -> list[dict]:
    """
    This function generates scenario options from the provided scenarios.

    Parameters:
    scenarios (dict): A dictionary containing scenarios.

    Returns:
    list[dict]: A list of dictionaries containing scenario options.
    """
    scenario_options = []
    for scene in scenarios:
        if scene["id"].startswith("ssp") and len(scene["id"]) == 6:
            formatted_id = f"SSP{scene['id'][3]}-{scene['id'][4]}.{scene['id'][5:]}"
        elif scene["id"].startswith("rcp"):
            formatted_id = f"RCP-{(scene['id'][3:]).replace('p', '.')}"
        else:
            formatted_id = scene["id"]
        scenario_options.append(
            {
                "label": formatted_id,
                "value": scene["id"],
                "year_options": scene["years"],
            }
        )
    return dedupe_dict(scenario_options)


class CustomDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def get_indicator_options(data: dict) -> list[dict]:
    """
    This function generates indicator options from the provided parameters.

    Parameters:
    params (dict): A dictionary containing parameters.

    Returns:
    list[dict]: A list of dictionaries containing indicator options.
    """
    params = data["properties"]["osc-hazard:params"]
    indicator_options = []
    param_values = list(itertools.product(*params.values()))
    for values in param_values:
        props = data["properties"]
        param_dict = dict(zip(params.keys(), values))
        # Checks if there are keys in param_dict
        if not param_dict:
            display_name = props["osc-hazard:display_name"]
            path = data["properties"]["osc-hazard:path"]
        # Check if all keys are in the strings
        for key in param_dict.keys():
            if key not in props["osc-hazard:indicator_id"]:
                display_name = (
                    props["osc-hazard:display_name"]
                    .replace("{" + key + "}", "")
                    .format(**param_dict)
                )
            else:
                display_name = props["osc-hazard:display_name"].format(**param_dict)
            path = (data["properties"]["osc-hazard:path"]).format_map(
                CustomDict(**param_dict)
            )
        indicator_id = (
            props["osc-hazard:indicator_id"].replace("/", "_").format(**param_dict)
        )
        if props['osc-hazard:indicator_model_id']:
            indicator_id = indicator_id + "_" + props['osc-hazard:indicator_model_id'].replace("/", "_")
        
        if props["osc-hazard:indicator_model_gcm"] != 'unknown' and props["osc-hazard:indicator_model_gcm"] != "{gcm}":
            indicator_id = indicator_id + "_" + props["osc-hazard:indicator_model_gcm"]
        
        indicator_options.append(
            {
                "label": display_name,
                "value": indicator_id,
                "path": path,
            }
        )
    return dedupe_dict(indicator_options)


def get_menu_items_from_file(data: dict) -> list[dict]:
    """
    This function generates indicator options, climate model options, and scenario
    options from the provided data.

    Parameters:
    data (dict): A dictionary containing properties and scenarios.

    Returns:
    list[dict]: A list of dictionaries containing indicator options, climate model
    options, and scenario options.
    """

    climate_model_options = get_climate_model_options(
        data["properties"]["osc-hazard:params"]
    )

    scenario_options = get_scenario_options(data["properties"]["osc-hazard:scenarios"])

    indicator_options = get_indicator_options(data)

    hazard_types = get_hazard_types(data)

    return indicator_options, climate_model_options, scenario_options, hazard_types


def dedupe_dict(dict_list: list[dict]) -> list[dict]:
    """
    Removes duplicates from a list of dictionaries.

    Parameters:
    dict_list (list[dict]): A list of dictionaries.

    Returns:
    list[dict]: A list of dictionaries with duplicates removed.
    """
    unique = []
    for item in dict_list:
        if item not in unique:
            unique.append(item)
    return unique


def update_options(
    single_list: list[dict],
    main_list: list[dict],
    options_dicts: list[dict],
):
    """
    Updates the options of items in the main list with the options from the options
    list. If an item from the single list does not exist in the main list, it is added
    to the main list.

    Parameters:
    single_list (list): A list of dictionaries, each containing a 'label' key
    and an 'options' key.
    main_list (list): A list of dictionaries, each containing a 'label' key
    and an 'options' key.
    options_dicts (list): A list of dictionaries, each containing
    a 'name' key and a 'list' key.


    Returns:
    list: The updated main list.
    """
    for single_item in single_list:
        for main_item in main_list:
            if main_item["label"] == single_item["label"]:
                for option in options_dicts:
                    options_name = option["name"]
                    options_list = option["list"]
                    if options_list != []:
                        main_item[options_name] += [
                            option["value"]
                            for option in options_list
                            if option["value"] not in main_item[options_name]
                        ]
                break
        else:
            if options_dicts != []:
                for option in options_dicts:
                    options_name = option["name"]
                    options_list = option["list"]
                    if options_list != []:
                        single_item[options_name] = [
                            option["value"] for option in options_list
                        ]
            main_list.append(single_item)
    return main_list


def create_menu_options(catalog_url: str) -> list[dict]:
    """
    This function generates menu options from the provided catalog URL.

    Parameters:
    catalog_url (str): A URL to a catalog.

    Returns:
    list[dict]: A list of dictionaries containing menu options.
    """
    indicator_options = []
    climate_model_options = []
    scenario_options = []
    hazard_types = []
    item_links = get_item_links(catalog_url)
    for item in item_links:
        data = download_from_s3(item)
        (
            indicator_options_single,
            climate_model_options_single,
            scenario_options_single,
            hazard_types_single,
        ) = get_menu_items_from_file(data)
        # Combine the lists
        hazard_types = update_options(
            hazard_types_single,
            hazard_types,
            options_dicts=[
                {"name": "indicator_options", "list": indicator_options_single}
            ],
        )
        indicator_options = update_options(
            indicator_options_single,
            indicator_options,
            options_dicts=[
                {"name": "climate_model_options", "list": climate_model_options_single},
                {"name": "scenario_options", "list": scenario_options_single},
            ],
        )
        climate_model_options = update_options(
            climate_model_options_single,
            climate_model_options,
            options_dicts=[
                {"name": "scenario_options", "list": scenario_options_single}
            ],
        )
        scenario_options = update_options(
            scenario_options_single, scenario_options, options_dicts=[]
        )

    return {
        "climateModelOptions": climate_model_options,
        "scenarioOptions": scenario_options,
        "indicatorOptions": indicator_options,
        "hazardTypes": hazard_types,
    }


def create_menu_options_local(json_file: str) -> dict:
    """
    This function generates menu options from the provided json file.

    Parameters:
    json_file (str): A json file containing menu options.

    Returns:
    dict: A dictionary containing menu options.
    """
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)
    return data


def save_menu_options_to_file(menu_options: dict, output_file: str):
    """
    This function saves menu options to a file.

    Parameters:
    menu_options (dict): A dictionary containing menu options.
    output_file (str): The output file path.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(menu_options, f, ensure_ascii=False, indent=4)

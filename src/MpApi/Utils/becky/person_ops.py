import tomllib
import tomli_w
from pathlib import Path


def open_person_cache(conf: dict) -> dict:
    cache_fn = conf["project_dir"] / conf["person_cache"]
    if not cache_fn.exists():
        print(">> Starting new person cache")
        return {}

    print(f">> Person cache from file'{cache_fn}'")
    with open(cache_fn, "rb") as toml_file:
        person_data = tomllib.load(toml_file)
        return person_data


def save_person_cache(*, conf: dict, data: dict) -> None:
    print(">> Saving person cache")
    cache_fn = conf["project_dir"] / conf["person_cache"]
    # Write the data to a TOML file
    with open(cache_fn, "wb") as toml_file:
        tomli_w.dump(data, toml_file)

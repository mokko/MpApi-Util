import tomllib
import tomli_w
from pathlib import Path


def open_geo_cache(conf: dict) -> dict:
    cache_fn = conf["project_dir"] / conf["geo_cache"]
    return _open(cache_fn, "Geo cache")


def open_person_cache(conf: dict) -> dict:
    cache_fn = conf["project_dir"] / conf["person_cache"]
    return _open(cache_fn, "Person cache")


def save_person_cache(*, conf: dict, data: dict) -> None:
    print(">> Saving person cache")
    cache_fn = conf["project_dir"] / conf["person_cache"]
    _save(cache_fn)


def save_geo_cache(*, conf: dict, data: dict) -> None:
    print(">> Saving geo cache")
    cache_fn = conf["project_dir"] / conf["geo_cache"]
    _save(cache_fn)


#
# more privately
#


def _open(cache_fn: Path, name: str) -> dict:
    if not cache_fn.exists():
        print(">> Starting new {name}")
        return {}

    print(f">> {name} from file'{cache_fn}'")
    with open(cache_fn, "rb") as toml_file:
        data = tomllib.load(toml_file)
        return data


def _save(cache_fn):  # Write data to a TOML file
    with open(cache_fn, "wb") as toml_file:
        tomli_w.dump(data, toml_file)

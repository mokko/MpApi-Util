import tomllib
import tomli_w
from pathlib import Path

changed = False  # global variable


def open_archive_cache(conf: dict) -> dict:
    cache_fn = conf["project_dir"] / conf["archive_cache"]
    return _open(cache_fn, "Archive cache")


def open_geo_cache(conf: dict) -> dict:
    cache_fn = conf["project_dir"] / conf["geo_cache"]
    return _open(cache_fn, "Geo cache")


def open_person_cache(conf: dict) -> dict:
    cache_fn = conf["project_dir"] / conf["person_cache"]
    return _open(cache_fn, "Person cache")


def reset_change():
    global changed
    changed = False


def save_archive_cache(*, conf: dict, data: dict) -> None:
    cache_fn = conf["project_dir"] / conf["archive_cache"]
    _save(cache_fn, data)


def save_geo_cache(*, conf: dict, data: dict) -> None:
    cache_fn = conf["project_dir"] / conf["geo_cache"]
    _save(cache_fn, data)


def save_person_cache(*, conf: dict, data: dict) -> None:
    cache_fn = conf["project_dir"] / conf["person_cache"]
    _save(cache_fn, data)


def set_change():
    """
    set internal variable to indicate that cache contents have been changed
    and need saving
    """
    global changed
    changed = True


#
# more privately
#


def _open(cache_fn: Path, name: str) -> dict:
    if not cache_fn.exists():
        print(f">> Starting new {name} ({cache_fn})")
        return {}

    print(f">> {name} from file'{cache_fn}'")
    with open(cache_fn, "rb") as toml_file:
        data = tomllib.load(toml_file)
        return data


def _save(cache_fn: str, data: dict) -> None:  # Write data to a TOML file
    if changed:
        print(">> Saving cache")
        with open(cache_fn, "wb") as toml_file:
            tomli_w.dump(data, toml_file)
        reset_change()

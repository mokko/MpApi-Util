# Installing MpApi.Utils

## Requirements

- Python 3.11.1 or newer (the code uses union types with `|`)
- Three packages, none of them on PyPI:
  - **MpApi.Utils** — this one, the command line tools
  - **MpApi** — the client, <https://github.com/mokko/MpApi>
  - **MpApi.Record** — logic for single moduleItems, <https://github.com/mokko/MpApi-Record>

The two siblings are declared as direct references in `pyproject.toml`, so pip
fetches them from their repositories on its own. Nothing else has to be cloned
by hand.

## Install from github

```
pip install git+https://github.com/mokko/MpApi-Util
```

This pulls `mpapi` and `mpapi-record` along with it. On a current Linux
distribution the system Python is "externally managed" and pip refuses to install
into it, so make a virtual environment first:

```
uv venv .venv          # or: python3 -m venv .venv
uv pip install --python .venv/bin/python "git+https://github.com/mokko/MpApi-Util"
```

## Install from clones (editable)

For work on the code, all three belong side by side and all three editable, so an
edit in any of them takes effect immediately:

```
git clone https://github.com/mokko/MpApi.git
git clone https://github.com/mokko/MpApi-Record.git
git clone https://github.com/mokko/MpApi-Util.git
cd MpApi-Util
uv venv .venv
uv pip install --python .venv/bin/python -e .                # deps, and the siblings from github
uv pip install --python .venv/bin/python --no-deps -e ../MpApi -e ../MpApi-Record
```

**The second command is not optional.** Because the siblings are declared as git
references, a resolver asked to install a local `-e ../MpApi` alongside them
stops with

```
Requirements contain conflicting URLs for package `mpapi`:
  - file:///home/you/py/MpApi (editable)
  - git+https://github.com/mokko/MpApi
```

so install the declared dependencies first, then replace the two GitHub copies
with the local clones using `--no-deps`. Afterwards all three are editable:

```
MpApi         0.1.10  /home/you/py/MpApi
MpApi.Record  0.0.1   /home/you/py/MpApi-Record
MpApi.Utils   0.0.11  /home/you/py/MpApi-Util
```

uv writes a `.venv/.gitignore` containing `*`, so a uv environment ignores itself
and needs no entry in `.gitignore` (a `python3 -m venv` one does).

## Configuration

Same as MpApi: credentials at `~/.ria`

```
user = "EM_XY"
pw = "pass"
baseURL = "https://museumplus-produktiv.spk-berlin.de:8181/MpWeb-mpBerlinStaatlicheMuseen"
```

The instance above is behind a firewall and only answers from inside the museum
network.

Credentials are read **at import time**, so every tool needs this file before it
will even print its usage. Without it:

```
SyntaxError: RIA Credentials not found at /home/you/.ria
```

Jobs go in `jobs.toml` (see `New_toml_configuration.md` in MpApi). I keep jobs and
all the working data in `sdata/` inside the MpApi directory; it is not tracked by
git.

## The tools

```
attach   attach2   becky    count    mk_grp   mover    prepare
reportx  sren      update_schemas      up       uta
```

`attach`, `attach2`, `becky`, `count`, `mk_grp`, `mover`, `prepare`, `reportx`,
`sren`, `update_schemas`, `up` and `uta` all take `-h`.

**`restart` does not.** It is a shell command repeater — `restart -x 3 echo m` —
with no argument parser, so it treats `-h` as the command to run and then loops
forever. Interrupt it with CTRL+C.

## Checking the install

```
attach -h
```

## Tests

```
.venv/bin/python -m pytest -q
```

Expect failures without the museum network: the suite reaches the real RIA
instance (`requests.exceptions.ConnectionError`), reads `sdata/` files that are
not in git, and looks up vocabulary entries that only exist on the server.

Running the suite in the repository root also leaves an untracked
`upload15.xlsx`: that is AssetUploader's Excel list (`AssetUploader.py:56`),
written into the current directory. It is not covered by `.gitignore`.

Two known local problems, unrelated to the install:

- `test/test_becky.py` imports `_is_space_etc` from `MpApi.Utils.becky.set_fields_Object`, which does not define it.
- `MpApi/Utils/IdentNr_Cache.py` line 36 says `from dataclass import dataclass, field` — the module is `dataclasses`. Nothing imports `IdentNr_Cache` yet, so the typo is currently dormant.

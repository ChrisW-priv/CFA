# CFA
Project created to allow easy simulation of cash flow and total networth based on some behaviour

## Start contributing

If you don't have `uv`:
```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```
or 
```powerchell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

And then simply:
```sh
git clone https://github.com/ChrisW-priv/CFA.git
cd CFA
uv sync
pre-commit install
```

## TODO

- Make nice UI
- Make simulation work with all the types of events, no just income
- Make inflation adjustable (val instead of bool + fixed 3)

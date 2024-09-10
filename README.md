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

- Add some more procedures like debt liabilities on the backend 
- Make frontend to allow making simulations with few button clicks
- Make nice UI

I would much rather create a list of json like objs that will say stuff like:
"start sim with n amount of cash"
"on negative cash: create debt with following params: [...]"
"from this to this date add x amount of money to the cash state"
"on this date buy x amount of compounding value asset {start, end, price, %per_year}, on the expiry date: execute this func"
"on the end of the sim, [true|false] draw picture"
"on the end of the sim, [true|false] return dataframe with data"

Based on this I need to define:

- income strategy:
    - strategies:
        - const: value
        - step_func: list of zipped start date and value
    - day apply [default: 10]
- living_expense strategy:
    - strategies:
        - const: value
        - step_func: list of zipped start date and value
    - day apply [default: 25]
- asset definition:
    - price for one
    - quantity
    - date_buy
    - asset value over time: curve based: like in prev. -> use the valuation func from next part, just make the date shorter
    - asset keep duration | asset expiry
    - func to calc value at the end:
        - const: x
        - compound: %year
        - step_func: list of zipped start date and value of single one
    - what to do on expiry (sell_asset=true|false [default: true]):
        - just get cash
        - buy the same asset
    - allow for the partial buy (can I buy 0.5 of an asset? [default=false])
- asset_buy strategy:
    - function that should allow the "smart" handling of state. common cases to include
        - buy this asset until date or from (date range guard, that is easy)
        - buy the asset for n amount of money
        - buy the asset for max money possible
- debt_payment strategy:
    - function that should allow the "smart" handling of state. common cases to include
        - pay only if the debt is actually there (check in the sim state if it exists and value is > 0)
        - pay n amount of money
        - pay max available money possible
        - pay max available money possible - some value
- strategy priority - either go first with asset or debt handling strategy [on missing: error]

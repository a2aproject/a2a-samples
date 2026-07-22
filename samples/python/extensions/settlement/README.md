# Settlement Extension Implementation

This is the Python implementation of the Settlement Extension in
`extensions/settlement/v1`.

The structure follows the timestamp extension: a `SettlementExtension` class
with support methods ranging from fully manual (build and read escrow
metadata yourself) to managed (`wrap_executor`, which verifies escrow on the
exchange before the agent runs).

The release decision stays with the client. After observing the terminal
task state, the client calls `settle(state, escrow_id)` which releases on
COMPLETED and refunds on FAILED / CANCELED / REJECTED. There is no path for
a provider to trigger release of its own payment.

## Usage

Server side:

```python
exchange = ExchangeClient('https://exchange.example.com/api/v1', api_key)
ext = SettlementExtension(exchange, account_id='my-provider-account')
executor = ext.wrap_executor(MyExecutor())
card = ext.add_to_card(my_card)
```

Client side:

```python
exchange = ExchangeClient('https://exchange.example.com/api/v1', api_key)
ext = SettlementExtension(exchange, account_id='my-client-account')

escrow = await exchange.create_escrow(provider_id=provider_account, amount=10)
ext.add_escrow_metadata(
    message,
    escrow_id=escrow['escrow_id'],
    amount=10,
    exchange_url='https://exchange.example.com/api/v1',
)
# ... send the message, watch for the terminal state ...
await ext.settle(final_state, escrow['escrow_id'])
```

## Tests

```bash
cd samples/python/extensions/settlement
uv sync --group dev
uv run pytest -v
```

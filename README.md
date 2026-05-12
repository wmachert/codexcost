# codexcost

codexcost collects cost relevant usage information from OpenAIs Codex local session store and outputs them in various formats.

## Usage

### Installation

At the moment there is no registered package, so you have to install codexcost directly from github, i.e. using uvx:

```sh
uv tool install --from git+https://github.com/wmachert/codexcost[all] codexcost
```

> The `all` extras include the dependencies for both the `follow` and `xlsx` features.

You can then run the tool using:
```sh
uvx codexcost
```

### Example Usage

Some useful parameters:

- show current month credit usage: `uvx codexcost`
- follow codex credit usage with extended informations: `uvx codexcost -ft ext`
- export all existing credit usage data in *csv* format to *usage.csv*: `uvx codexcost -at csv -o usage.csv`
- export all existing credit usage data as excel file to *usage.xlsx*: `uvx codexcost -at xlsx -o usage.xslx`
- show help page: `uvx codexcost --help`

## Linux / OSX Platform

As my Codex usage is constrained to a specific computer running Windows I cannot test codexcost with Linux / OSX (although it should work fine as long as codex stores it's session data in `~/.codex/sessions`).
If you encounter any problems on those platforms, create an issue and we'll try to find a solution.

## Credit calculation

Codex sessions periodically contain token_usage events, that state the current and total token usage for the previous messages (usually at least once after each task).

codexcost multiplies uncached input, cached input, and output tokens individually with the cost for the used model according to the [Codex rate card](https://help.openai.com/en/articles/20001106-codex-rate-card#codex-rate-card-token-based-pricing) for each of these token_usage events and accumulates the resulting credits.

While the calculation seems simple, there is no reliable published algorithm on how the actual cost is calculated.

To my knowledge there is also no clearly stated information about the credit budget per ChatGPT plan in any of OpenAIs documentation.
While the pricing states [usage limits](https://developers.openai.com/codex/pricing#what-are-the-usage-limits-for-my-plan), they only declare messages per time window - and are very vague in their estimates - a price-model that ChatGPT (along with other LLM providers) abandoned in April 2026. Enterprise and Educational plans have a negotiated fixed monthly credit budget, [api prices](https://developers.openai.com/api/docs/pricing) are well known, but all other plans do not have a clearly defined limit.

Keep that in mind when using codexcost.

**You should not rely on codexcosts numbers and only consider them a rough guideline for your usage.**

## License

codexcost is licensed unter [MIT license](LICENSE).

# Alpha Hardening / Harness Conformance

Alpha is gated, not released. The target is `alpha-v1`: independent Rust and
Python decisions against the same host facts, request context and candidates.
Broader research results are not production conformance results.

## Versioned policy

`terminal/resources/alpha-policy.json` defines audited CLI coverage. Installed
executable presence alone does not prove CLI validity. Unknown commands, options,
subcommands and unsupported operand shapes fail closed. Documentation remains
untrusted evidence and cannot add capabilities to this manifest. Literal requests
authorize only their exact candidate, subject to every remaining gate.

The deterministic trace records the contract, context validity, initial and final
parser/CLI/intent/safety/secret/risk decisions, correction rule, final command and
stageability. Unknown and skipped checks are not successes. The sole automatic
candidate correction chooses the first approved alternative for a known task
after invalid CLI options, and rechecks every gate; syntax/safety/secret failures
never enter correction. No literal-command operands are invented.

## Acceptance

Zero deterministic discrepancies and observed dangerous escapes; passing boundary,
property/fuzz and real-PTY suites; all final staging gates satisfied. Three release
benchmark runs of at least 200 warm explicit requests must each achieve p50 ≤750 ms
and p95 ≤1500 ms on the i7-1355U target with the verified current model. Invalid
responses are failures, not fast successes. No daily dogfood before these pass.

Dogfood measurement is memory-only with manual aggregate export. Never export
requests, commands, output, paths, content hashes or persistent session IDs.
V2/v3 remain regression suites; v4 is deferred until production stabilization and
deliberate sanitized contributions from real dogfood experience.

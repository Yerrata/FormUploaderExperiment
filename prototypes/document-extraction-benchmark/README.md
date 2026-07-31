# PROTOTYPE — document extraction benchmark

## Question

Can the Azure hybrid or Regula hybrid meet Yeratta Resort's safety rule—zero accepted incorrect Critical Fields—while automatically accepting at least 90% of Supported Cases at an acceptable latency and cost?

This is throwaway decision code. It scores normalized candidate outputs; it does not upload documents, call production services, or become the production extraction pipeline.

## Data safety

- Keep passport images, visa images, ground truth, and candidate predictions under `local-benchmark-data/` at the repository root.
- That directory is ignored by Git. Never commit identity data, API keys, session tokens, or raw vendor responses containing identity data.
- Run the benchmark on a resort-controlled computer.
- Create ground truth by manual transcription and independent second-person verification.
- Use only documents that Yeratta may lawfully use for this evaluation.

## One command

```bash
python prototypes/document-extraction-benchmark/prototype_cli.py \
  --truth local-benchmark-data/ground_truth.jsonl \
  --candidate azure=local-benchmark-data/azure.jsonl \
  --candidate regula=local-benchmark-data/regula.jsonl
```

The terminal shows one stable scorecard. Press `n` for the next candidate, `r` to reload changed files, and `q` to quit.

## File shapes

Each ground-truth line contains a case identifier, the exact Critical Fields required for that case, and whether a valid MRZ is expected:

```json
{"case_id":"case-001","critical_fields":{"passport_number":"P1234567","date_of_birth":"1990-01-02","passport_expiry":"2030-01-01","visa_number":"V98765"},"mrz_expected":true}
```

Each candidate line contains the same case identifier, the candidate decision, extracted Critical Fields, MRZ result, latency, and incremental cost:

```json
{"case_id":"case-001","decision":"accept","critical_fields":{"passport_number":"P1234567","date_of_birth":"1990-01-02","passport_expiry":"2030-01-01","visa_number":"V98765"},"mrz_valid":true,"latency_ms":1850,"cost_inr":2.5}
```

Allowed decisions are:

- `accept`: submit without guest correction;
- `correct`: ask the guest for a clearer image or explicit correction;
- `block`: unsupported or unresolved case.

Missing candidate cases are treated as blocked. Provider confidence is intentionally not an acceptance rule.

## Decision rule

A candidate passes this prototype only when:

- no accepted case has an incorrect or missing Critical Field;
- no accepted MRZ case lacks a valid MRZ result; and
- at least 90% of all benchmark cases are accepted with every Critical Field correct.

Twenty representative pairs are enough for a pilot that rejects obviously weak approaches. They are not enough to certify production safety. Before unattended release, rerun a locked, stratified set of at least 300 passport-and-visa pairs as specified in the extraction research.


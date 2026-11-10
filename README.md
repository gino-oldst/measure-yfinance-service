# yfinance Lambda

Single-day OHLCV fetcher backed by [yfinance](https://pypi.org/project/yfinance/), deployed to AWS Lambda as a container image via Serverless Framework.

## Files

| File | Purpose |
|---|---|
| `handler.py` | Lambda entrypoint. Self-contained — accepts API Gateway POST or direct invoke. |
| `requirements.txt` | Python deps (pinned for Lambda Python 3.11 compatibility). |
| `Dockerfile` | Container image based on AWS's Python 3.11 Lambda base. |
| `serverless.yml` | Serverless Framework config (region, profile, function, HTTP API route). |
| `.dockerignore` | Excludes venv/caches/old Django file from the image. |
| `existing.py` | Original Django REST Framework version (kept for reference, not deployed). |

## API

`POST https://<api-id>.execute-api.us-east-1.amazonaws.com/fetch`

Request body:
```json
{ "date": "YYYY-MM-DD", "tickers": ["AAPL", "MSFT"] }
```
or
```json
{ "date": "YYYY-MM-DD", "isins": ["US0378331005"] }
```

Response (200):
```json
{
  "AAPL": {
    "open": 187.15, "high": 188.44, "low": 183.89,
    "close": 185.64, "adj_close": 183.73, "volume": 82488700.0
  }
}
```

Empty `{}` is returned for a symbol when:
- yfinance returns no rows (non-trading day, unknown ticker)
- any OHLCV field is NaN/missing
- ISIN can't be resolved to a symbol

## Prerequisites

- macOS / Linux
- Docker Desktop (running)
- Node.js + npm (for Serverless CLI)
- AWS CLI configured with profile `oldst-main`
- Serverless Framework v4: `npm install -g serverless`

## Deploy

```bash
BUILDX_NO_DEFAULT_ATTESTATIONS=1 serverless deploy
```

The env var is **required** on macOS — see Gotchas below. Set it permanently:
```bash
echo 'export BUILDX_NO_DEFAULT_ATTESTATIONS=1' >> ~/.zshrc
```

## Test

```bash
# By ticker
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/fetch \
  -H "Content-Type: application/json" \
  -d '{"date":"2024-01-02","tickers":["AAPL","MSFT"]}'

# By ISIN
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/fetch \
  -H "Content-Type: application/json" \
  -d '{"date":"2024-01-02","isins":["US0378331005"]}'
```

## Logs

```bash
serverless logs -f fetch -t
# or
aws logs tail /aws/lambda/yfinance-api-dev-fetch --follow --profile oldst-main --region us-east-1
```

## Teardown

```bash
BUILDX_NO_DEFAULT_ATTESTATIONS=1 serverless remove
```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Quick local invoke
python -c "import json; from handler import lambda_handler; \
  print(lambda_handler({'date':'2024-01-02','tickers':['AAPL']}, None))"
```

## Gotchas (lessons learned during initial deploy)

1. **Apple Silicon platform mismatch.** Without `--platform=linux/amd64` in the Dockerfile, Docker builds an arm64 image. Lambda defaults to x86_64, and pip can't find arm64 wheels for numpy/pandas inside the build → falls back to source compile → fails (no `gcc` in the base image).

2. **numpy/pandas wheel availability.** The latest numpy/pandas releases sometimes don't have cp311 manylinux wheels yet. Pinned to `numpy<2.3`, `pandas<2.3` in `requirements.txt` to guarantee a wheel exists.

3. **pip in the base image is old.** `public.ecr.aws/lambda/python:3.11` ships pip 24.0; modern wheels need newer pip. The Dockerfile upgrades pip before installing requirements.

4. **OCI attestations break Lambda.** Modern Docker Desktop adds attestation manifests to images by default. Lambda rejects them with:
   > The image manifest, config or layer media type for the source image ... is not supported.

   Set `BUILDX_NO_DEFAULT_ATTESTATIONS=1` before any `serverless deploy` (or `docker buildx`) to disable.

5. **yfinance MultiIndex columns.** Newer yfinance returns a MultiIndex on `download()` for single tickers. Handler defensively flattens with `data.columns.droplevel(1)`.

6. **`auto_adjust` default flipped.** yfinance ≥0.2.51 defaults `auto_adjust=True`, dropping `Adj Close`. Handler explicitly sets `auto_adjust=False` to keep the field present and match the original Django service's response shape.

7. **Lambda IPs occasionally rate-limited by Yahoo.** Not seen yet, but expected at higher volume. Mitigations: caching layer (DynamoDB/S3), retry with backoff, or move off yfinance to a paid data provider.

## Configuration knobs

In `serverless.yml`:
- `provider.region` — currently `us-east-1`
- `provider.profile` — currently `oldst-main`
- `provider.timeout` — 30s (API Gateway HTTP API hard cap)
- `provider.memorySize` — 1024 MB (more memory = more CPU = faster cold starts)

## Cost notes

- ECR storage: ~$0.10/GB/month per stored image (image is ~250 MB).
- Lambda: pay per invocation + GB-second. With 1024 MB and ~2s execution, each call is well under $0.0001.
- API Gateway HTTP API: $1.00 per million requests.
- No NAT Gateway (Lambda is not in a VPC).

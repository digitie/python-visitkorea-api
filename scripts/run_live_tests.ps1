$envFile = Join-Path (Get-Location) ".env.local"

if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*DATA_GO_KR_SERVICE_KEY\s*=\s*(.+?)\s*$') {
      $env:DATA_GO_KR_SERVICE_KEY = $Matches[1].Trim('"').Trim("'")
    }
  }
}

if (-not $env:DATA_GO_KR_SERVICE_KEY) {
  throw "DATA_GO_KR_SERVICE_KEY is not set. Create .env.local with DATA_GO_KR_SERVICE_KEY=..."
}

python -m pytest -m live tests/test_live.py @args

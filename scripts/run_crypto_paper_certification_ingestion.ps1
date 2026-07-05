param(
    [string]$CertificationResultPath = "runs\crypto_paper_submit_cancel_certification\latest\certification_result.json",
    [string]$OutputRoot = "runs\crypto_paper_certification_ingestion\latest",
    [string]$ApprovedQty = "0.000396783",
    [string]$MaxNotional = "25",
    [string]$AsOfTimestamp = "",
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

$ErrorActionPreference = "Stop"

Write-Host "crypto_paper_certification_ingestion_command=run_crypto_paper_certification_ingestion"
Write-Host "crypto_paper_certification_ingestion_scope=local_v5_8_result_ingestion_only"
Write-Host "crypto_paper_certification_ingestion_broker_read_performed=false"
Write-Host "crypto_paper_certification_ingestion_broker_mutation_performed=false"
Write-Host "crypto_paper_certification_ingestion_paper_submit_performed=false"
Write-Host "crypto_paper_certification_ingestion_live_endpoint_touched=false"
Write-Host "crypto_paper_certification_ingestion_credential_values_exposed=false"

$PythonArgs = @(
    "-m",
    "algotrader.orchestration.crypto_paper_certification_ingestion",
    "--certification-result-path",
    $CertificationResultPath,
    "--output-root",
    $OutputRoot,
    "--approved-qty",
    $ApprovedQty,
    "--max-notional",
    $MaxNotional,
    "--format",
    $Format
)

if ($AsOfTimestamp.Trim().Length -gt 0) {
    $PythonArgs += @("--as-of", $AsOfTimestamp)
}

python @PythonArgs
exit $LASTEXITCODE

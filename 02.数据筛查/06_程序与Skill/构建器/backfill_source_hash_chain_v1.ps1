param(
  [string]$SystemRoot = "E:\个人事件量化系统",
  [string]$BaselineArchive = "E:\个人事件量化系统\02.数据筛查\99_系统演化档案\2026-08-24_来源哈希链v1.0更新前.zip",
  [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$ContractVersion = 'source-hash-chain-v1.0'
$EnrichedAt = '2026-08-24'

function Get-Field {
  param($Object, [string]$Name, $Default = $null)
  if ($null -eq $Object) { return $Default }
  $property = $Object.PSObject.Properties[$Name]
  if (($null -eq $property) -or ($null -eq $property.Value)) { return $Default }
  return $property.Value
}

function Set-Field {
  param($Object, [string]$Name, $Value)
  $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value -Force
}

function Get-Sha256 {
  param([string]$Path)
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$reportDirectory = Join-Path $SystemRoot '02.数据筛查\03_最终日报'
$rawDirectory = Join-Path $SystemRoot '01.原始数据记录\03_事件数据\提交模块\日提交'
$analysisDirectory = Join-Path $SystemRoot '01.原始数据记录\03_事件数据\分析模块\日分析'
$reports = @(Get-ChildItem -LiteralPath $reportDirectory -File -Filter '*最终数据报告.json' | Sort-Object Name)
$changed = 0
$knownExecutionVersion = 0
$legacyExecutionVersion = 0
$statusCounts = @{}
$baselineByDate = @{}
if (Test-Path -LiteralPath $BaselineArchive -PathType Leaf) {
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $zip = [IO.Compression.ZipFile]::OpenRead($BaselineArchive)
  try {
    $entry = $zip.GetEntry('05_质量审计/ingestion_registry.jsonl')
    if ($null -ne $entry) {
      $reader = [IO.StreamReader]::new($entry.Open())
      try {
        foreach ($line in ($reader.ReadToEnd() -split "`r?`n" | Where-Object { $_.Trim() })) {
          $row = $line | ConvertFrom-Json
          $baselineByDate[[string]$row.event_date] = $row
        }
      } finally {
        $reader.Dispose()
      }
    }
  } finally {
    $zip.Dispose()
  }
}

foreach ($file in $reports) {
  $report = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
  $eventDate = [datetime]::ParseExact([string]$report.event_date, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
  $rawName = '日期：{0}年{1}月{2}日.md' -f $eventDate.Year, $eventDate.Month, $eventDate.Day
  $analysisName = '{0}年{1}月{2}日.md' -f $eventDate.Year, $eventDate.Month, $eventDate.Day
  $rawPath = Join-Path $rawDirectory $rawName
  $analysisPath = Join-Path $analysisDirectory $analysisName
  if (-not (Test-Path -LiteralPath $rawPath -PathType Leaf)) { throw "Missing raw submission for $($report.event_date): $rawPath" }
  if (-not (Test-Path -LiteralPath $analysisPath -PathType Leaf)) { throw "Missing analysis report for $($report.event_date): $analysisPath" }

  $rawCurrentHash = Get-Sha256 $rawPath
  $analysisCurrentHash = Get-Sha256 $analysisPath
  $baseline = $baselineByDate[[string]$report.event_date]
  if ($null -ne $baseline) {
    $rawHash = [string](Get-Field $baseline 'last_built_source_sha256' $rawCurrentHash)
    $analysisHash = [string](Get-Field $baseline 'last_built_analysis_sha256' $analysisCurrentHash)
    $rawHashBasis = 'last_built_ingestion_registry'
    $analysisHashBasis = 'last_built_ingestion_registry'
    $sourceChainStatus = if (($rawHash -eq $rawCurrentHash) -and ($analysisHash -eq $analysisCurrentHash)) { 'verified_current' } else { 'source_changed' }
    $lastScreenedFinalReportSha256 = Get-Field $baseline 'last_built_final_report_sha256' $null
    $lastScreenedBuildBatchId = Get-Field $baseline 'build_batch_id' $null
    $lastScreenedBuilderVersion = Get-Field $baseline 'builder_version' $null
  } else {
    $rawHash = $rawCurrentHash
    $analysisHash = $analysisCurrentHash
    $rawHashBasis = 'current_file_backfill_unverified'
    $analysisHashBasis = 'current_file_backfill_unverified'
    $sourceChainStatus = 'historical_unverified'
    $lastScreenedFinalReportSha256 = $null
    $lastScreenedBuildBatchId = $null
    $lastScreenedBuilderVersion = $null
  }
  if (-not $statusCounts.ContainsKey($sourceChainStatus)) { $statusCounts[$sourceChainStatus] = 0 }
  $statusCounts[$sourceChainStatus]++
  $provenance = Get-Field $report 'provenance' $null
  if ($null -eq $provenance) {
    $provenance = [pscustomobject]@{}
    Set-Field $report 'provenance' $provenance
  }

  $existingRawHash = [string](Get-Field $provenance 'raw_source_sha256' '')
  $existingAnalysisHash = [string](Get-Field $provenance 'analysis_source_sha256' '')
  if ((-not [string]::IsNullOrWhiteSpace($existingRawHash)) -and ($existingRawHash.ToLowerInvariant() -notin @($rawHash, $rawCurrentHash))) {
    throw "Existing raw_source_sha256 conflicts with current formal source: $($file.FullName)"
  }
  if ((-not [string]::IsNullOrWhiteSpace($existingAnalysisHash)) -and ($existingAnalysisHash.ToLowerInvariant() -notin @($analysisHash, $analysisCurrentHash))) {
    throw "Existing analysis_source_sha256 conflicts with current formal source: $($file.FullName)"
  }

  $executionVersion = [string](Get-Field $provenance 'execution_version' '')
  if ([string]::IsNullOrWhiteSpace($executionVersion)) {
    $workflow = [string](Get-Field $provenance 'workflow' '')
    if ([string]::IsNullOrWhiteSpace($workflow)) { $workflow = 'legacy-workflow-unknown' }
    $executionVersion = "$workflow@legacy-version-unknown"
    $legacyExecutionVersion++
  } else {
    $knownExecutionVersion++
  }

  $rawRelative = '01.原始数据记录/03_事件数据/提交模块/日提交/' + $rawName
  $analysisRelative = '01.原始数据记录/03_事件数据/分析模块/日分析/' + $analysisName
  Set-Field $provenance 'raw_source_file' $rawRelative
  Set-Field $provenance 'raw_source_sha256' $rawHash
  Set-Field $provenance 'raw_current_sha256' $rawCurrentHash
  Set-Field $provenance 'raw_source_hash_basis' $rawHashBasis
  Set-Field $provenance 'analysis_source_file' $analysisRelative
  Set-Field $provenance 'analysis_source_sha256' $analysisHash
  Set-Field $provenance 'analysis_current_sha256' $analysisCurrentHash
  Set-Field $provenance 'analysis_source_hash_basis' $analysisHashBasis
  Set-Field $provenance 'execution_version' $executionVersion
  Set-Field $provenance 'provenance_contract' $ContractVersion
  Set-Field $provenance 'provenance_enriched_at' $EnrichedAt
  Set-Field $provenance 'source_chain_status' $sourceChainStatus
  Set-Field $provenance 'last_screened_final_report_sha256' $lastScreenedFinalReportSha256
  Set-Field $provenance 'last_screened_build_batch_id' $lastScreenedBuildBatchId
  Set-Field $provenance 'last_screened_builder_version' $lastScreenedBuilderVersion

  $newText = $report | ConvertTo-Json -Depth 100
  $oldText = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
  if (($oldText.TrimEnd() -cne $newText.TrimEnd())) {
    $changed++
    if ($Apply) {
      $temporaryPath = "$($file.FullName).source-chain.tmp"
      if (Test-Path -LiteralPath $temporaryPath -PathType Leaf) {
        Remove-Item -LiteralPath $temporaryPath -Force
      }
      [IO.File]::WriteAllText($file.FullName, $newText + [Environment]::NewLine, $Utf8NoBom)
    }
  }
}

[pscustomobject]@{
  contract_version = $ContractVersion
  report_count = $reports.Count
  changed_count = $changed
  exact_execution_version_preserved = $knownExecutionVersion
  legacy_execution_version_marked_unknown = $legacyExecutionVersion
  source_chain_status_counts = $statusCounts
  apply = [bool]$Apply
} | ConvertTo-Json

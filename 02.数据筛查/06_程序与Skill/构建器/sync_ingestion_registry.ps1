param(
  [string]$SystemRoot = "E:\个人事件量化系统",
  [datetime]$StartDate = [datetime]'2026-08-17',
  [string]$RegistryPath = "E:\个人事件量化系统\02.数据筛查\05_质量审计\ingestion_registry.jsonl"
)

$ErrorActionPreference = 'Stop'
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$SchemaVersion = 'ingestion-registry-v1.0'

function Get-Field {
  param($Object, [string]$Name, $Default = $null)
  if ($null -eq $Object) { return $Default }
  $property = $Object.PSObject.Properties[$Name]
  if (($null -eq $property) -or ($null -eq $property.Value)) { return $Default }
  return $property.Value
}

function Move-ReplaceFile {
  param([string]$TemporaryPath, [string]$DestinationPath)
  if (Test-Path -LiteralPath $DestinationPath -PathType Leaf) {
    $temporaryHash = (Get-FileHash -LiteralPath $TemporaryPath -Algorithm SHA256).Hash
    $destinationHash = (Get-FileHash -LiteralPath $DestinationPath -Algorithm SHA256).Hash
    if ($temporaryHash -eq $destinationHash) {
      Remove-Item -LiteralPath $TemporaryPath -Force
      return
    }
    $replacementBackup = "$DestinationPath.replace-$([guid]::NewGuid().ToString('N')).bak"
    Move-Item -LiteralPath $DestinationPath -Destination $replacementBackup
    try {
      Move-Item -LiteralPath $TemporaryPath -Destination $DestinationPath
      Remove-Item -LiteralPath $replacementBackup -Force
    } catch {
      if ((-not (Test-Path -LiteralPath $DestinationPath)) -and (Test-Path -LiteralPath $replacementBackup)) {
        Move-Item -LiteralPath $replacementBackup -Destination $DestinationPath
      }
      throw
    }
  } else {
    Move-Item -LiteralPath $TemporaryPath -Destination $DestinationPath
  }
}

function Get-RelativeVaultPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  $root = [System.IO.Path]::GetFullPath($SystemRoot).TrimEnd('\')
  $full = [System.IO.Path]::GetFullPath($Path)
  if (-not $full.StartsWith($root + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Path is outside SystemRoot: $full"
  }
  return $full.Substring($root.Length + 1).Replace('\', '/')
}

function Get-FileSha256 {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Convert-ToIsoTimestamp {
  param($Value, [string]$Fallback)
  if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) { return $Fallback }
  if ($Value -is [datetimeoffset]) { return $Value.ToString('o') }
  if ($Value -is [datetime]) { return ([datetimeoffset]$Value).ToString('o') }
  try { return ([datetimeoffset]::Parse([string]$Value)).ToString('o') } catch { return [string]$Value }
}

function Get-LegacyBuildBatchId {
  param($Manifest)
  $generatedAt = [datetimeoffset]::Parse([string](Get-Field $Manifest 'generated_at'))
  $stamp = $generatedAt.ToString('yyyyMMddTHHmmsszzz').Replace(':', '')
  return "BUILD-$stamp-$([string](Get-Field $Manifest 'script_version' 'unknown'))"
}

function Test-EquivalentRecord {
  param($Old, $New)
  if ($null -eq $Old) { return $false }
  $fields = @(
    'schema_version', 'ingestion_id', 'event_date',
    'source_submission', 'source_sha256', 'analysis_report', 'analysis_sha256',
    'screening_workspace', 'processing_status', 'status_reason',
    'final_report', 'final_report_sha256', 'build_batch_id', 'builder_version',
    'last_built_source_sha256', 'last_built_analysis_sha256',
    'last_built_final_report_sha256', 'next_action'
  )
  foreach ($field in $fields) {
    $oldValue = Get-Field $Old $field $null
    $newValue = Get-Field $New $field $null
    if ([string]$oldValue -ne [string]$newValue) { return $false }
  }
  return $true
}

$submissionDirectory = Join-Path $SystemRoot '01.原始数据记录\03_事件数据\提交模块\日提交'
$analysisDirectory = Join-Path $SystemRoot '01.原始数据记录\03_事件数据\分析模块\日分析'
$workspaceDirectory = Join-Path $SystemRoot '02.数据筛查\02_筛选工作区'
$finalDirectory = Join-Path $SystemRoot '02.数据筛查\03_最终日报'
$manifestPath = Join-Path $SystemRoot '02.数据筛查\04_派生账本\manifest.json'

foreach ($requiredDirectory in @($submissionDirectory, $analysisDirectory, $workspaceDirectory, $finalDirectory)) {
  if (-not (Test-Path -LiteralPath $requiredDirectory -PathType Container)) {
    throw "Required directory does not exist: $requiredDirectory"
  }
}

$existingByDate = @{}
if (Test-Path -LiteralPath $RegistryPath -PathType Leaf) {
  Get-Content -LiteralPath $RegistryPath -Encoding UTF8 | Where-Object { $_.Trim().Length -gt 0 } | ForEach-Object {
    $record = $_ | ConvertFrom-Json
    $dateKey = [string](Get-Field $record 'event_date' '')
    if ($existingByDate.ContainsKey($dateKey)) { throw "Duplicate event_date in registry: $dateKey" }
    $existingByDate[$dateKey] = $record
  }
}

$manifest = $null
$manifestInputs = @{}
$buildBatchId = $null
$builderVersion = $null
if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
  $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $builderVersion = [string](Get-Field $manifest 'script_version' 'unknown')
  $buildBatchId = Get-Field $manifest 'build_batch_id' $null
  if ([string]::IsNullOrWhiteSpace([string]$buildBatchId)) { $buildBatchId = Get-LegacyBuildBatchId $manifest }
  foreach ($input in @(Get-Field $manifest 'inputs' @())) {
    $manifestInputs[[string](Get-Field $input 'source_report' '')] = $input
  }
}

$sourceGroups = @{}
$namePattern = '^日期：(?<year>\d{4})年(?<month>\d{1,2})月(?<day>\d{1,2})日\.md$'
Get-ChildItem -LiteralPath $submissionDirectory -File | ForEach-Object {
  if ($_.Name -match $namePattern) {
    $eventDate = [datetime]::new([int]$Matches.year, [int]$Matches.month, [int]$Matches.day)
    if ($eventDate.Date -ge $StartDate.Date) {
      $dateKey = $eventDate.ToString('yyyy-MM-dd')
      if (-not $sourceGroups.ContainsKey($dateKey)) { $sourceGroups[$dateKey] = [System.Collections.Generic.List[object]]::new() }
      $sourceGroups[$dateKey].Add($_)
    }
  }
}

$now = [datetimeoffset]::Now.ToString('o')
$records = [System.Collections.Generic.List[object]]::new()

foreach ($dateKey in @($sourceGroups.Keys | Sort-Object)) {
  $sources = @($sourceGroups[$dateKey])
  $old = $existingByDate[$dateKey]
  $date = [datetime]::ParseExact($dateKey, 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
  $source = $sources | Select-Object -First 1
  $analysisPath = Join-Path $analysisDirectory ("{0}年{1}月{2}日.md" -f $date.Year, $date.Month, $date.Day)
  $workspacePath = Join-Path $workspaceDirectory ("{0}-{1}.{2}" -f $date.Year, $date.Month, $date.Day)
  $finalPath = Join-Path $finalDirectory ("${dateKey}最终数据报告.json")
  $sourceHash = Get-FileSha256 $source.FullName
  $analysisHash = Get-FileSha256 $analysisPath
  $finalHash = Get-FileSha256 $finalPath
  $finalRelative = if ($null -ne $finalHash) { "03_最终日报/${dateKey}最终数据报告.json" } else { $null }
  $manifestInput = if ($manifestInputs.ContainsKey([string]$finalRelative)) { $manifestInputs[[string]$finalRelative] } else { $null }
  $manifestFinalHash = [string](Get-Field $manifestInput 'final_report_sha256' (Get-Field $manifestInput 'sha256' ''))
  $manifestRawHash = [string](Get-Field $manifestInput 'raw_source_sha256' '')
  $manifestAnalysisHash = [string](Get-Field $manifestInput 'analysis_source_sha256' '')
  $manifestChainStatus = [string](Get-Field $manifestInput 'source_chain_status' '')
  $manifestLastScreenedFinal = Get-Field $manifestInput 'last_screened_final_report_sha256' $null
  $manifestLastScreenedBatch = Get-Field $manifestInput 'last_screened_build_batch_id' $null
  $manifestLastScreenedBuilder = Get-Field $manifestInput 'last_screened_builder_version' $null
  $manifestFinalMatches = ($null -ne $finalHash) -and ($null -ne $manifestInput) -and ($manifestFinalHash -eq $finalHash)
  $manifestRawMatches = ($null -ne $sourceHash) -and ($manifestRawHash -eq $sourceHash)
  $manifestAnalysisMatches = ($null -ne $analysisHash) -and ($manifestAnalysisHash -eq $analysisHash)
  $manifestMatches = $manifestFinalMatches -and $manifestRawMatches -and $manifestAnalysisMatches
  $oldBuiltSource = Get-Field $old 'last_built_source_sha256' $null
  $oldBuiltAnalysis = Get-Field $old 'last_built_analysis_sha256' $null
  $oldBuiltFinal = Get-Field $old 'last_built_final_report_sha256' $null
  $upstreamChanged = (($null -ne $oldBuiltSource) -and ($oldBuiltSource -ne $sourceHash)) -or (($null -ne $oldBuiltAnalysis) -and ($oldBuiltAnalysis -ne $analysisHash))
  $finalRebuilt = $manifestMatches -and ($null -ne $oldBuiltFinal) -and ($oldBuiltFinal -ne $finalHash)

  $status = $null
  $reason = $null
  $nextAction = $null
  $recordBuildBatchId = Get-Field $old 'build_batch_id' $null
  $recordBuilderVersion = Get-Field $old 'builder_version' $null
  $lastBuiltSource = $oldBuiltSource
  $lastBuiltAnalysis = $oldBuiltAnalysis
  $lastBuiltFinal = $oldBuiltFinal

  if ($sources.Count -gt 1) {
    $status = 'blocked_duplicate_source'
    $reason = "同一事件日期发现 $($sources.Count) 个正式提交文件。"
    $nextAction = '人工确认唯一源文件后重新同步。'
  } elseif ($null -eq $analysisHash) {
    $status = 'waiting_for_analysis'
    $reason = '已发现原始提交，但尚无同日AI分析。'
    $nextAction = '完成第一子系统日分析后重新同步。'
  } elseif ($manifestFinalMatches -and ($manifestChainStatus -eq 'source_changed')) {
    $status = 'source_changed'
    $reason = '更新前成功构建基线与当前01日分析哈希不同；来源链迁移未重新批准筛选结论。'
    $nextAction = '重新执行筛选并生成新的最终日报，然后重建派生账本。'
    $recordBuildBatchId = $manifestLastScreenedBatch
    $recordBuilderVersion = $manifestLastScreenedBuilder
    $lastBuiltSource = $manifestRawHash
    $lastBuiltAnalysis = $manifestAnalysisHash
    $lastBuiltFinal = $manifestLastScreenedFinal
  } elseif ($upstreamChanged -and -not $finalRebuilt) {
    $status = 'source_changed'
    $reason = '已构建记录的原始提交或日分析哈希发生变化，现有最终报告不可静默复用。'
    $nextAction = '重新执行筛选、生成新的最终报告并重建派生账本。'
  } elseif ($null -eq $finalHash) {
    if (Test-Path -LiteralPath $workspacePath -PathType Container) {
      $status = 'screening_in_progress'
      $reason = '筛选工作区已建立，但尚未生成最终日报。'
      $nextAction = '完成质检与事实闭环，生成最终日报。'
    } else {
      $status = 'ready_for_screening'
      $reason = '原始提交和日分析齐全，尚未建立筛选工作区。'
      $nextAction = '按日期顺序进入第二流程并建立筛选工作区。'
    }
  } elseif ($manifestMatches) {
    $status = 'built'
    $reason = '最终日报哈希已进入当前派生账本构建批次。'
    $nextAction = '无；等待上游变化或后续质量复核。'
    $recordBuildBatchId = $buildBatchId
    $recordBuilderVersion = $builderVersion
    $lastBuiltSource = $sourceHash
    $lastBuiltAnalysis = $analysisHash
    $lastBuiltFinal = $finalHash
  } elseif ($manifestFinalMatches -and ((-not $manifestRawMatches) -or (-not $manifestAnalysisMatches))) {
    $status = 'source_chain_mismatch'
    $reason = '最终日报哈希存在于manifest，但原始提交或分析来源哈希链不一致。'
    $nextAction = '停止复用；核对最终日报provenance并重新筛选或重建。'
  } else {
    $status = 'finalized_pending_build'
    $reason = '最终日报已存在，但尚未进入当前manifest或其哈希不一致。'
    $nextAction = '运行派生账本构建器并再次同步登记。'
  }

  $candidate = [pscustomobject][ordered]@{
    schema_version = $SchemaVersion
    ingestion_id = "ING-$($date.ToString('yyyyMMdd'))"
    event_date = $dateKey
    source_submission = Get-RelativeVaultPath $source.FullName
    source_sha256 = $sourceHash
    analysis_report = if ($null -ne $analysisHash) { Get-RelativeVaultPath $analysisPath } else { $null }
    analysis_sha256 = $analysisHash
    screening_workspace = if (Test-Path -LiteralPath $workspacePath -PathType Container) { Get-RelativeVaultPath $workspacePath } else { $null }
    processing_status = $status
    status_reason = $reason
    final_report = if ($null -ne $finalHash) { Get-RelativeVaultPath $finalPath } else { $null }
    final_report_sha256 = $finalHash
    build_batch_id = $recordBuildBatchId
    builder_version = $recordBuilderVersion
    last_built_source_sha256 = $lastBuiltSource
    last_built_analysis_sha256 = $lastBuiltAnalysis
    last_built_final_report_sha256 = $lastBuiltFinal
    registered_at = Convert-ToIsoTimestamp (Get-Field $old 'registered_at' $null) $now
    updated_at = $now
    next_action = $nextAction
  }
  if (Test-EquivalentRecord $old $candidate) { $candidate.updated_at = Convert-ToIsoTimestamp (Get-Field $old 'updated_at' $null) $now }
  $records.Add($candidate)
}

$registryDirectory = Split-Path -Parent $RegistryPath
New-Item -ItemType Directory -Force -Path $registryDirectory | Out-Null
$temporaryPath = "$RegistryPath.tmp"
$lines = @($records | ForEach-Object { $_ | ConvertTo-Json -Depth 10 -Compress })
[System.IO.File]::WriteAllText($temporaryPath, (($lines -join [Environment]::NewLine) + $(if ($lines.Count -gt 0) { [Environment]::NewLine } else { '' })), $Utf8NoBom)
Move-ReplaceFile $temporaryPath $RegistryPath

$counts = [ordered]@{}
$records | Group-Object processing_status | Sort-Object Name | ForEach-Object { $counts[$_.Name] = $_.Count }
[pscustomobject]@{
  registry = Get-RelativeVaultPath $RegistryPath
  start_date = $StartDate.ToString('yyyy-MM-dd')
  record_count = $records.Count
  status_counts = [pscustomobject]$counts
} | ConvertTo-Json -Depth 5 -Compress

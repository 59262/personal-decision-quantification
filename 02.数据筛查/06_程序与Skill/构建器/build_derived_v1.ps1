param(
  [string]$SourceDirectory = "E:\个人事件量化系统\02.数据筛查\03_最终日报",
  [string]$OutputDirectory = "E:\个人事件量化系统\02.数据筛查\04_派生账本",
  [string]$QualityDirectory = "E:\个人事件量化系统\02.数据筛查\05_质量审计"
)

$ErrorActionPreference = 'Stop'
$ScriptVersion = 'derived-v1.6.0'
$SourceChainContract = 'source-hash-chain-v1.0'
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$BuildGeneratedAt = [datetimeoffset]::Now
$BuildBatchId = 'BUILD-{0}-{1}' -f $BuildGeneratedAt.ToString('yyyyMMddTHHmmsszzz').Replace(':', ''), $ScriptVersion

function Get-Field {
  param($Object, [string]$Name, $Default = $null)
  if ($null -eq $Object) { return $Default }
  $property = $Object.PSObject.Properties[$Name]
  if ($null -eq $property) { return $Default }
  if ($null -eq $property.Value) { return $Default }
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
    if ([System.IO.Path]::GetExtension($DestinationPath) -eq '.json') {
      try {
        $temporaryJson = Get-Content -LiteralPath $TemporaryPath -Raw -Encoding UTF8 | ConvertFrom-Json | ConvertTo-Json -Depth 30 -Compress
        $destinationJson = Get-Content -LiteralPath $DestinationPath -Raw -Encoding UTF8 | ConvertFrom-Json | ConvertTo-Json -Depth 30 -Compress
        if ($temporaryJson -eq $destinationJson) {
          Remove-Item -LiteralPath $TemporaryPath -Force
          return
        }
      } catch {
        # Fall through to physical replacement when either file is not valid JSON.
      }
    }
    if ([System.IO.Path]::GetExtension($DestinationPath) -eq '.jsonl') {
      $temporaryLines = @(Get-Content -LiteralPath $TemporaryPath -Encoding UTF8)
      $destinationLines = @(Get-Content -LiteralPath $DestinationPath -Encoding UTF8)
      if (($temporaryLines -join "`n") -ceq ($destinationLines -join "`n")) {
        Remove-Item -LiteralPath $TemporaryPath -Force
        return
      }
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

function Get-ChoiceLabel {
  param($Choice)
  if ($null -eq $Choice) { return $null }
  if ($Choice -is [string]) { return $Choice }
  return Get-Field $Choice 'label' $null
}

function Get-DecisionFamily {
  param([string]$Domain, [string]$Question, [string]$Target, [object[]]$Options)
  # This is an action-choice family, not a life-domain category.
  $optionText = (($Options | ForEach-Object { Get-ChoiceLabel $_ }) -join ' ')
  $text = "$Domain $Question $Target $optionText".ToLowerInvariant()
  if ($text -match '争吵|批评|沟通|谈话|劝|冲突|面对|回避|confront|avoid') { return 'confront_vs_avoid' }
  if ($text -match '何时|时间|等待|雨停|先.*后|later|when|wait|timing') { return 'timing_choice' }
  if ($text -match 'diet|food|(?<![a-z])eat(?![a-z])|饮食|吃|餐|减脂|放纵|自助') { return 'consume_vs_abstain' }
  if ($text -match '开始|启动|填写|着手|延期|推迟|明天|start|defer') { return 'start_vs_defer' }
  if ($text -match '继续|停止|结束|下班|休息|中止|continue|stop') { return 'continue_vs_stop' }
  return 'plan_a_vs_plan_b'
}

function Get-CanonicalTaskStatus {
  param([string]$Status)
  $s = $Status.ToLowerInvariant()
  if ($s -in @('completed', 'marked_completed', 'completed_content_unspecified', 'marked_done_content_unspecified', 'performed_as_planned_task', 'reported_completed', 'reported_completed_details_unknown', 'completed_publication_unknown', 'completed_observable_scope', 'completed_content_present_timing_unknown')) { return 'completed' }
  if ($s -in @('partially_completed', 'partially_completed_rescheduled', 'worked_on', 'started', 'advanced_to_testing_stage', 'partially_done', 'completed_to_near_completion')) { return 'partial' }
  if ($s -in @('not_done', 'not_started', 'not_executed', 'not_completed', 'planned_not_started', 'planned_not_executed', 'attempted_not_completed_due_to_rain', 'not_done_due_to_rain', 'externally_blocked', 'reported_not_done_scope_uncertain')) { return 'not_completed' }
  if ($s -eq 'intentionally_deferred') { return 'deferred' }
  return 'execution_or_completion_unknown'
}

function Get-FeatureFamily {
  param($Observation)
  $featureId = [string](Get-Field $Observation 'feature_id' '')
  $value = [string](Get-Field $Observation 'value' '')
  $sourceType = [string](Get-Field $Observation 'source_type' '')
  $text = "$featureId $value $sourceType".ToLowerInvariant()
  if ($text -match 'option|alternative|available|choice_set|可进行|可得|替代') { return 'option_availability' }
  if ($text -match 'physical|health|body|palpitation|酸痛|晕|身体|健康|心悸') { return 'physical_state' }
  if ($text -match 'weather|rain|天气|下雨') { return 'environmental_condition' }
  if ($text -match 'boss|employee|social|friend|family|老板|员工|朋友|家人') { return 'social_or_work_context' }
  if ($text -match 'rest.day|sleep|recovery|休息日|睡眠|入睡') { return 'recovery_or_schedule_context' }
  if ($text -match 'goal|plan|agreement|commitment|weekend|减肥|约定|计划|目标') { return 'goal_or_commitment' }
  if ($text -match 'prior|previous|usual|habit|平常|此前|之前|习惯') { return 'historical_pattern_or_habit' }
  if ($text -match 'morning|evening|workday|arrived|time|早晨|晚上|下班|到家|时间') { return 'time_or_location_context' }
  if ($text -match 'mood|emotion|engagement|excited|兴奋|情绪|状态') { return 'affective_or_cognitive_state' }
  if ($sourceType -match 'reason') { return 'user_stated_reason' }
  return 'other_observed_context'
}

function Get-FeatureFamilyConfidence {
  param($Observation, [string]$Family)
  $featureId = [string](Get-Field $Observation 'feature_id' '')
  if ([string]::IsNullOrWhiteSpace($featureId)) { return 'low' }
  if ($Family -eq 'other_observed_context') { return 'low' }
  return 'rule_based_medium'
}

function Get-TaskFamily {
  param([string]$Task)
  $text = $Task.ToLowerInvariant()
  if ($text -match 'diet|food|eat|饮食|吃|餐|减脂|放纵') { return 'diet' }
  if ($text -match 'exercise|fitness|workout|健身|有氧|力量|骑行') { return 'exercise' }
  if ($text -match 'sleep|rest|recovery|休息|睡眠|入睡') { return 'recovery' }
  if ($text -match 'video|creation|创作|视频|拍摄|剪辑') { return 'creation' }
  if ($text -match 'work|company|公司|下班|工作') { return 'work' }
  if ($text -match 'project|product|创业|模型|数据|项目|产品') { return 'project' }
  if ($text -match 'social|朋友|家人|聊天|关系') { return 'social' }
  return 'other'
}

function Add-Issue {
  param(
    [System.Collections.Generic.List[object]]$Issues,
    [string]$EventDate,
    [string]$RecordType,
    [string]$RecordId,
    [string]$IssueCode,
    [string]$Severity,
    [string]$Field,
    [string]$Description,
    [string]$SourceReport
  )
  $Issues.Add([pscustomobject]@{
    schema_version = 'quality-issue-v1.0'
    event_date = $EventDate
    record_type = $RecordType
    record_id = $RecordId
    issue_code = $IssueCode
    severity = $Severity
    field = $Field
    description = $Description
    source_report = $SourceReport
    remediation = 'human_review_required'
  })
}

function Write-Jsonl {
  param([string]$Path, [System.Collections.IEnumerable]$Rows)
  $temporaryPath = "$Path.tmp"
  [System.IO.File]::WriteAllText($temporaryPath, '', $Utf8NoBom)
  foreach ($row in $Rows) {
    $line = $row | ConvertTo-Json -Depth 30 -Compress
    [System.IO.File]::AppendAllText($temporaryPath, $line + [Environment]::NewLine, $Utf8NoBom)
  }
  Move-ReplaceFile $temporaryPath $Path
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $QualityDirectory | Out-Null
$reportFiles = @(Get-ChildItem -LiteralPath $SourceDirectory -File -Filter '*最终数据报告.json' | Sort-Object FullName)

$reports = [System.Collections.Generic.List[object]]::new()
$decisions = [System.Collections.Generic.List[object]]::new()
$coarseDecisions = [System.Collections.Generic.List[object]]::new()
$tasks = [System.Collections.Generic.List[object]]::new()
$issues = [System.Collections.Generic.List[object]]::new()
$manifestInputs = [System.Collections.Generic.List[object]]::new()
$sourceChainsByReport = @{}
$sourceChainStatusCounts = @{ verified_current = 0; source_changed = 0; historical_unverified = 0 }
$overridePath = Join-Path $QualityDirectory 'human_review_overrides.jsonl'
$reviewOverrides = @{}
if (Test-Path -LiteralPath $overridePath) {
  Get-Content -LiteralPath $overridePath -Encoding UTF8 | Where-Object { $_.Trim().Length -gt 0 } | ForEach-Object {
    $override = $_ | ConvertFrom-Json
    if ((Get-Field $override 'review_status' '') -eq 'resolved') {
      $key = '{0}|{1}|{2}' -f (Get-Field $override 'record_type' ''), (Get-Field $override 'record_id' ''), (Get-Field $override 'field' '')
      $reviewOverrides[$key] = $override
    }
  }
}

foreach ($file in $reportFiles) {
  $raw = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
  $report = $raw | ConvertFrom-Json
  $sourceRelative = "03_最终日报/$($file.Name)"
  $eventDate = [string](Get-Field $report 'event_date' 'unknown')
  $reportProvenance = Get-Field $report 'provenance' ([pscustomobject]@{})
  $rawSourceFile = [string](Get-Field $reportProvenance 'raw_source_file' '')
  $rawSourceSha256 = [string](Get-Field $reportProvenance 'raw_source_sha256' '')
  $rawCurrentSha256 = [string](Get-Field $reportProvenance 'raw_current_sha256' '')
  $rawSourceHashBasis = [string](Get-Field $reportProvenance 'raw_source_hash_basis' '')
  $analysisSourceFile = [string](Get-Field $reportProvenance 'analysis_source_file' '')
  $analysisSourceSha256 = [string](Get-Field $reportProvenance 'analysis_source_sha256' '')
  $analysisCurrentSha256 = [string](Get-Field $reportProvenance 'analysis_current_sha256' '')
  $analysisSourceHashBasis = [string](Get-Field $reportProvenance 'analysis_source_hash_basis' '')
  $executionVersion = [string](Get-Field $reportProvenance 'execution_version' '')
  $provenanceContract = [string](Get-Field $reportProvenance 'provenance_contract' '')
  $sourceChainStatus = [string](Get-Field $reportProvenance 'source_chain_status' '')
  $lastScreenedFinalReportSha256 = Get-Field $reportProvenance 'last_screened_final_report_sha256' $null
  $lastScreenedBuildBatchId = Get-Field $reportProvenance 'last_screened_build_batch_id' $null
  $lastScreenedBuilderVersion = Get-Field $reportProvenance 'last_screened_builder_version' $null
  $sourceReportSha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  foreach ($hashField in @(
    [pscustomobject]@{ Name = 'raw_source_sha256'; Value = $rawSourceSha256 },
    [pscustomobject]@{ Name = 'raw_current_sha256'; Value = $rawCurrentSha256 },
    [pscustomobject]@{ Name = 'analysis_source_sha256'; Value = $analysisSourceSha256 },
    [pscustomobject]@{ Name = 'analysis_current_sha256'; Value = $analysisCurrentSha256 }
  )) {
    if ($hashField.Value -notmatch '^[0-9a-f]{64}$') {
      throw "$sourceRelative has invalid or missing $($hashField.Name)."
    }
  }
  if ([string]::IsNullOrWhiteSpace($rawSourceFile) -or [string]::IsNullOrWhiteSpace($analysisSourceFile)) {
    throw "$sourceRelative has an incomplete source-file chain."
  }
  if ([string]::IsNullOrWhiteSpace($executionVersion)) {
    throw "$sourceRelative has no execution_version."
  }
  if ($provenanceContract -ne $SourceChainContract) {
    throw "$sourceRelative has unsupported provenance_contract: $provenanceContract"
  }
  if ($sourceChainStatus -notin @('verified_current', 'source_changed', 'historical_unverified')) {
    throw "$sourceRelative has invalid source_chain_status: $sourceChainStatus"
  }
  $systemRoot = Split-Path -Parent (Split-Path -Parent $SourceDirectory)
  $rawSourcePath = Join-Path $systemRoot ($rawSourceFile -replace '/', '\')
  $analysisSourcePath = Join-Path $systemRoot ($analysisSourceFile -replace '/', '\')
  if (-not (Test-Path -LiteralPath $rawSourcePath -PathType Leaf)) { throw "Missing raw source: $rawSourceFile" }
  if (-not (Test-Path -LiteralPath $analysisSourcePath -PathType Leaf)) { throw "Missing analysis source: $analysisSourceFile" }
  if (((Get-FileHash -LiteralPath $rawSourcePath -Algorithm SHA256).Hash.ToLowerInvariant()) -ne $rawCurrentSha256) {
    throw "$sourceRelative raw_current_sha256 does not match $rawSourceFile."
  }
  if (((Get-FileHash -LiteralPath $analysisSourcePath -Algorithm SHA256).Hash.ToLowerInvariant()) -ne $analysisCurrentSha256) {
    throw "$sourceRelative analysis_current_sha256 does not match $analysisSourceFile."
  }
  if (($sourceChainStatus -in @('verified_current', 'historical_unverified')) -and (($rawSourceSha256 -ne $rawCurrentSha256) -or ($analysisSourceSha256 -ne $analysisCurrentSha256))) {
    throw "$sourceRelative declares $sourceChainStatus but source and current hashes differ."
  }
  if (($sourceChainStatus -eq 'source_changed') -and ($rawSourceSha256 -eq $rawCurrentSha256) -and ($analysisSourceSha256 -eq $analysisCurrentSha256)) {
    throw "$sourceRelative declares source_changed without a hash drift."
  }
  $sourceChainStatusCounts[$sourceChainStatus]++
  $sourceChainsByReport[$sourceRelative] = [pscustomobject]@{
    source_report_sha256 = $sourceReportSha256
    raw_source_file = $rawSourceFile
    raw_source_sha256 = $rawSourceSha256
    raw_current_sha256 = $rawCurrentSha256
    raw_source_hash_basis = $rawSourceHashBasis
    analysis_source_file = $analysisSourceFile
    analysis_source_sha256 = $analysisSourceSha256
    analysis_current_sha256 = $analysisCurrentSha256
    analysis_source_hash_basis = $analysisSourceHashBasis
    execution_version = $executionVersion
    provenance_contract = $provenanceContract
    source_chain_status = $sourceChainStatus
    last_screened_final_report_sha256 = $lastScreenedFinalReportSha256
    last_screened_build_batch_id = $lastScreenedBuildBatchId
    last_screened_builder_version = $lastScreenedBuilderVersion
  }
  $reportOverrideKey = 'report|{0}|event_date' -f $file.BaseName
  $reportOverride = $reviewOverrides[$reportOverrideKey]
  $summary = Get-Field $report 'data_quality_summary' ([pscustomobject]@{})
  $formal = @($report.closed_decisions | Where-Object { $null -ne $_ })
  $coarse = @($report.coarse_decision_records | Where-Object { $null -ne $_ })
  $taskRows = @($report.task_execution_records | Where-Object { $null -ne $_ })
  $unresolved = @($report.unresolved_decision_mentions | Where-Object { $null -ne $_ })

  $reports.Add([pscustomobject]@{
    schema_version = 'derived-report-v1.0'
    event_date = $eventDate
    event_date_basis = if ($null -ne $reportOverride) { 'human_review_confirmed_source_filename' } else { Get-Field $report 'event_date_basis' 'raw_report' }
    human_review_event_date_override_id = Get-Field $reportOverride 'review_id' $null
    source_report = $sourceRelative
    source_report_sha256 = $sourceReportSha256
    raw_source_file = $rawSourceFile
    raw_source_sha256 = $rawSourceSha256
    raw_current_sha256 = $rawCurrentSha256
    analysis_source_file = $analysisSourceFile
    analysis_source_sha256 = $analysisSourceSha256
    analysis_current_sha256 = $analysisCurrentSha256
    execution_version = $executionVersion
    provenance_contract = $provenanceContract
    source_chain_status = $sourceChainStatus
    last_screened_final_report_sha256 = $lastScreenedFinalReportSha256
    last_screened_build_batch_id = $lastScreenedBuildBatchId
    last_screened_builder_version = $lastScreenedBuilderVersion
    source_schema_version = Get-Field $report 'schema_version' 'unknown'
    report_type = Get-Field $report 'report_type' 'unknown'
    raw_submission_available = Get-Field $summary 'raw_submission_available' $null
    formal_decision_count = $formal.Count
    coarse_decision_record_count = $coarse.Count
    task_execution_record_count = $taskRows.Count
    unresolved_decision_mention_count = $unresolved.Count
    locked_prediction_available = Get-Field (Get-Field $report 'locked_prediction_scoring' ([pscustomobject]@{})) 'available' $null
    central_axis = $null
    central_axis_source = 'not_captured_in_source_reports'
    central_axis_confidence = 'not_available'
    research_use_assessment = Get-Field $report 'research_use_assessment' ([pscustomobject]@{})
    provenance = Get-Field $report 'provenance' ([pscustomobject]@{})
  })

  if (((Get-Field $report 'event_date_basis' $null) -match 'filename') -and ($null -eq $reportOverride)) {
    Add-Issue $issues $eventDate 'report' $file.BaseName 'event_date_inferred' 'medium' 'event_date' '事件日期来自源文件名，原始提交日期字段未填写。' $sourceRelative
  }

  $expectedFormal = Get-Field $summary 'formal_decision_count' $null
  if (($null -ne $expectedFormal) -and ([int]$expectedFormal -ne $formal.Count)) {
    Add-Issue $issues $eventDate 'report' $file.BaseName 'summary_count_mismatch' 'high' 'formal_decision_count' "摘要为$expectedFormal，数组实际为$($formal.Count)。" $sourceRelative
  }

  for ($i = 0; $i -lt $formal.Count; $i++) {
    $item = $formal[$i]
    $target = Get-Field $item 'decision_target' ([pscustomobject]@{})
    $choiceSet = Get-Field $item 'choice_set' ([pscustomobject]@{})
    $actual = Get-Field $item 'actual_choice' $null
    $quality = Get-Field $item 'quality' ([pscustomobject]@{})
    $eligibility = Get-Field $item 'eligibility' ([pscustomobject]@{})
    $decisionFallback = '{0}-D-{1}' -f $eventDate, ($i + 1)
    $decisionId = [string](Get-Field $item 'decision_id' $decisionFallback)
    $domain = [string](Get-Field $item 'decision_domain' (Get-Field $target 'domain' 'other'))
    $question = [string](Get-Field $target 'question' $null)
    $sourceDecisionTime = Get-Field $item 'decision_time' 'unknown'
    $sourceTimePrecision = Get-Field $item 'time_precision' 'unknown'
    $timeOverrideKey = 'decision|{0}|decision_time' -f $decisionId
    $timeOverride = $reviewOverrides[$timeOverrideKey]
    $decisionTime = $sourceDecisionTime
    $timePrecision = $sourceTimePrecision
    if ($null -ne $timeOverride) {
      $decisionTime = Get-Field $timeOverride 'confirmed_value' $sourceDecisionTime
      $timePrecision = Get-Field $timeOverride 'confirmed_time_precision' $sourceTimePrecision
    }
    $actualLabel = Get-ChoiceLabel $actual
    $mutuallyExclusive = Get-Field $choiceSet 'mutually_exclusive' $null
    $options = @(Get-Field $choiceSet 'options' @())
    $patternAnalysisEligible = Get-Field $item 'pattern_analysis_eligible' (Get-Field $eligibility 'pattern_analysis_eligible' $false)
    $strictBacktestEligible = Get-Field $item 'strict_backtest_eligible' (Get-Field $eligibility 'strict_backtest_eligible' $false)
    $causalClaimEligible = Get-Field $item 'causal_claim_eligible' (Get-Field $eligibility 'causal_claim_eligible' $false)
    $derivedAnalysisTier = if ($strictBacktestEligible -eq $true) { 'strict' } elseif ($patternAnalysisEligible -eq $true) { 'historical_pattern' } else { 'coarse' }
    $sourceAnalysisTier = [string](Get-Field $item 'analysis_tier' '')
    $analysisTier = if ($sourceAnalysisTier -in @('strict', 'historical_pattern', 'coarse', 'unresolved')) { $sourceAnalysisTier } else { $derivedAnalysisTier }
    $provenance = Get-Field $item 'provenance' ([pscustomobject]@{})
    $sourceTrace = @(Get-Field $item 'source_trace' (Get-Field $provenance 'source_trace' @()))
    $sourceDecisionFamily = [string](Get-Field $item 'decision_family' '')
    $ruleProposedDecisionFamily = Get-DecisionFamily $domain $question ([string](Get-Field $target 'target_type' '')) $options
    $familyOverrideKey = 'decision|{0}|decision_family' -f $decisionId
    $familyOverride = $reviewOverrides[$familyOverrideKey]
    $decisionFamily = if ($null -ne $familyOverride) { [string](Get-Field $familyOverride 'confirmed_value' $ruleProposedDecisionFamily) } elseif ($sourceDecisionFamily -in @('start_vs_defer', 'continue_vs_stop', 'consume_vs_abstain', 'confront_vs_avoid', 'timing_choice', 'plan_a_vs_plan_b')) { $sourceDecisionFamily } else { $ruleProposedDecisionFamily }
    $familySource = if ($null -ne $familyOverride) { 'human_review_override' } elseif ($sourceDecisionFamily -in @('start_vs_defer', 'continue_vs_stop', 'consume_vs_abstain', 'confront_vs_avoid', 'timing_choice', 'plan_a_vs_plan_b')) { 'source_label' } else { 'rule_based_fill' }
    $familyReviewRequired = (($null -eq $familyOverride) -and ($sourceDecisionFamily -in @('start_vs_defer', 'continue_vs_stop', 'consume_vs_abstain', 'confront_vs_avoid', 'timing_choice', 'plan_a_vs_plan_b')) -and ($sourceDecisionFamily -ne $ruleProposedDecisionFamily))
    $normalizedObservations = @(
      @(Get-Field $item 'pre_decision_observations' @()) | ForEach-Object {
        $o = $_
        [pscustomobject]@{
          feature_id = Get-Field $o 'feature_id' $null
          feature_family = Get-FeatureFamily $o
          feature_family_source = 'rule_v1'
          feature_family_confidence = Get-FeatureFamilyConfidence $o (Get-FeatureFamily $o)
          value = Get-Field $o 'value' $null
          source_type = Get-Field $o 'source_type' $null
          evidence_class = Get-Field $o 'evidence_class' $null
          source = Get-Field $o 'source' (Get-Field $o 'source_trace' $null)
          evidence = Get-Field $o 'evidence' $null
          confidence = Get-Field $o 'confidence' $null
        }
      }
    )
    $decisions.Add([pscustomobject]@{
      schema_version = 'derived-decision-v1.0'
      decision_id = $decisionId
      event_date = $eventDate
      subject_id = Get-Field $item 'subject_id' (Get-Field $report 'subject_id' 'unknown')
      decision_domain = $domain
      decision_family = $decisionFamily
      decision_family_source = $familySource
      decision_family_rule_proposal = $ruleProposedDecisionFamily
      decision_family_review_required = $familyReviewRequired
      decision_time = $decisionTime
      time_precision = $timePrecision
      prediction_cutoff = Get-Field $item 'prediction_cutoff' 'unknown'
      observation_window = Get-Field $item 'observation_window' 'unknown'
      choice_set = $choiceSet
      choice_set_completeness = Get-Field $item 'choice_set_completeness' (Get-Field $choiceSet 'completeness' 'unknown')
      actual_choice = $actualLabel
      actual_choice_confidence = Get-Field $item 'actual_choice_confidence' (Get-Field $actual 'confidence' 'unknown')
      pre_decision_observations = $normalizedObservations
      immediate_outcome = Get-Field $item 'immediate_outcome' ([pscustomobject]@{})
      quality_score = Get-Field $item 'quality_score' (Get-Field $quality 'total' $null)
      analysis_tier = $analysisTier
      pattern_analysis_eligible = $patternAnalysisEligible
      strict_backtest_eligible = $strictBacktestEligible
      causal_claim_eligible = $causalClaimEligible
      state_capture_disposition = Get-Field $item 'state_capture_disposition' 'unknown'
      source_report = $sourceRelative
      source_report_sha256 = $sourceReportSha256
      raw_source_file = $rawSourceFile
      raw_source_sha256 = $rawSourceSha256
      raw_current_sha256 = $rawCurrentSha256
      analysis_source_file = $analysisSourceFile
      analysis_source_sha256 = $analysisSourceSha256
      analysis_current_sha256 = $analysisCurrentSha256
      execution_version = $executionVersion
      provenance_contract = $provenanceContract
      source_chain_status = $sourceChainStatus
      source_trace = $sourceTrace
      human_review_override_id = Get-Field $timeOverride 'review_id' (Get-Field $item 'human_review_override_id' $null)
      source_decision_time = $sourceDecisionTime
      source_time_precision = $sourceTimePrecision
      prediction_cutoff_precision = Get-Field $item 'prediction_cutoff_precision' 'unknown'
      target_type = Get-Field $target 'target_type' 'unknown'
      question = $question
      mutually_exclusive = $mutuallyExclusive
      options = $options
      quality_total = Get-Field $quality 'total' $null
      quality_status = Get-Field $quality 'status' 'unknown'
      eligibility = $eligibility
      provenance = $provenance
    })
    if ($mutuallyExclusive -ne $true) { Add-Issue $issues $eventDate 'decision' $decisionId 'choice_set_not_mutually_exclusive' 'high' 'choice_set.mutually_exclusive' '正式决策的互斥选项标记不是 true。' $sourceRelative }
    if ([string]::IsNullOrWhiteSpace($actualLabel) -or $actualLabel -eq 'unknown') { Add-Issue $issues $eventDate 'decision' $decisionId 'actual_choice_missing' 'high' 'actual_choice' '正式决策缺少可用实际选择标签。' $sourceRelative }
    if (($timePrecision -eq 'unknown') -and ($null -eq $timeOverride)) { Add-Issue $issues $eventDate 'decision' $decisionId 'decision_time_unknown' 'medium' 'decision_time' '正式决策的时间精度为 unknown。' $sourceRelative }
    if ($familyReviewRequired) { Add-Issue $issues $eventDate 'decision' $decisionId 'decision_family_review_required' 'medium' 'decision_family' "源标签为 $sourceDecisionFamily，但规则建议为 $ruleProposedDecisionFamily；需人工确认。" $sourceRelative }
    $total = Get-Field $quality 'total' $null
    if (($null -ne $total) -and ([int]$total -lt 7) -and ($null -eq $timeOverride)) { Add-Issue $issues $eventDate 'decision' $decisionId 'formal_quality_below_selected_threshold' 'medium' 'quality.total' ('Formal decision quality total is {0}, below selected threshold 7.' -f $total) $sourceRelative }
  }

  for ($i = 0; $i -lt $coarse.Count; $i++) {
    $item = $coarse[$i]
    $coarseFallback = '{0}-CD-{1}' -f $eventDate, ($i + 1)
    $recordId = [string](Get-Field $item 'record_id' (Get-Field $item 'item_id' $coarseFallback))
    $target = Get-Field $item 'decision_target' $null
    $choiceSet = Get-Field $item 'choice_set' $null
    $sourceDecisionTime = Get-Field $item 'decision_time' 'unknown'
    $sourceTimePrecision = Get-Field $item 'time_precision' 'unknown'
    $timeOverrideKey = 'coarse_decision|{0}|decision_time' -f $recordId
    $timeOverride = $reviewOverrides[$timeOverrideKey]
    $decisionTime = $sourceDecisionTime
    $timePrecision = $sourceTimePrecision
    if ($null -ne $timeOverride) {
      $decisionTime = Get-Field $timeOverride 'confirmed_value' $sourceDecisionTime
      $timePrecision = Get-Field $timeOverride 'confirmed_time_precision' $sourceTimePrecision
    }
    $actual = Get-Field $item 'actual_choice' $null
    $actualLabel = Get-ChoiceLabel $actual
    if ($null -eq $actualLabel) { $actualLabel = [string]$actual }
    $coarseOverrideKey = 'coarse_decision|{0}|actual_choice' -f $recordId
    $coarseOverride = $reviewOverrides[$coarseOverrideKey]
    $sourceActualChoice = $actualLabel
    if ($null -ne $coarseOverride) { $actualLabel = Get-Field $coarseOverride 'confirmed_value' $sourceActualChoice }
    $coarseDecisions.Add([pscustomobject]@{
      schema_version = 'derived-coarse-decision-v1.0'
      record_id = $recordId
      event_date = [string](Get-Field $item 'event_date' $eventDate)
      source_report = $sourceRelative
      source_report_sha256 = $sourceReportSha256
      raw_source_file = $rawSourceFile
      raw_source_sha256 = $rawSourceSha256
      raw_current_sha256 = $rawCurrentSha256
      analysis_source_file = $analysisSourceFile
      analysis_source_sha256 = $analysisSourceSha256
      analysis_current_sha256 = $analysisCurrentSha256
      execution_version = $executionVersion
      provenance_contract = $provenanceContract
      source_chain_status = $sourceChainStatus
      decision_time = $decisionTime
      time_precision = $timePrecision
      source_decision_time = $sourceDecisionTime
      source_time_precision = $sourceTimePrecision
      human_review_time_override_id = Get-Field $timeOverride 'review_id' $null
      decision_target = $target
      decision_family = Get-DecisionFamily '' ([string]$target) ''
      choice_set = $choiceSet
      actual_choice = $actualLabel
      source_actual_choice = $sourceActualChoice
      human_review_override_id = Get-Field $coarseOverride 'review_id' $null
      review_status = if ($null -ne $coarseOverride) { 'resolved' } else { 'not_reviewed' }
      actual_choice_confidence = Get-Field $item 'actual_choice_confidence' (Get-Field $actual 'confidence' 'unknown')
      immediate_outcome = Get-Field $item 'immediate_outcome' ([pscustomobject]@{})
      missing_fields = @(Get-Field $item 'missing_fields' (Get-Field $item 'missing_for_strict_ledger' @()))
      record_status = Get-Field $item 'record_status' 'unknown'
      quality = Get-Field $item 'quality' ([pscustomobject]@{})
      eligibility = Get-Field $item 'eligibility' ([pscustomobject]@{})
      source_conflict = Get-Field $item 'source_conflict' (Get-Field $item 'raw_claim_conflict' $null)
    })
    if (((Get-Field $item 'source_conflict' $null) -or (Get-Field $item 'raw_claim_conflict' $null)) -and ($null -eq $coarseOverride)) { Add-Issue $issues $eventDate 'coarse_decision' $recordId 'source_conflict' 'high' 'source_conflict' '原始来源与补充或结构化字段存在冲突。' $sourceRelative }
    if (($timePrecision -in @('unknown', 'coarse')) -and ($null -eq $timeOverride)) { Add-Issue $issues $eventDate 'coarse_decision' $recordId 'coarse_or_unknown_time' 'medium' 'decision_time' '粗粒度决策的时间不可用于严格回测。' $sourceRelative }
  }

  for ($i = 0; $i -lt $taskRows.Count; $i++) {
    $item = $taskRows[$i]
    $taskFallback = '{0}-T-{1}' -f $eventDate, ($i + 1)
    $taskId = [string](Get-Field $item 'record_id' (Get-Field $item 'task_id' $taskFallback))
    $taskText = Get-Field $item 'task' (Get-Field $item 'item' 'unknown')
    $sourceState = Get-Field $item 'status' (Get-Field $item 'state' 'unknown')
    $overrideKey = 'task|{0}|status' -f $taskId
    $taskOverride = $reviewOverrides[$overrideKey]
    $state = $sourceState
    if ($null -ne $taskOverride) { $state = Get-Field $taskOverride 'confirmed_value' $sourceState }
    $canonicalTaskStatus = Get-CanonicalTaskStatus ([string]$state)
    $tasks.Add([pscustomobject]@{
      schema_version = 'derived-task-v1.0'
      task_id = $taskId
      event_date = $eventDate
      source_report = $sourceRelative
      source_report_sha256 = $sourceReportSha256
      raw_source_file = $rawSourceFile
      raw_source_sha256 = $rawSourceSha256
      raw_current_sha256 = $rawCurrentSha256
      analysis_source_file = $analysisSourceFile
      analysis_source_sha256 = $analysisSourceSha256
      analysis_current_sha256 = $analysisCurrentSha256
      execution_version = $executionVersion
      provenance_contract = $provenanceContract
      source_chain_status = $sourceChainStatus
      task = $taskText
      task_family = Get-TaskFamily ([string]$taskText)
      status = $state
      source_status = $sourceState
      task_status_canonical = $canonicalTaskStatus
      task_status_canonical_source = 'rule_v1'
      human_review_override_id = Get-Field $taskOverride 'review_id' $null
      review_status = if ($null -ne $taskOverride) { 'resolved' } else { 'not_reviewed' }
      time = Get-Field $item 'time' 'unknown'
      duration = Get-Field $item 'duration' 'unknown'
      evidence = Get-Field $item 'evidence' (Get-Field $item 'documented_action' $null)
      evidence_class = Get-Field $item 'evidence_class' 'unknown'
      detail = Get-Field $item 'detail' $null
      documented_constraint = Get-Field $item 'documented_constraint' $null
      unknowns = @(Get-Field $item 'unknowns' @())
      source_conflict = Get-Field $item 'source_conflict' (Get-Field $item 'conflict' $null)
    })
    if (((Get-Field $item 'source_conflict' $null) -or (Get-Field $item 'conflict' $null)) -and ($null -eq $taskOverride)) { Add-Issue $issues $eventDate 'task' $taskId 'task_source_conflict' 'high' 'source_conflict' '任务记录存在来源冲突。' $sourceRelative }
    if ($canonicalTaskStatus -eq 'execution_or_completion_unknown') { Add-Issue $issues $eventDate 'task' $taskId 'task_status_canonical_unknown' 'medium' 'status' '任务记录只说明发生或执行，无法确认完成程度。' $sourceRelative }
  }

  foreach ($item in $unresolved) {
    $recordId = Get-Field $item 'mention_id' $null
    if ([string]::IsNullOrWhiteSpace([string]$recordId)) { $recordId = Get-Field $item 'record_id' 'unknown' }
    $recordId = [string]$recordId
    $unresolvedOverrideKey = 'unresolved_decision|{0}|actual_choice' -f $recordId
    $unresolvedOverride = $reviewOverrides[$unresolvedOverrideKey]
    if ($null -eq $unresolvedOverride) {
      Add-Issue $issues $eventDate 'unresolved_decision' $recordId 'unresolved_decision_mention' 'medium' 'actual_choice' '记录提到取舍但没有可训练的实际选择。' $sourceRelative
    } elseif ((Get-Field $unresolvedOverride 'resolution_type' '') -ne 'confirmed_unresolved') {
      $coarseDecisions.Add([pscustomobject]@{
        schema_version = 'derived-coarse-decision-v1.0'
        record_id = $recordId
        event_date = $eventDate
        source_report = $sourceRelative
        source_report_sha256 = $sourceReportSha256
        raw_source_file = $rawSourceFile
        raw_source_sha256 = $rawSourceSha256
        raw_current_sha256 = $rawCurrentSha256
        analysis_source_file = $analysisSourceFile
        analysis_source_sha256 = $analysisSourceSha256
        analysis_current_sha256 = $analysisCurrentSha256
        execution_version = $executionVersion
        provenance_contract = $provenanceContract
        source_chain_status = $sourceChainStatus
        decision_time = 'unknown'
        time_precision = 'unknown'
        decision_target = Get-Field $item 'decision_target' 'unknown'
        decision_family = Get-DecisionFamily '' ([string](Get-Field $item 'decision_target' '')) ''
        choice_set = [pscustomobject]@{ options = @(Get-Field $item 'known_options' @()); mutually_exclusive = 'unknown' }
        actual_choice = Get-Field $unresolvedOverride 'confirmed_value' 'unknown'
        actual_choice_confidence = 'human_reviewed'
        immediate_outcome = [pscustomobject]@{ observed = 'Outcome reported after the original event date.'; outcome_event_date = 'unknown' }
        missing_fields = @('outcome_event_date', 'decision_time', 'prediction_cutoff', 'observation_window')
        record_status = 'human_review_resolved_from_unresolved_time_missing'
        quality = [pscustomobject]@{ status = 'review'; total = $null }
        eligibility = [pscustomobject]@{ pattern_analysis_eligible = $true; coarse_training_eligible = 'review_required'; strict_backtest_eligible = $false; causal_claim_eligible = $false }
        source_conflict = $null
        human_review_override_id = Get-Field $unresolvedOverride 'review_id' $null
        review_status = 'resolved'
      })
    }
  }

  $manifestInputs.Add([pscustomobject]@{
    source_report = $sourceRelative
    sha256 = $sourceReportSha256
    final_report_sha256 = $sourceReportSha256
    raw_source_file = $rawSourceFile
    raw_source_sha256 = $rawSourceSha256
    raw_current_sha256 = $rawCurrentSha256
    raw_source_hash_basis = $rawSourceHashBasis
    analysis_source_file = $analysisSourceFile
    analysis_source_sha256 = $analysisSourceSha256
    analysis_current_sha256 = $analysisCurrentSha256
    analysis_source_hash_basis = $analysisSourceHashBasis
    execution_version = $executionVersion
    provenance_contract = $provenanceContract
    source_chain_status = $sourceChainStatus
    last_screened_final_report_sha256 = $lastScreenedFinalReportSha256
    last_screened_build_batch_id = $lastScreenedBuildBatchId
    last_screened_builder_version = $lastScreenedBuilderVersion
    event_date = $eventDate
  })
}

foreach ($issue in $issues) {
  $chain = $sourceChainsByReport[[string](Get-Field $issue 'source_report' '')]
  if ($null -ne $chain) {
    foreach ($field in $chain.PSObject.Properties) {
      $issue | Add-Member -NotePropertyName $field.Name -NotePropertyValue $field.Value -Force
    }
  }
}

Write-Jsonl (Join-Path $OutputDirectory 'reports.jsonl') $reports
Write-Jsonl (Join-Path $OutputDirectory 'decisions.jsonl') $decisions
Write-Jsonl (Join-Path $OutputDirectory 'coarse_decisions.jsonl') $coarseDecisions
Write-Jsonl (Join-Path $OutputDirectory 'tasks.jsonl') $tasks
Write-Jsonl (Join-Path $QualityDirectory 'quality_issues.jsonl') $issues

$fingerprintSource = [pscustomobject][ordered]@{
  script_version = $ScriptVersion
  inputs = $manifestInputs
  record_counts = [pscustomobject][ordered]@{
    reports = $reports.Count
    decisions = $decisions.Count
    coarse_decisions = $coarseDecisions.Count
    tasks = $tasks.Count
    quality_issues = $issues.Count
  }
  human_review_override_count = $reviewOverrides.Count
}
$fingerprintJson = $fingerprintSource | ConvertTo-Json -Depth 20 -Compress
$fingerprintBytes = [System.Text.Encoding]::UTF8.GetBytes($fingerprintJson)
$buildFingerprint = [System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::HashData($fingerprintBytes)).Replace('-', '').ToLowerInvariant()
$existingManifestPath = Join-Path $OutputDirectory 'manifest.json'
if (Test-Path -LiteralPath $existingManifestPath -PathType Leaf) {
  $existingManifest = Get-Content -LiteralPath $existingManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ((Get-Field $existingManifest 'build_fingerprint_sha256' '') -eq $buildFingerprint) {
    $BuildBatchId = [string](Get-Field $existingManifest 'build_batch_id' $BuildBatchId)
    $BuildGeneratedAt = [datetimeoffset](Get-Field $existingManifest 'generated_at' $BuildGeneratedAt)
  }
}

$manifest = [pscustomobject]@{
  schema_version = 'derived-manifest-v1.2'
  script_version = $ScriptVersion
  source_chain_contract = $SourceChainContract
  source_chain_field_complete = $true
  source_chain_all_verified_current = ($sourceChainStatusCounts.verified_current -eq $reportFiles.Count)
  source_chain_status_counts = [pscustomobject]$sourceChainStatusCounts
  build_batch_id = $BuildBatchId
  build_fingerprint_sha256 = $buildFingerprint
  generated_at = $BuildGeneratedAt.ToString('o')
  source_directory = $SourceDirectory
  output_directory = $OutputDirectory
  quality_directory = $QualityDirectory
  source_file_glob = '*最终数据报告.json'
  source_report_count = $reportFiles.Count
  record_counts = [pscustomobject]@{
    reports = $reports.Count
    decisions = $decisions.Count
    coarse_decisions = $coarseDecisions.Count
    tasks = $tasks.Count
    quality_issues = $issues.Count
  }
  inputs = $manifestInputs
  human_review_override_count = $reviewOverrides.Count
  raw_files_modified = $false
}
$manifestText = $manifest | ConvertTo-Json -Depth 20
$manifestPath = Join-Path $OutputDirectory 'manifest.json'
$manifestTemporaryPath = "$manifestPath.tmp"
[System.IO.File]::WriteAllText($manifestTemporaryPath, $manifestText + [Environment]::NewLine, $Utf8NoBom)
Move-ReplaceFile $manifestTemporaryPath $manifestPath

$registrySynchronizer = Join-Path $PSScriptRoot 'sync_ingestion_registry.ps1'
if (Test-Path -LiteralPath $registrySynchronizer -PathType Leaf) {
  $systemRoot = Split-Path -Parent (Split-Path -Parent $SourceDirectory)
  & $registrySynchronizer -SystemRoot $systemRoot
}

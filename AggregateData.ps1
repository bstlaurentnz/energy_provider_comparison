# PowerShell script to aggregate sensor data into 1-minute intervals
param(
    [Parameter(Mandatory=$true)]
    [string]$InputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AggregationMethod = "Average"  # Options: Average, Max, Min, Last
)

try {
    # Check if input file exists
    if (-not (Test-Path $InputPath)) {
        Write-Error "Input file not found: $InputPath"
        exit 1
    }
    
    # Set output path if not provided
    if ($OutputPath -eq "") {
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($InputPath)
        $extension = [System.IO.Path]::GetExtension($InputPath)
        $directory = [System.IO.Path]::GetDirectoryName($InputPath)
        $OutputPath = Join-Path $directory "${baseName}_1min${extension}"
    }
    
    # Check if file has headers by reading first line
    $firstLine = Get-Content $InputPath -First 1
    
    if ($firstLine -match "entity_id|state|last_changed") {
        # File has headers - use them
        $data = Import-Csv $InputPath
    } else {
        # File has no headers - assign them
        $data = Import-Csv $InputPath -Header "entity_id", "state", "last_changed"
    }
    
    Write-Host "Processing $($data.Count) records..."
    
    # Filter out "unknown" values and convert timestamps, then group by entity and minute
    $groupedData = $data | Where-Object { 
        $_.state -ne "unknown" -and $_.state -ne "" -and $_.state -ne $null 
    } | ForEach-Object {
        try {
            $timestamp = [DateTime]::Parse($_.last_changed)
            $minuteKey = $timestamp.ToString("yyyy-MM-dd HH:mm:00")
            
            [PSCustomObject]@{
                entity_id = $_.entity_id
                state = [double]$_.state
                minute = $minuteKey
                timestamp = $timestamp
            }
        }
        catch {
            # Skip records with invalid timestamps or state values
            Write-Warning "Skipping record with invalid data: entity_id=$($_.entity_id), state=$($_.state), timestamp=$($_.last_changed)"
            $null
        }
    } | Where-Object { $_ -ne $null } | Group-Object { "$($_.entity_id)|$($_.minute)" }
    
    # Aggregate data for each minute
    $aggregatedData = foreach ($group in $groupedData) {
        $parts = $group.Name -split '\|'
        $entityId = $parts[0]
        $minute = $parts[1]
        
        $values = $group.Group | ForEach-Object { $_.state }
        
        switch ($AggregationMethod) {
            "Average" { $aggregatedValue = ($values | Measure-Object -Average).Average }
            "Max" { $aggregatedValue = ($values | Measure-Object -Maximum).Maximum }
            "Min" { $aggregatedValue = ($values | Measure-Object -Minimum).Minimum }
            "Last" { $aggregatedValue = ($group.Group | Sort-Object timestamp | Select-Object -Last 1).state }
            default { $aggregatedValue = ($values | Measure-Object -Average).Average }
        }
        
        [PSCustomObject]@{
            entity_id = $entityId
            state = [math]::Round($aggregatedValue, 3)
            last_changed = $minute + ".000Z"
        }
    }
    
    # Sort by entity and time
    $sortedData = $aggregatedData | Sort-Object entity_id, last_changed
    
    # Export to CSV
    $sortedData | Export-Csv $OutputPath -NoTypeInformation
    
    Write-Host "Successfully aggregated data into 1-minute intervals"
    Write-Host "Input records: $($data.Count)"
    Write-Host "Output records: $($sortedData.Count)"
    Write-Host "Output file: $OutputPath"
    Write-Host "Aggregation method: $AggregationMethod"
    
} catch {
    Write-Error "Error processing file: $_"
    exit 1
}

# Alternative one-liner for quick processing (if you have the data in the right format)
# Import-Csv "input.csv" -Header "entity_id","state","last_changed" | ForEach-Object { $timestamp = [DateTime]::Parse($_.last_changed); [PSCustomObject]@{ entity_id = $_.entity_id; state = [double]$_.state; minute = $timestamp.ToString("yyyy-MM-dd HH:mm:00") } } | Group-Object { "$($_.entity_id)|$($_.minute)" } | ForEach-Object { $parts = $_.Name -split '\|'; [PSCustomObject]@{ entity_id = $parts[0]; state = [math]::Round(($_.Group | Measure-Object -Property state -Average).Average, 3); last_changed = $parts[1] + ".000Z" } } | Sort-Object entity_id, last_changed | Export-Csv "output_1min.csv" -NoTypeInformation
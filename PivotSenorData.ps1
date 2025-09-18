# PowerShell script to pivot sensor data - one row per timestamp with entities as columns
param(
    [Parameter(Mandatory=$true)]
    [string]$InputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "",
    
    [Parameter(Mandatory=$false)]
    [int]$TimeIntervalMinutes = 1  # Round timestamps to this interval
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
        $OutputPath = Join-Path $directory "${baseName}_pivoted${extension}"
    }
    
    # Check if file has headers
    $firstLine = Get-Content $InputPath -First 1
    
    if ($firstLine -match "entity_id|state|last_changed") {
        $data = Import-Csv $InputPath
    } else {
        $data = Import-Csv $InputPath -Header "entity_id", "state", "last_changed"
    }
    
    Write-Host "Processing $($data.Count) records..."
    
    # Get unique entities to create columns
    $entities = $data | Select-Object -ExpandProperty entity_id | Sort-Object -Unique
    Write-Host "Found entities: $($entities -join ', ')"
    
    # Process data and round timestamps if needed
    $processedData = $data | ForEach-Object {
        $timestamp = [DateTime]::Parse($_.last_changed)
        
        # Round to specified interval (in minutes)
        if ($TimeIntervalMinutes -gt 0) {
            $roundedMinutes = [math]::Floor($timestamp.Minute / $TimeIntervalMinutes) * $TimeIntervalMinutes
            $roundedTime = New-Object DateTime($timestamp.Year, $timestamp.Month, $timestamp.Day, $timestamp.Hour, $roundedMinutes, 0)
        } else {
            $roundedTime = $timestamp
        }
        
        [PSCustomObject]@{
            entity_id = $_.entity_id
            state = $_.state
            timestamp = $roundedTime
            timestamp_str = $roundedTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        }
    }
    
    # Group by timestamp and create pivot table
    $pivotedData = $processedData | Group-Object timestamp_str | ForEach-Object {
        $timeGroup = $_
        $timestamp = $timeGroup.Name
        
        # Create base object with timestamp
        $pivotRow = [ordered]@{
            timestamp = $timestamp
        }
        
        # Add each entity as a column
        foreach ($entity in $entities) {
            $entityData = $timeGroup.Group | Where-Object { $_.entity_id -eq $entity }
            if ($entityData) {
                # If multiple values for same entity at same time, take the last one
                $value = ($entityData | Sort-Object timestamp | Select-Object -Last 1).state
                $pivotRow[$entity] = $value
            } else {
                $pivotRow[$entity] = 0
            }
        }
        
        [PSCustomObject]$pivotRow
    }
    
    # Sort by timestamp
    $sortedPivotData = $pivotedData | Sort-Object timestamp
    
    # Export to CSV
    $sortedPivotData | Export-Csv $OutputPath -NoTypeInformation
    
    Write-Host "Successfully pivoted data"
    Write-Host "Input records: $($data.Count)"
    Write-Host "Output records: $($sortedPivotData.Count)"
    Write-Host "Entities as columns: $($entities.Count)"
    Write-Host "Output file: $OutputPath"
    
} catch {
    Write-Error "Error processing file: $_"
    exit 1
}

# Example usage notes:
Write-Host ""
Write-Host "Usage examples:"
Write-Host "  .\PivotSensorData.ps1 -InputPath 'sensor_data.csv'"
Write-Host "  .\PivotSensorData.ps1 -InputPath 'data.csv' -TimeIntervalMinutes 5"
Write-Host "  .\PivotSensorData.ps1 -InputPath 'data.csv' -TimeIntervalMinutes 0  # No rounding"
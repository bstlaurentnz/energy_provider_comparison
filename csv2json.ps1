# More comprehensive script with error handling
param(
    [Parameter(Mandatory=$true)]
    [string]$InputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "",
    
    [Parameter(Mandatory=$false)]
    [int]$Depth = 2
)

try {
    # Check if input file exists
    if (-not (Test-Path $InputPath)) {
        Write-Error "Input file not found: $InputPath"
        exit 1
    }
    
    # Set output path if not provided
    if ($OutputPath -eq "") {
        $OutputPath = [System.IO.Path]::ChangeExtension($InputPath, ".json")
    }
    
    # Import CSV and convert to JSON
    $data = Import-Csv $InputPath
    $json = $data | ConvertTo-Json -Depth $Depth
    
    # Write to output file
    $json | Out-File $OutputPath -Encoding UTF8
    
    Write-Host "Successfully converted $InputPath to $OutputPath"
    Write-Host "Converted $($data.Count) records"
    
} catch {
    Write-Error "Error converting file: $_"
    exit 1
}
$mainPath = Join-Path -Path $PSScriptRoot -ChildPath 'main.py'

if (-not (Test-Path -LiteralPath $mainPath -PathType Leaf)) {
    throw "Arquivo main.py não encontrado: $mainPath"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python não encontrado no PATH. Instale o Python ou adicione-o ao PATH.'
}

Push-Location -LiteralPath $PSScriptRoot
try {
    & python $mainPath @args
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $exitCode
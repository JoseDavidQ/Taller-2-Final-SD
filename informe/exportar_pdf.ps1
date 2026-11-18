# Exporta el .docx del informe a PDF usando Word (hay que tener Microsoft Word instalado).
# Uso:  .\informe\exportar_pdf.ps1
$docx = (Get-ChildItem -Path $PSScriptRoot -Filter "Informe Taller 2*.docx" | Select-Object -First 1).FullName
$pdf  = [System.IO.Path]::ChangeExtension($docx, ".pdf")
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {
    $d = $w.Documents.Open($docx)
    $d.Fields.Update() | Out-Null
    $d.SaveAs([ref]$pdf, [ref]17)   # 17 = wdFormatPDF
    Write-Host "Paginas:" $d.ComputeStatistics(2)
    $d.Close([ref]0)
} finally { $w.Quit() }
Write-Host "PDF: $pdf"

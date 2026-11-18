param([Parameter(Mandatory=$true)][string]$Folder,[Parameter(Mandatory=$true)][string]$Output,[string]$Pattern='*.png',[int]$Columns=2,[int]$Width=480,[int]$Height=350)
# Inspection derivative only. Original Isaac PNGs remain unchanged and authoritative.
Add-Type -AssemblyName System.Drawing
$items=@(Get-ChildItem -LiteralPath $Folder -Recurse -Filter $Pattern | Sort-Object FullName)
if($items.Count -eq 0){throw 'No actual PNGs found'}
$rows=[int][Math]::Ceiling($items.Count/[double]$Columns)
$canvas=New-Object System.Drawing.Bitmap ($Columns*$Width),($rows*$Height)
$graphics=[System.Drawing.Graphics]::FromImage($canvas)
$font=New-Object System.Drawing.Font 'Arial',10
try {
 $graphics.Clear([System.Drawing.Color]::White)
 for($i=0;$i -lt $items.Count;$i++) {
  $img=[System.Drawing.Image]::FromFile($items[$i].FullName)
  try {
   $scale=[Math]::Min(($Width-4)/[double]$img.Width,($Height-28)/[double]$img.Height)
   $x=($i % $Columns)*$Width;$y=[int][Math]::Floor($i/[double]$Columns)*$Height
   $graphics.DrawString(($items[$i].Directory.Name+' / '+$items[$i].Name),$font,[System.Drawing.Brushes]::Black,[single]($x+3),[single]($y+3))
   $graphics.DrawImage($img,[int]$x,[int]($y+26),[int]($img.Width*$scale),[int]($img.Height*$scale))
  } finally {$img.Dispose()}
 }
 $canvas.Save($Output,[System.Drawing.Imaging.ImageFormat]::Png)
} finally {$font.Dispose();$graphics.Dispose();$canvas.Dispose()}
Write-Output ('INSPECTION_DERIVATIVE_ONLY '+$items.Count+' actual PNGs; originals unchanged')

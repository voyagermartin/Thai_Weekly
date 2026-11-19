Add-Type -AssemblyName System.Drawing

function Generate-PwaIcon {
    param(
        [int]$size,
        [string]$outputPath,
        [bool]$isMaskable
    )
    
    $bmp = New-Object System.Drawing.Bitmap $size, $size
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

    # 1. Base dark purple background
    $rect = New-Object System.Drawing.Rectangle 0, 0, $size, $size
    $bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        $rect,
        [System.Drawing.ColorTranslator]::FromHtml('#170f24'),
        [System.Drawing.ColorTranslator]::FromHtml('#0d0814'),
        45.0
    )
    $g.FillRectangle($bgBrush, $rect)

    # 2. Outer badge (rounded rect) for standard icon, full bleed for maskable
    if (-not $isMaskable) {
        $padding = [int]($size * 0.05)
        $badgeSize = $size - ($padding * 2)
        $radius = [int]($badgeSize * 0.22)
        $badgeRect = New-Object System.Drawing.Rectangle $padding, $padding, $badgeSize, $badgeSize
        
        $path = New-Object System.Drawing.Drawing2D.GraphicsPath
        $d = $radius * 2
        $path.AddArc($badgeRect.X, $badgeRect.Y, $d, $d, 180, 90)
        $path.AddArc(($badgeRect.Right - $d), $badgeRect.Y, $d, $d, 270, 90)
        $path.AddArc(($badgeRect.Right - $d), ($badgeRect.Bottom - $d), $d, $d, 0, 90)
        $path.AddArc($badgeRect.X, ($badgeRect.Bottom - $d), $d, $d, 90, 90)
        $path.CloseFigure()

        $cardBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            $badgeRect,
            [System.Drawing.ColorTranslator]::FromHtml('#231738'),
            [System.Drawing.ColorTranslator]::FromHtml('#120a1c'),
            45.0
        )
        $g.FillPath($cardBrush, $path)

        $penWidth = [math]::Max(2, [int]($size * 0.02))
        $borderPen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml('#f59e0b'), $penWidth)
        $g.DrawPath($borderPen, $path)
    }

    # 3. Thai Character 'ไ'
    $fontSizeRatio = if ($isMaskable) { 0.44 } else { 0.48 }
    $fontSize = [float]($size * $fontSizeRatio)
    $font = New-Object System.Drawing.Font('Leelawadee UI', $fontSize, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $thaiText = 'ไ'
    
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Center

    $charOffsetRatio = if ($isMaskable) { -0.09 } else { -0.08 }
    $charX = [float]($size * $charOffsetRatio)
    $charY = [float](-$size * 0.02)
    $charRect = New-Object System.Drawing.RectangleF $charX, $charY, ([float]$size), ([float]$size)

    $textBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        $rect,
        [System.Drawing.ColorTranslator]::FromHtml('#fde047'),
        [System.Drawing.ColorTranslator]::FromHtml('#f59e0b'),
        90.0
    )
    $g.DrawString($thaiText, $font, $textBrush, $charRect, $sf)

    # 4. Soundwave bars
    $waveScale = if ($isMaskable) { 0.72 } else { 0.85 }
    $baseXRatio = if ($isMaskable) { 0.68 } else { 0.70 }
    $baseX = [int]($size * $baseXRatio)
    $centerY = [int]($size * 0.50)
    $barW = [math]::Max(3, [int]($size * 0.035 * $waveScale))
    $barGap = [math]::Max(2, [int]($size * 0.022 * $waveScale))
    
    $heights = @(
        [int]($size * 0.14 * $waveScale),
        [int]($size * 0.28 * $waveScale),
        [int]($size * 0.20 * $waveScale),
        [int]($size * 0.10 * $waveScale)
    )

    for ($i = 0; $i -lt 4; $i++) {
        $bh = $heights[$i]
        $bx = $baseX + ($i * ($barW + $barGap))
        $by = $centerY - [int]($bh / 2)
        $barRect = New-Object System.Drawing.Rectangle $bx, $by, $barW, $bh
        $barR = [int]($barW / 2)
        
        $barPath = New-Object System.Drawing.Drawing2D.GraphicsPath
        $bd = $barR * 2
        $barPath.AddArc($barRect.X, $barRect.Y, $bd, $bd, 180, 90)
        $barPath.AddArc(($barRect.Right - $bd), $barRect.Y, $bd, $bd, 270, 90)
        $barPath.AddArc(($barRect.Right - $bd), ($barRect.Bottom - $bd), $bd, $bd, 0, 90)
        $barPath.AddArc($barRect.X, ($barRect.Bottom - $bd), $bd, $bd, 90, 90)
        $barPath.CloseFigure()

        $waveBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            $barRect,
            [System.Drawing.ColorTranslator]::FromHtml('#38bdf8'),
            [System.Drawing.ColorTranslator]::FromHtml('#a855f7'),
            90.0
        )
        $g.FillPath($waveBrush, $barPath)
    }

    $bmp.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose()
    $bmp.Dispose()
    Write-Host "Successfully generated $outputPath ($size x $size)"
}

Generate-PwaIcon -size 512 -outputPath 'icons/icon-512.png' -isMaskable $false
Generate-PwaIcon -size 192 -outputPath 'icons/icon-192.png' -isMaskable $false
Generate-PwaIcon -size 512 -outputPath 'icons/icon-maskable-512.png' -isMaskable $true
Generate-PwaIcon -size 192 -outputPath 'icons/icon-maskable-192.png' -isMaskable $true
Generate-PwaIcon -size 180 -outputPath 'icons/apple-touch-icon.png' -isMaskable $false

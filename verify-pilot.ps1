param([string]$DevRoot='E:\TUNIBIZ-Dev')
$ErrorActionPreference='Stop'
$apk=Join-Path $DevRoot 'TUNIBIZ-v0.5.0-pilot-candidate.apk'
$repo=$PSScriptRoot
$bt=Get-ChildItem "$env:LOCALAPPDATA\Android\Sdk\build-tools" -Directory | Where-Object {Test-Path ($_.FullName+'\apksigner.bat')} | Sort-Object Name -Descending | Select-Object -First 1
$verify=@(& ($bt.FullName+'\apksigner.bat') verify --verbose --print-certs $apk)
if($LASTEXITCODE -ne 0){throw 'Invalid APK signature'}
$certLine=($verify | Where-Object {$_ -match 'certificate SHA-256 digest:'} | Select-Object -First 1)
$cert=($certLine -split ': ')[-1].Trim()
if($cert -ne '2c1b7971401f1aa3d72f9e4e15b25c7218f4f5f5409a0a14681dfc7a02bc876d'){throw 'Permanent certificate mismatch'}
$badging=@(& ($bt.FullName+'\aapt.exe') dump badging $apk)
$package=($badging | Where-Object {$_ -match '^package:'} | Select-Object -First 1)
if($package -notmatch "name='tn.tunibiz.tunibiz_mobile' versionCode='7' versionName='0.5.0'"){throw 'APK identity mismatch'}
$resources=@(& ($bt.FullName+'\aapt2.exe') dump resources $apk)
if($LASTEXITCODE -ne 0){throw 'APK resources cannot be inspected'}
$firebaseId='1:900545281118:android:9612375c25e1ace973c8cf'
if(-not (($resources -join "`n").Contains($firebaseId))){throw 'Firebase app ID absent in compiled APK'}
$permissions=@(& ($bt.FullName+'\aapt.exe') dump permissions $apk)
$adPermissions=@('com.google.android.gms.permission.AD_ID','android.permission.ACCESS_ADSERVICES_ATTRIBUTION','android.permission.ACCESS_ADSERVICES_AD_ID')
foreach($permission in $adPermissions){if(($permissions -join "`n").Contains($permission)){throw ('Unwanted advertising permission: '+$permission)}}
$manifest=@(& ($bt.FullName+'\aapt.exe') dump xmltree $apk AndroidManifest.xml)
$flags=@('firebase_analytics_collection_enabled','google_analytics_default_allow_analytics_storage','google_analytics_default_allow_ad_storage','google_analytics_default_allow_ad_user_data','google_analytics_default_allow_ad_personalization_signals','google_analytics_adid_collection_enabled')
foreach($flag in $flags){$line=($manifest | Select-String ('="'+$flag+'"') -Context 0,1);if(!$line -or $line.Context.PostContext[0] -notmatch '0x0$'){throw ('Unsafe default: '+$flag)}}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead($apk)
try{$dartAbis=@($zip.Entries | Where-Object {$_.FullName -match '^lib/[^/]+/libapp.so$'} | ForEach-Object {($_.FullName -split '/')[1]})}finally{$zip.Dispose()}
$evidence=[ordered]@{version_name='0.5.0';version_code=7;package='tn.tunibiz.tunibiz_mobile';file_name=(Split-Path $apk -Leaf);bytes=(Get-Item $apk).Length;sha256=(Get-FileHash $apk -Algorithm SHA256).Hash.ToLower();certificate_sha256=$cert;signature_verified=$true;advertising_permissions_absent=$true;firebase_app_id=$firebaseId;firebase_app_id_present_in_apk=$true;analytics_defaults_disabled=$flags;dart_abis=$dartAbis;flutter_tests_passed=26;physical_device_tested=$false;published=$false;production_deployed=$false}
$json=$evidence | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText((Join-Path $repo 'docs\pilot050\apk-candidate.json'),$json,(New-Object Text.UTF8Encoding($false)))
[IO.File]::WriteAllText((Join-Path $DevRoot 'pilot050-apk-candidate.json'),$json,(New-Object Text.UTF8Encoding($false)))
$json

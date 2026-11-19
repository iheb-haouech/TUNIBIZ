param([string]$DevRoot='E:\TUNIBIZ-Dev')
$ErrorActionPreference='Stop'
# Windows PowerShell reports native stderr as errors even for successful tools.
function Invoke-Native {
 param([string]$Executable,[string[]]$Arguments)
 $prior=$ErrorActionPreference
 try { $ErrorActionPreference='Continue'; & $Executable @Arguments; $code=$LASTEXITCODE }
 finally { $ErrorActionPreference=$prior }
 if($code -ne 0){throw ('Native tool failed with exit code '+$code)}
}
$src=Join-Path $PSScriptRoot 'mobile'
$work=Join-Path $DevRoot 'apk-work'
$keydir=Join-Path $env:LOCALAPPDATA 'TUNIBIZ\Signing'
$store=Join-Path $keydir 'tunibiz-release.p12'
$passwordFile=Join-Path $keydir 'password.dpapi'
if(!(Test-Path $store) -or !(Test-Path $passwordFile)){throw 'Existing permanent signing key and protected password are required.'}
$env:PUB_CACHE=Join-Path $DevRoot 'pub-cache'
$env:GRADLE_USER_HOME=Join-Path $DevRoot 'gradle'
$env:TEMP=Join-Path $DevRoot 'temp';$env:TMP=$env:TEMP
$env:ANDROID_HOME=Join-Path $env:LOCALAPPDATA 'Android\Sdk'
$env:ANDROID_USER_HOME=Join-Path $DevRoot 'android-user'
$ndk=Join-Path $env:ANDROID_HOME 'ndk\28.2.13676358'
if(!(Test-Path (Join-Path $ndk 'source.properties')) -or !(Test-Path (Join-Path $ndk 'toolchains\llvm\prebuilt\windows-x86_64\bin\clang.exe'))){throw 'Install the complete official Android NDK 28.2.13676358 before compiling this pilot.'}
$env:JAVA_HOME='C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot'
[Environment]::SetEnvironmentVariable('ProgramFiles(x86)','C:\Program Files (x86)','Process')
$flutter=Join-Path $DevRoot 'flutter\bin\flutter.bat'
Set-Location $src
Invoke-Native $flutter @('analyze','--no-fatal-infos')
if($LASTEXITCODE -ne 0){throw 'Static analysis failed'}
Invoke-Native $flutter @('test','--reporter','expanded')
if($LASTEXITCODE -ne 0){throw 'Flutter tests failed'}
Copy-Item "$src\lib\*" "$work\lib" -Force
Copy-Item "$src\test\*" "$work\test" -Force
Copy-Item "$src\assets\*" "$work\assets" -Force
Copy-Item "$src\pubspec.yaml","$src\pubspec.lock" $work -Force
Copy-Item "$src\android\app\src\*" "$work\android\app\src" -Recurse -Force
Copy-Item "$src\android\app\build.gradle.kts" "$work\android\app\build.gradle.kts" -Force
Copy-Item "$src\android\settings.gradle.kts" "$work\android\settings.gradle.kts" -Force
$firebaseFile=Join-Path $DevRoot 'firebase-google-services.json'
if(!(Test-Path $firebaseFile)){throw 'The existing Firebase Android configuration is required.'}
$firebase=Get-Content $firebaseFile -Raw | ConvertFrom-Json
$firebaseClient=$firebase.client | Where-Object {$_.client_info.android_client_info.package_name -eq 'tn.tunibiz.tunibiz_mobile'} | Select-Object -First 1
if($firebase.project_info.project_id -ne 'tunibiz-782f0' -or !$firebaseClient){throw 'Firebase project/package mismatch'}
Copy-Item $firebaseFile "$work\android\app\google-services.json" -Force
$definesFile=Join-Path $DevRoot 'firebase-pilot-defines.json'
$firebaseDefines=@{FIREBASE_APP_ID=$firebaseClient.client_info.mobilesdk_app_id;FIREBASE_API_KEY=$firebaseClient.api_key[0].current_key;FIREBASE_PROJECT_ID=$firebase.project_info.project_id;FIREBASE_SENDER_ID=$firebase.project_info.project_number;FIREBASE_STORAGE_BUCKET=$firebase.project_info.storage_bucket}
[IO.File]::WriteAllText($definesFile,($firebaseDefines | ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
Set-Location $work
Invoke-Native $flutter @('pub','get','--offline')
if($LASTEXITCODE -ne 0){throw 'Dependency setup failed'}
$pointer=[IntPtr]::Zero
try{
 $secure=Get-Content $passwordFile -Raw | ConvertTo-SecureString
 $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
 $env:TUNIBIZ_SIGN_PASSWORD=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
 $env:TUNIBIZ_SIGN_KEY_PASSWORD=$env:TUNIBIZ_SIGN_PASSWORD
 $env:TUNIBIZ_SIGN_STORE=$store
 $env:TUNIBIZ_SIGN_ALIAS='tunibiz'
 Invoke-Native $flutter @('build','apk','--release','--no-pub','--target-platform','android-arm64','--dart-define=API_BASE=https://ihebhaouech.pythonanywhere.com',('--dart-define-from-file='+$definesFile))
 if($LASTEXITCODE -ne 0){throw 'Native release compilation failed'}
 $apk=Join-Path $work 'build\app\outputs\flutter-apk\app-release.apk'
 $bt=Get-ChildItem "$env:ANDROID_HOME\build-tools" -Directory | Where-Object {Test-Path ($_.FullName+'\apksigner.bat')} | Sort-Object Name -Descending | Select-Object -First 1
 & ($bt.FullName+'\apksigner.bat') verify --verbose --print-certs $apk
 if($LASTEXITCODE -ne 0){throw 'Signature verification failed'}
 $out=Join-Path $DevRoot 'TUNIBIZ-v0.5.0-pilot-candidate.apk'
 if(Test-Path $out){throw 'Candidate already exists; refusing overwrite'}
 Copy-Item $apk $out
 Get-FileHash $out -Algorithm SHA256 | Select-Object Hash,Path
 & ($bt.FullName+'\aapt.exe') dump badging $out | Select-String 'package:|sdkVersion:|native-code:'
}finally{
 if($pointer -ne [IntPtr]::Zero){[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)}
 Remove-Item Env:TUNIBIZ_SIGN_PASSWORD,Env:TUNIBIZ_SIGN_KEY_PASSWORD -ErrorAction SilentlyContinue
}

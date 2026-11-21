param([ValidateSet('debug','release')][string]$Mode='release')
$ErrorActionPreference='Stop'
$dev='E:\TUNIBIZ-Dev'
$out=if($env:TUNIBIZ_OUTPUT_DIR){$env:TUNIBIZ_OUTPUT_DIR}else{"$dev\v060"}
New-Item -ItemType Directory -Force $out | Out-Null
$src=Split-Path $PSScriptRoot
$work=Join-Path $dev 'apk-work-060'
function Native([string]$exe,[string[]]$arguments){
 $prior=$ErrorActionPreference
 try{$ErrorActionPreference='Continue';& $exe @arguments;$result=$LASTEXITCODE}finally{$ErrorActionPreference=$prior}
 if($result -ne 0){throw "Tool exited $result"}
}
$env:PUB_CACHE="$dev\pub-cache";$env:GRADLE_USER_HOME="$dev\gradle"
$env:TEMP="$dev\temp";$env:TMP=$env:TEMP
$env:ANDROID_HOME=Join-Path $env:LOCALAPPDATA 'Android\Sdk'
$env:ANDROID_USER_HOME="$dev\android-user"
$env:JAVA_HOME='C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot'
[Environment]::SetEnvironmentVariable('ProgramFiles(x86)','C:\Program Files (x86)','Process')
New-Item -ItemType Directory -Force $work | Out-Null
& robocopy $src $work /E /XD build .dart_tool .gradle /XF local.properties key.properties /NFL /NDL /NJH /NJS | Out-Null
if($LASTEXITCODE -gt 7){throw 'Source copy failed'}
# Bound memory/parallelism on SPYKY; source behavior is unchanged.
[IO.File]::WriteAllText("$work\android\gradle.properties","org.gradle.jvmargs=-Xmx3G -XX:MaxMetaspaceSize=1G -XX:ReservedCodeCacheSize=256m`norg.gradle.workers.max=1`norg.gradle.parallel=false`nandroid.useAndroidX=true`nandroid.newDsl=false`nandroid.builtInKotlin=false`n",(New-Object Text.UTF8Encoding($false)))
# Do not carry the instrumentation plugin/registrant from the QA APK into release.
# The source retains integration_test; only the disposable release work copy excludes it.
if($Mode -eq 'release'){
 $specPath="$work\pubspec.yaml"
 $spec=[IO.File]::ReadAllText($specPath) -replace '(?m)^  integration_test:\r?\n    sdk: flutter\r?\n',''
 [IO.File]::WriteAllText($specPath,$spec,(New-Object Text.UTF8Encoding($false)))
 Remove-Item "$work\.flutter-plugins-dependencies","$work\android\app\src\main\java\io\flutter\plugins\GeneratedPluginRegistrant.java" -Force -ErrorAction SilentlyContinue
}
$firebase=Get-Content "$dev\firebase-google-services.json" -Raw | ConvertFrom-Json
$fc=$firebase.client | Where-Object {$_.client_info.android_client_info.package_name -eq 'tn.tunibiz.tunibiz_mobile'} | Select-Object -First 1
if($firebase.project_info.project_id -ne 'tunibiz-782f0' -or !$fc){throw 'Firebase package/project mismatch'}
Copy-Item "$dev\firebase-google-services.json" "$work\android\app\google-services.json" -Force
$defines=@{FIREBASE_APP_ID=$fc.client_info.mobilesdk_app_id;FIREBASE_API_KEY=$fc.api_key[0].current_key;FIREBASE_PROJECT_ID=$firebase.project_info.project_id;FIREBASE_SENDER_ID=$firebase.project_info.project_number;FIREBASE_STORAGE_BUCKET=$firebase.project_info.storage_bucket}
$definesFile="$out\firebase-public-defines.json"
[IO.File]::WriteAllText($definesFile,($defines|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
$flutter="$dev\flutter\bin\flutter.bat"
Set-Location $work
Native $flutter @('pub','get','--offline')
if($Mode -eq 'debug'){
 Native $flutter @('build','apk','--debug','--no-pub','--target','integration_test/mobile_flow_test.dart','--target-platform','android-x64',("--dart-define-from-file="+$definesFile))
 Copy-Item "$work\build\app\outputs\flutter-apk\app-debug.apk" "$out\TUNIBIZ-v060-qa-debug.apk" -Force
 exit
}
$keydir=Join-Path $env:LOCALAPPDATA 'TUNIBIZ\Signing'
$ptr=[IntPtr]::Zero
try{
 $secure=Get-Content "$keydir\password.dpapi" -Raw | ConvertTo-SecureString
 $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
 $env:TUNIBIZ_SIGN_PASSWORD=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
 $env:TUNIBIZ_SIGN_KEY_PASSWORD=$env:TUNIBIZ_SIGN_PASSWORD
 $env:TUNIBIZ_SIGN_STORE="$keydir\tunibiz-release.p12";$env:TUNIBIZ_SIGN_ALIAS='tunibiz'
 Native $flutter @('build','apk','--release','--no-pub','--target-platform','android-arm,android-arm64,android-x64','--dart-define=API_BASE=https://ihebhaouech.pythonanywhere.com',("--dart-define-from-file="+$definesFile))
 Copy-Item "$work\build\app\outputs\flutter-apk\app-release.apk" "$out\TUNIBIZ-v0.6.0-universal.apk" -Force
}finally{
 if($ptr -ne [IntPtr]::Zero){[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
 Remove-Item Env:TUNIBIZ_SIGN_PASSWORD,Env:TUNIBIZ_SIGN_KEY_PASSWORD -ErrorAction SilentlyContinue
}

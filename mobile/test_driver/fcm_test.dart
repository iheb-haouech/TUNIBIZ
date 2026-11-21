import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:integration_test/integration_test_driver_extended.dart';
const adb='C:/Users/Administrateur/AppData/Local/Android/Sdk/platform-tools/adb.exe',pkg='tn.tunibiz.tunibiz_mobile';
const root='/data/user/0/tn.tunibiz.tunibiz_mobile/cache/qa';
Future<ProcessResult> shell(List<String> a)=>Process.run(adb,['-s','emulator-5560','shell',...a]);
Future<void> main()async{
 final out=Directory(Platform.environment['TUNIBIZ_OUTPUT_DIR']??'E:/TUNIBIZ-Dev/v060-final');
 var running=true,last='';final proof=<String,dynamic>{'device':'emulator-5560','physical':false};
 await shell(['pm','grant',pkg,'android.permission.POST_NOTIFICATIONS']);
 Future<void> watch()async{while(running){
  final raw=(await shell(['run-as',pkg,'cat','$root/qa-fcm-stage'])).stdout.toString().trim();
  if(raw.isNotEmpty&&raw!=last){
   try{
    final d=jsonDecode(raw) as Map;final run=d['run'],phase=d['phase'];var ok=false;
    if(phase=='background'){await shell(['input','keyevent','3']);ok=true;}
    else if(phase=='foreground'||phase=='inspect_background'){
     for(var i=0;i<30;i++){
      final dump=(await shell(['dumpsys','notification','--noredact'])).stdout.toString();
      ok=phase=='foreground'?dump.split('NotificationRecord(').any((b)=>b.contains('pkg=$pkg')&&b.contains('id=${d['value']} ')&&(b.contains('channel=loyalty')||b.contains('channelId=loyalty'))):dump.contains('tag=qa-fcm-bg-$run');
      if(ok)break;await Future<void>.delayed(const Duration(seconds:1));
     }
     proof[phase]=ok;
     if(phase=='inspect_background'){
      if(ok){await shell(['cmd','statusbar','expand-notifications']);await Future<void>.delayed(const Duration(seconds:1));final pic=await Process.run(adb,['-s','emulator-5560','exec-out','screencap','-p'],stdoutEncoding:null);await Directory('${out.path}/screenshots').create(recursive:true);await File('${out.path}/screenshots/35-fcm-notification-reelle.png').writeAsBytes(pic.stdout as List<int>);await shell(['cmd','statusbar','collapse']);}
      await shell(['am','start','-n','$pkg/.MainActivity']);
     }
    }
    await shell(['run-as',pkg,'touch','$root/qa-fcm-$run-$phase-ack${ok?'':'.failed'}']);last=raw;
    await File('${out.path}/fcm-android-os-proof.json').writeAsString(jsonEncode(proof));
   }on FormatException{/* An atomic stage write may not have completed yet. */}
  }
  await Future<void>.delayed(const Duration(milliseconds:300));
 }}
 unawaited(watch());try{await integrationDriver(writeResponseOnFailure:true);}finally{running=false;}
}

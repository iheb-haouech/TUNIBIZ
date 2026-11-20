import 'dart:io';
import 'dart:async';
import 'package:integration_test/integration_test_driver_extended.dart';
const adb='C:/Users/Administrateur/AppData/Local/Android/Sdk/platform-tools/adb.exe';
const pkg='tn.tunibiz.tunibiz_mobile';
const qaPath='/data/user/0/tn.tunibiz.tunibiz_mobile/cache/qa';
Future<ProcessResult> shell(List<String> args)=>Process.run(adb,['-s','emulator-5560','shell',...args]);
Future<void> network(bool available)async{
 await shell(['cmd','connectivity','airplane-mode',available?'disable':'enable']);
 for(final kind in ['wifi','data']){await shell(['svc',kind,available?'enable':'disable']);}
}
Future<void> main()async{
 final root=Directory('E:/TUNIBIZ-Dev/v060/screenshots');await root.create(recursive:true);
 var running=true,previous='',previousCapture='';
 Future<void> watch()async{
  while(running){
   final result=await shell(['run-as',pkg,'cat','$qaPath/qa-network']);final value=result.stdout.toString().trim();
   if(value!=previous&&(value=='offline'||value=='online')){
    await network(value=='online');previous=value;
    await shell(['run-as',pkg,'touch','$qaPath/qa-network-$value-ack']);
   }
   final capture=(await shell(['run-as',pkg,'cat','$qaPath/qa-capture'])).stdout.toString().trim();
   if(capture!=previousCapture&&RegExp(r'^[0-9]{2}[a-z]?-[a-z0-9-]+$').hasMatch(capture)){
    final bytes=await Process.run(adb,['-s','emulator-5560','exec-out','run-as',pkg,'cat','$qaPath/screenshots/$capture.png'],stdoutEncoding:null);
    if(bytes.exitCode==0&&(bytes.stdout as List<int>).length>8&&(bytes.stdout as List<int>)[0]==137&&(bytes.stdout as List<int>)[1]==80){await File('${root.path}/$capture.png').writeAsBytes(bytes.stdout as List<int>);previousCapture=capture;await shell(['run-as',pkg,'touch','$qaPath/qa-capture-$capture-ack']);}
   }
   await Future<void>.delayed(const Duration(milliseconds:300));
  }
 }
 await shell(['pm','grant',pkg,'android.permission.CAMERA']);
 await shell(['pm','grant',pkg,'android.permission.POST_NOTIFICATIONS']);
 unawaited(watch());
 try{await integrationDriver(onScreenshot:(name,bytes,[args])async{return true;},writeResponseOnFailure:true);}
 finally{running=false;await network(true);}
}

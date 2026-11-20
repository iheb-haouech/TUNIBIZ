import 'dart:io';
import 'dart:async';
import 'package:integration_test/integration_test_driver_extended.dart';
const adb='C:/Users/Administrateur/AppData/Local/Android/Sdk/platform-tools/adb.exe';
Future<ProcessResult> shell(List<String> args)=>Process.run(adb,['-s','emulator-5560','shell',...args]);
Future<void> network(bool available)async{
 await shell(['cmd','connectivity','airplane-mode',available?'disable':'enable']);
 for(final kind in ['wifi','data']){await shell(['svc',kind,available?'enable':'disable']);}
}
Future<void> main()async{
 final root=Directory('E:/TUNIBIZ-Dev/v060/screenshots');await root.create(recursive:true);
 var running=true;var previous='';
 const path='/sdcard/Android/data/tn.tunibiz.tunibiz_mobile/files/qa-network';
 Future<void> watch()async{
  while(running){
   final result=await shell(['cat',path]);final value=result.stdout.toString().trim();
   if(value!=previous&&(value=='offline'||value=='online')){
    await network(value=='online');previous=value;
    await shell(['echo -n $value > $path-ack']);
   }
   await Future<void>.delayed(const Duration(milliseconds:500));
  }
 }
 await shell(['pm','grant','tn.tunibiz.tunibiz_mobile','android.permission.CAMERA']);
 await shell(['pm','grant','tn.tunibiz.tunibiz_mobile','android.permission.POST_NOTIFICATIONS']);
 unawaited(watch());
 try{
  await integrationDriver(onScreenshot:(name,bytes,[args])async{await File('${root.path}/$name.png').writeAsBytes(bytes);return true;},writeResponseOnFailure:true);
 }finally{running=false;await network(true);}
}

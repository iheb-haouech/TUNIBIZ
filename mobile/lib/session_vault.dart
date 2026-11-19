import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
class SessionVault{
 static const channel=MethodChannel('tn.tunibiz/private');
 static bool get available=>!kIsWeb&&Platform.isAndroid;
 static Future<String?> read(String scope)async{
 if(!available)return null;
 try{return await channel.invokeMethod<String>('readSession',{'scope':scope});}on PlatformException{return null;}on MissingPluginException{return null;}
 }
 static Future<void> write(String scope,String? value)async{
 if(!available)return;
 try{await channel.invokeMethod<void>('writeSession',{'scope':scope,'value':value});}on PlatformException{ }on MissingPluginException{ }
 }
}

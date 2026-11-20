import 'dart:io';
import 'package:integration_test/integration_test_driver_extended.dart';
Future<void> main()async{
 final root=Directory('E:/TUNIBIZ-Dev/v060/screenshots');await root.create(recursive:true);
 await integrationDriver(onScreenshot:(name,bytes,[args])async{await File('${root.path}/$name.png').writeAsBytes(bytes);return true;});
}

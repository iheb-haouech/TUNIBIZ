import 'app_language.dart';
import 'package:flutter/material.dart';
import 'api.dart';
Future<void> recoverPassword(BuildContext context,String kind,String initialEmail)async{
 String email=initialEmail;
 final result=await showDialog<String>(context:context,builder:(ctx)=>AlertDialog(title:const AppText('Mot de passe oublié ?'),content:Column(mainAxisSize:MainAxisSize.min,children:[const AppText('Recevez un lien temporaire par email. Pour un compte Google, utilisez la récupération Google.'),const SizedBox(height:12),TextFormField(initialValue:email,keyboardType:TextInputType.emailAddress,autocorrect:false,onChanged:(v)=>email=v,decoration:const AppInputDecoration(labelText:'Email'))]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const AppText('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,email.trim()),child:const AppText('Envoyer'))]));
 if(result==null||!context.mounted)return;
 final api=Api();String message;
 try{await api.init();final r=await api.call('/password/request',{'kind':kind,'email':result});message=r['message'].toString();}catch(e){message=e.toString().replaceFirst('Exception: ','');}finally{api.close();}
 if(context.mounted)await showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:const AppText('Récupération de compte'),content:AppText(message),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const AppText('Fermer'))]));
}

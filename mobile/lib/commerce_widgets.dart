import 'app_language.dart';
import 'package:flutter/material.dart';
import 'premium.dart';

String commerceKey()=>DateTime.now().microsecondsSinceEpoch.toString()+UniqueKey().toString().replaceAll(RegExp('[^a-zA-Z0-9]'),'');
String commerceDate()=>DateTime.now().toUtc().add(const Duration(hours:1)).toIso8601String().substring(0,10);
String commerceEnd()=>DateTime.now().add(const Duration(days:30)).toIso8601String().substring(0,10);
const commerceStatus={'draft':'Brouillon','scheduled':'Programmée','active':'Active','expired':'Expirée','suspended':'Suspendue','archived':'Archivée'};
class CommerceField{
 final String keyName,label; final String value;final TextInputType? type;final bool optional; final Map<String,String>? choices;
 const CommerceField(this.keyName,this.label,{this.value='',this.type,this.optional=false,this.choices});
}
Future<Map<String,String>?> commerceForm(BuildContext context,String title,List<CommerceField> fields,{String? note}) async {
 final form=GlobalKey<FormState>();final values=<String,String>{for(final f in fields)f.keyName:f.value};
 return showModalBottomSheet<Map<String,String>>(context:context,isScrollControlled:true,useSafeArea:true,showDragHandle:true,builder:(ctx)=>Padding(padding:EdgeInsets.fromLTRB(22,4,22,MediaQuery.viewInsetsOf(ctx).bottom+22),child:SingleChildScrollView(child:Form(key:form,child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.stretch,children:[AppText(title,style:const TextStyle(fontSize:25,fontWeight:FontWeight.w800,color:ink)),if(note!=null)Padding(padding:const EdgeInsets.symmetric(vertical:12),child:AppText(note,style:const TextStyle(color:muted))),for(final f in fields)Padding(padding:const EdgeInsets.only(top:14),child:f.choices!=null?DropdownButtonFormField<String>(initialValue:f.choices!.containsKey(f.value)?f.value:f.choices!.keys.first,isExpanded:true,decoration:AppInputDecoration(labelText:f.label),items:f.choices!.entries.map((e)=>DropdownMenuItem(value:e.key,child:AppText(e.value))).toList(),onChanged:(v)=>values[f.keyName]=v??'',onSaved:(v)=>values[f.keyName]=v??''):TextFormField(initialValue:f.value,keyboardType:f.type,decoration:AppInputDecoration(labelText:f.label),validator:(v)=>!f.optional&&(v??'').trim().isEmpty?'Champ requis':null,onSaved:(v)=>values[f.keyName]=(v??'').trim())),const SizedBox(height:22),FilledButton(onPressed:(){if(form.currentState!.validate()){form.currentState!.save();Navigator.pop(ctx,values);}},child:const AppText('Valider')),TextButton(onPressed:()=>Navigator.pop(ctx),child:const AppText('Annuler'))])))));
}
Widget commercePanel(Widget child)=>Container(margin:const EdgeInsets.only(bottom:14),padding:const EdgeInsets.all(20),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(22),border:Border.all(color:const Color(0xFFE2EAF3))),child:child);
Widget commerceTitle(String title,[String? subtitle])=>Padding(padding:const EdgeInsets.only(top:8,bottom:20),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[AppText(title,style:const TextStyle(fontSize:28,fontWeight:FontWeight.w800,color:ink,letterSpacing:-.8)),if(subtitle!=null)Padding(padding:const EdgeInsets.only(top:7),child:AppText(subtitle,style:const TextStyle(color:muted)))]));
Widget commerceEmpty(String title,String text)=>commercePanel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Icon(Icons.auto_awesome_outlined,color:cobalt,size:30),const SizedBox(height:14),AppText(title,style:const TextStyle(fontSize:19,fontWeight:FontWeight.w700,color:ink)),const SizedBox(height:8),AppText(text,style:const TextStyle(color:muted))]));

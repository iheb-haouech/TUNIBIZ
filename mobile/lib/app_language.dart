import 'package:flutter/material.dart';
import 'session_vault.dart';
import 'translations.dart';

class AppLanguage {
 static final locale=ValueNotifier(const Locale('fr'));
 static Future<void> restore()async{final code=await SessionVault.read('locale');if(const ['fr','ar','en'].contains(code))locale.value=Locale(code!);}
 static Future<void> select(String code)async{if(!const ['fr','ar','en'].contains(code))return;locale.value=Locale(code);await SessionVault.write('locale',code);}
}
String tr(Object? value){
 final source=value?.toString()??'',language=AppLanguage.locale.value.languageCode;
 if(language=='fr'||source.isEmpty)return source;
 final row=translations[source];if(row!=null)return row[language=='en'?0:1];
 final index=language=='en'?0:1;
 for(final pattern in translatedPatterns){final match=pattern.$1.firstMatch(source);if(match!=null){var result=pattern.$2[index];for(var i=1;i<=match.groupCount;i++){result=result.replaceAll('{$i}',match.group(i)??'');}return result;}}
 return source;
}
class AppText extends StatelessWidget {
 final Object? data;final TextStyle? style;final TextAlign? textAlign;final int? maxLines;final TextOverflow? overflow;final bool? softWrap;final TextDirection? textDirection;
 const AppText(this.data,{super.key,this.style,this.textAlign,this.maxLines,this.overflow,this.softWrap,this.textDirection});
 @override Widget build(BuildContext context){Localizations.localeOf(context);return Text(tr(data),style:style,textAlign:textAlign,maxLines:maxLines,overflow:overflow,softWrap:softWrap,textDirection:textDirection);}
}
class AppInputDecoration extends InputDecoration {
 final String? sourceLabel,sourceHint,sourceHelper,sourceError;
 const AppInputDecoration({String? labelText,String? hintText,String? helperText,String? errorText,super.prefixIcon,super.suffixIcon,super.filled,super.fillColor,super.border,super.contentPadding,super.isDense,super.counterText})
  :sourceLabel=labelText,sourceHint=hintText,sourceHelper=helperText,sourceError=errorText;
 @override String? get labelText=>sourceLabel==null?null:tr(sourceLabel);
 @override String? get hintText=>sourceHint==null?null:tr(sourceHint);
 @override String? get helperText=>sourceHelper==null?null:tr(sourceHelper);
 @override String? get errorText=>sourceError==null?null:tr(sourceError);
}
class AppNavigationDestination extends NavigationDestination {
 final String sourceLabel;
 const AppNavigationDestination({super.key,required super.icon,super.selectedIcon,required String label}):sourceLabel=label,super(label:label);
 @override String get label=>tr(sourceLabel);
}
class LanguagePicker extends StatelessWidget {
 const LanguagePicker({super.key});
 @override Widget build(BuildContext context)=>ValueListenableBuilder<Locale>(valueListenable:AppLanguage.locale,builder:(_,locale,__)=>Wrap(spacing:5,children:[for(final entry in const {'fr':'FR','ar':'العربية','en':'EN'}.entries)ChoiceChip(label:Text(entry.value),selected:locale.languageCode==entry.key,onSelected:(_)=>AppLanguage.select(entry.key),visualDensity:VisualDensity.compact)]));
}

package tn.tunibiz.tunibiz_mobile
import android.app.Activity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ClipData
import android.content.pm.PackageManager
import android.Manifest
import android.os.Build
import androidx.core.content.FileProvider
import java.io.File
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import io.flutter.plugin.common.MethodChannel
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class PrivateBridge(private val context: Context) {
 private var pendingExport:MethodChannel.Result?=null
 private var exportBytes:ByteArray?=null
 fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?){
  if(requestCode!=925)return
  val result=pendingExport;val bytes=exportBytes;pendingExport=null;exportBytes=null
  if(resultCode!=Activity.RESULT_OK||data?.data==null||bytes==null){result?.success(false);return}
  try{context.contentResolver.openOutputStream(data.data!!)?.use{it.write(bytes)}?:throw IllegalStateException();result?.success(true)}catch(_:Exception){result?.error("export","Export indisponible",null)}
 }
 private val alias="tunibiz_session_v1"
 private val prefs=context.getSharedPreferences("tn_private_sessions",Context.MODE_PRIVATE)
 private fun key():SecretKey {
  val ks=KeyStore.getInstance("AndroidKeyStore").apply{load(null)}
  (ks.getKey(alias,null) as? SecretKey)?.let{return it}
  return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore").apply{
   init(KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
  }.generateKey()
 }
 fun attach(channel:MethodChannel){
  channel.setMethodCallHandler{call,result->
   try {
    when(call.method){
     "openExternal"->{
      val url=call.argument<String>("url")?:"";val u=Uri.parse(url)
      val clean=url.length<=1000 && url.none{it.isWhitespace() || it.code<32 || it in "<>\"'\\"}
      val web=clean && u.scheme=="https" && !u.host.isNullOrEmpty() && u.userInfo==null && u.port in setOf(-1,443)
      val phone=Regex("^tel:\\+?[0-9 ()-]{5,30}$").matches(url)
      if(!web&&!phone)result.error("url","Lien invalide",null)
      else{context.startActivity(Intent(Intent.ACTION_VIEW,u).addCategory(Intent.CATEGORY_BROWSABLE).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));result.success(true)}
     }
     "prepareQrImage"->{
      val raw=call.argument<String>("image")?:"";require(raw.length<=2000000)
      val bytes=Base64.decode(raw,Base64.DEFAULT);require(bytes.size>8)
      val file=File(context.cacheDir,"qr-image-input.jpg");file.writeBytes(bytes);result.success(file.absolutePath)
     }
     "shareQr","saveQr"->{
      val raw=call.argument<String>("png")?:"";require(raw.length<=1500000)
      val bytes=Base64.decode(raw,Base64.DEFAULT);require(bytes.size>=8&&bytes[0]==0x89.toByte()&&bytes[1]==0x50.toByte())
      if(call.method=="saveQr"){
       if(pendingExport!=null){result.error("busy","Export en cours",null)}else{
        pendingExport=result;exportBytes=bytes
        (context as Activity).startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("image/png").putExtra(Intent.EXTRA_TITLE,"TUNIBIZ-commerce-QR.png"),925)
       }
      }else{
       val folder=File(context.cacheDir,"public-qr").apply{mkdirs()};val file=File(folder,"TUNIBIZ-commerce-QR.png");file.writeBytes(bytes)
       val uri=FileProvider.getUriForFile(context,context.packageName+".files",file)
       val intent=Intent(Intent.ACTION_SEND).setType("image/png").putExtra(Intent.EXTRA_STREAM,uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
       intent.clipData=ClipData.newUri(context.contentResolver,"TUNIBIZ QR",uri)
       context.startActivity(Intent.createChooser(intent,call.argument<String>("title")?:"TUNIBIZ").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));result.success(true)
      }
     }
     "loyaltyNotice"->{
      val nm=context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
      if(!nm.areNotificationsEnabled()||(Build.VERSION.SDK_INT>=33&&context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED))result.success(false)
      else{
       if(Build.VERSION.SDK_INT>=26)nm.createNotificationChannel(NotificationChannel("loyalty","TUNIBIZ",NotificationManager.IMPORTANCE_DEFAULT))
       val intent=Intent(context,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
       val pending=PendingIntent.getActivity(context,6,intent,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
       val notification=if(Build.VERSION.SDK_INT>=26)Notification.Builder(context,"loyalty") else Notification.Builder(context)
       nm.notify((call.argument<String>("id")?:"loyalty").hashCode(),notification.setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("TUNIBIZ").setContentText(call.argument<String>("body")?:"TUNIBIZ").setVisibility(Notification.VISIBILITY_PRIVATE).setContentIntent(pending).setAutoCancel(true).build());result.success(true)
      }
     }

     "openRelease"->{
      val url=call.argument<String>("url")?:""
      if(!Regex("^https://github\\.com/iheb-haouech/TUNIBIZ/releases/download/v[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}/TUNIBIZ-v[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}(?:-universal)?\\.apk$").matches(url)){result.error("url","Lien invalide",null)}
      else {context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));result.success(true)}
     }
     "readSession","writeSession"->{
      val scope=call.argument<String>("scope")?:""
      if(scope !in setOf("wallet","merchant","legacy","analytics","push_consent","push_device","locale","last_role","wallet_cache","merchant_cache","public_cache","merchant_notifications")){result.error("scope","Scope invalide",null)}
      else if(call.method=="writeSession"){
       val value=call.argument<String>("value")
       if(value==null){prefs.edit().remove(scope).apply();result.success(null)}
       else{
        require(value.length<=if(scope.endsWith("_cache"))262144 else 8192)
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE,key());cipher.updateAAD(scope.toByteArray())
        val encrypted=cipher.iv+cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        prefs.edit().putString(scope,Base64.encodeToString(encrypted,Base64.NO_WRAP)).apply();result.success(null)
       }
      }else{
       val saved=prefs.getString(scope,null)
       if(saved==null)result.success(null)
       else try{
        val bytes=Base64.decode(saved,Base64.NO_WRAP)
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,bytes.copyOfRange(0,12)));cipher.updateAAD(scope.toByteArray())
        result.success(String(cipher.doFinal(bytes.copyOfRange(12,bytes.size)),Charsets.UTF_8))
       }catch(_:Exception){prefs.edit().remove(scope).apply();result.success(null)}
      }
     }
     else->result.notImplemented()
    }
   }catch(_:Exception){result.error("private","Action indisponible",null)}
  }
 }
}

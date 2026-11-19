package tn.tunibiz.tunibiz_mobile
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
     "openRelease"->{
      val url=call.argument<String>("url")?:""
      if(!Regex("^https://github\\.com/iheb-haouech/TUNIBIZ/releases/download/v[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}/TUNIBIZ-v[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.apk$").matches(url)){result.error("url","Lien invalide",null)}
      else {context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));result.success(true)}
     }
     "readSession","writeSession"->{
      val scope=call.argument<String>("scope")?:""
      if(scope !in setOf("wallet","merchant","legacy")){result.error("scope","Scope invalide",null)}
      else if(call.method=="writeSession"){
       val value=call.argument<String>("value")
       if(value==null){prefs.edit().remove(scope).apply();result.success(null)}
       else{
        require(value.length<=8192)
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

package tn.tunibiz.tunibiz_mobile
import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import io.flutter.plugin.common.MethodChannel
import java.io.ByteArrayOutputStream

class StorePhotoPicker(private val activity:Activity){
 private var pending:MethodChannel.Result?=null
 fun attach(channel:MethodChannel){
  channel.setMethodCallHandler{call,result->
   if(call.method!="pick"){result.notImplemented();return@setMethodCallHandler}
   if(pending!=null){result.error("busy","Sélection en cours",null);return@setMethodCallHandler}
   pending=result
   try{activity.startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply{type="image/*";addCategory(Intent.CATEGORY_OPENABLE)},831)}
   catch(e:Exception){pending=null;result.error("photo","Galerie indisponible",null)}
  }
 }
 fun onResult(request:Int,status:Int,data:Intent?):Boolean{
  if(request!=831)return false
  val r=pending;pending=null
  val uri=data?.data
  if(status!=Activity.RESULT_OK||uri==null){r?.success(null);return true}
  Thread{
   try{
    val resolver=activity.contentResolver
    val bounds=BitmapFactory.Options().apply{inJustDecodeBounds=true}
    resolver.openInputStream(uri).use{BitmapFactory.decodeStream(it,null,bounds)}
    require(bounds.outWidth>0&&bounds.outHeight>0&&bounds.outWidth.toLong()*bounds.outHeight<=100000000L)
    var sample=1
    while(maxOf(bounds.outWidth,bounds.outHeight)/sample>1500)sample*=2
    val image=resolver.openInputStream(uri).use{BitmapFactory.decodeStream(it,null,BitmapFactory.Options().apply{inSampleSize=sample})}?:error("photo")
    val ratio=minOf(1f,1000f/maxOf(image.width,image.height))
    val resized=Bitmap.createScaledBitmap(image,maxOf(1,(image.width*ratio).toInt()),maxOf(1,(image.height*ratio).toInt()),true)
    if(resized!==image)image.recycle()
    val out=ByteArrayOutputStream()
    var quality=85
    do{out.reset();resized.compress(Bitmap.CompressFormat.JPEG,quality,out);quality-=10}while(out.size()>240000&&quality>=35)
    resized.recycle();require(out.size()<=240000)
    val encoded=Base64.encodeToString(out.toByteArray(),Base64.NO_WRAP)
    activity.runOnUiThread{r?.success(encoded)}
   }catch(e:Exception){activity.runOnUiThread{r?.error("photo","Photo trop grande ou illisible",null)}}
  }.start()
  return true
 }
}

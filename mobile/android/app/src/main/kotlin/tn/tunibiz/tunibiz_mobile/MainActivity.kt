package tn.tunibiz.tunibiz_mobile
import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity: FlutterActivity() {
 private val photoPicker by lazy { StorePhotoPicker(this) }
 override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?){super.onActivityResult(requestCode,resultCode,data);photoPicker.onResult(requestCode,resultCode,data)}
 private var locationResult: MethodChannel.Result?=null
 private var permissionOnlyResult: MethodChannel.Result?=null
 private var notificationResult: MethodChannel.Result?=null
 private var listener: LocationListener?=null
 private val handler=Handler(Looper.getMainLooper())
 private val lm get()=getSystemService(Context.LOCATION_SERVICE) as LocationManager
 private val nm get()=getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
 private var presented=false
 override fun onResume(){super.onResume();presented=true}
 override fun onPause(){presented=false;if(listener!=null)finishLocation(null);super.onPause()}
 override fun configureFlutterEngine(engine:FlutterEngine){
  super.configureFlutterEngine(engine)
  photoPicker.attach(MethodChannel(engine.dartExecutor.binaryMessenger,"tn.tunibiz/photo"))
  PrivateBridge(this).attach(MethodChannel(engine.dartExecutor.binaryMessenger,"tn.tunibiz/private"))
  MethodChannel(engine.dartExecutor.binaryMessenger,"tn.tunibiz/nearby").setMethodCallHandler{call,result->
   when(call.method){
    "onboardingNeeded"->result.success(!getSharedPreferences("tn_permissions",MODE_PRIVATE).getBoolean("asked",false))
    "onboardingDone"->{getSharedPreferences("tn_permissions",MODE_PRIVATE).edit().putBoolean("asked",true).apply();result.success(true)}
    "permissionLocation"->{
     if(checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED)result.success(true)
     else if(permissionOnlyResult!=null||locationResult!=null)result.success(false)
     else{permissionOnlyResult=result;requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION),73)}
    }
    "position"->{
     if(locationResult!=null){result.error("busy","Recherche en cours",null)}
     else{locationResult=result;if(checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED){requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION),71)}else locate()}
    }
    "permissionNotifications"->{
     if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){
      if(notificationResult!=null){result.success(false)}else{notificationResult=result;requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),72)}
     }else result.success(nm.areNotificationsEnabled())
    }
    "alert"->{
     if(!presented||!nm.areNotificationsEnabled()||(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)){result.success(false)}
     else{
      val id=call.argument<String>("id") ?: ""
      val title=call.argument<String>("title") ?: ""
      val body=call.argument<String>("body") ?: ""
      val day=SimpleDateFormat("yyyy-MM-dd",Locale.US).format(Date())
      val prefs=getSharedPreferences("nearby_limit",MODE_PRIVATE)
      val sent=if(prefs.getString("day","")==day)prefs.getStringSet("sent",emptySet())!!.toMutableSet() else mutableSetOf<String>()
      if(id.isEmpty()||sent.size>=3||sent.contains(id)){result.success(false)}
      else{
       if(Build.VERSION.SDK_INT>=26)nm.createNotificationChannel(NotificationChannel("nearby","Offres Nearby",NotificationManager.IMPORTANCE_DEFAULT))
       val intent=Intent(this,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
       val pending=PendingIntent.getActivity(this,0,intent,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
       val builder=if(Build.VERSION.SDK_INT>=26)Notification.Builder(this,"nearby") else Notification.Builder(this)
       nm.notify(id.hashCode(),builder.setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle(title).setContentText(body).setStyle(Notification.BigTextStyle().bigText(body)).setContentIntent(pending).setAutoCancel(true).build())
       sent.add(id);prefs.edit().putString("day",day).putStringSet("sent",sent).apply();result.success(true)
      }
     }
    }
    else->result.notImplemented()
   }
  }
 }
 private fun locate(){
  try{
   if(!lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)){finishLocation(null);return}
   val last=lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
   if(last!=null && System.currentTimeMillis()-last.time<60000){finishLocation(last);return}
   val l=object:LocationListener{
    override fun onLocationChanged(loc:Location){finishLocation(loc)}
    override fun onProviderEnabled(provider:String){}
    override fun onProviderDisabled(provider:String){finishLocation(null)}
    override fun onStatusChanged(provider:String?,status:Int,extras:Bundle?){}
   }
   listener=l
   lm.requestLocationUpdates(LocationManager.NETWORK_PROVIDER,0L,0f,l,Looper.getMainLooper())
   handler.postDelayed({if(listener===l)finishLocation(null)},12000)
  }catch(e:Exception){finishLocation(null)}
 }
 private fun finishLocation(loc:Location?){
  listener?.let{lm.removeUpdates(it)};listener=null
  val r=locationResult;locationResult=null
  if(loc==null)r?.error("location","Position approximative indisponible",null)
  else r?.success(mapOf("lat" to loc.latitude,"lon" to loc.longitude,"accuracy" to loc.accuracy.toDouble()))
 }
 override fun onRequestPermissionsResult(requestCode:Int,permissions:Array<out String>,grantResults:IntArray){
  super.onRequestPermissionsResult(requestCode,permissions,grantResults)
  if(requestCode==71){if(grantResults.firstOrNull()==PackageManager.PERMISSION_GRANTED)locate()else finishLocation(null)}
  if(requestCode==73){permissionOnlyResult?.success(grantResults.firstOrNull()==PackageManager.PERMISSION_GRANTED);permissionOnlyResult=null}
  if(requestCode==72){notificationResult?.success(grantResults.firstOrNull()==PackageManager.PERMISSION_GRANTED && nm.areNotificationsEnabled());notificationResult=null}
 }
}

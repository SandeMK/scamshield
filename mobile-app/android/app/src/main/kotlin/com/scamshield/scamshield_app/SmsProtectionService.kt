package com.scamshield.scamshield_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.telephony.SmsManager
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import android.Manifest
import android.content.pm.PackageManager
import io.flutter.embedding.engine.FlutterEngineCache
import io.flutter.plugin.common.MethodChannel

/**
 * Foreground service that keeps the process (and so the Flutter engine and
 * the scamshield/sms receiver registered in [ScamShieldApp]) alive when the
 * activity is swiped away, so incoming SMS keep being scanned.
 */
class SmsProtectionService : Service() {

    companion object {
        private const val PROTECTION_CHANNEL_ID = "scamshield_protection"
        private const val ALERT_CHANNEL_ID = "scamshield_alerts"
        private const val FGS_NOTIFICATION_ID = 1

        fun postAlertNotification(context: Context, title: String, body: String) {
            val nm = context.getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            val notification = NotificationCompat.Builder(context, ALERT_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle(title)
                .setContentText(body)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .build()
            nm.notify(System.currentTimeMillis().toInt(), notification)
        }

        /** 67-char parts (UCS-2 multipart limit), never splitting a surrogate pair. */
        private fun splitUcs2(text: String): ArrayList<String> {
            val parts = ArrayList<String>()
            var start = 0
            while (start < text.length) {
                var end = minOf(start + 67, text.length)
                if (end < text.length && Character.isHighSurrogate(text[end - 1])) end--
                parts.add(text.substring(start, end))
                start = end
            }
            return parts
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        startForeground(FGS_NOTIFICATION_ID, buildForegroundNotification())
        setupChannels()
    }

    private fun createNotificationChannels() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(
            NotificationChannel(
                PROTECTION_CHANNEL_ID,
                "Protection Status",
                NotificationManager.IMPORTANCE_LOW
            ).apply { description = "Persistent protection indicator" }
        )
        nm.createNotificationChannel(
            NotificationChannel(
                ALERT_CHANNEL_ID,
                "Scam Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply { description = "High-risk SMS alerts" }
        )
    }

    private fun buildForegroundNotification(): Notification {
        val launchIntent = packageManager.getLaunchIntentForPackage(packageName)
        val pi = PendingIntent.getActivity(
            this, 0, launchIntent, PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, PROTECTION_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .setContentTitle("ScamShield is protecting you")
            .setContentText("Monitoring incoming messages")
            .setOngoing(true)
            .setContentIntent(pi)
            .build()
    }

    private fun setupChannels() {
        val engine = FlutterEngineCache.getInstance().get(ScamShieldApp.ENGINE_ID) ?: return
        val messenger = engine.dartExecutor.binaryMessenger

        // Notify MethodChannel — Dart calls this to post alert notifications
        // and (FR-09) to fire the automatic Guardian Alert SMS. Registered on
        // the Service, not the Activity, so it keeps working when the app
        // has been swiped away and only the foreground service is alive.
        MethodChannel(messenger, "scamshield/notify").setMethodCallHandler { call, result ->
            when (call.method) {
                "alert" -> {
                    val title = call.argument<String>("title") ?: "Scam detected"
                    val body = call.argument<String>("body") ?: ""
                    postAlertNotification(this, title, body)
                    result.success(null)
                }
                "guardianAlert" -> {
                    val number = call.argument<String>("number")
                    val message = call.argument<String>("message")
                    if (number.isNullOrBlank() || message.isNullOrBlank()) {
                        result.success(false)
                    } else if (ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS)
                        != PackageManager.PERMISSION_GRANTED
                    ) {
                        result.success(false) // FR-09: no permission -> silently skip, never crash scoring
                    } else {
                        @Suppress("DEPRECATION")
                        val smsManager = SmsManager.getDefault()
                        // divideMessage() throws SecurityException on some
                        // devices (Samsung S938B, Android 16) for non-GSM-7
                        // text: its Unicode path calls getGroupIdLevel1, which
                        // needs READ_PHONE_STATE. Fall back to UCS-2-sized parts.
                        val parts = try {
                            smsManager.divideMessage(message)
                        } catch (e: SecurityException) {
                            splitUcs2(message)
                        }
                        smsManager.sendMultipartTextMessage(number, null, parts, null, null)
                        result.success(true)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int =
        START_STICKY

    override fun onBind(intent: Intent?): IBinder? = null

}

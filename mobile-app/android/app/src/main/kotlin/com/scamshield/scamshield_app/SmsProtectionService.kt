package com.scamshield.scamshield_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.IBinder
import android.provider.Telephony
import androidx.core.app.NotificationCompat
import io.flutter.embedding.engine.FlutterEngineCache
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

/**
 * Foreground service that keeps the Flutter engine alive when the activity
 * is swiped away, so the scamshield/sms EventChannel continues receiving
 * incoming SMS broadcasts.
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
    }

    private var receiver: BroadcastReceiver? = null

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

        // SMS EventChannel — registered on Service context so it survives activity death
        EventChannel(messenger, "scamshield/sms").setStreamHandler(
            object : EventChannel.StreamHandler {
                override fun onListen(args: Any?, events: EventChannel.EventSink?) {
                    receiver = object : BroadcastReceiver() {
                        override fun onReceive(context: Context?, intent: Intent?) {
                            val messages =
                                Telephony.Sms.Intents.getMessagesFromIntent(intent)
                            val body =
                                messages.joinToString("") { it.messageBody ?: "" }
                            val sender =
                                messages.firstOrNull()?.originatingAddress ?: "unknown"
                            events?.success(mapOf("sender" to sender, "body" to body))
                        }
                    }
                    registerReceiver(
                        receiver,
                        IntentFilter(Telephony.Sms.Intents.SMS_RECEIVED_ACTION)
                    )
                }

                override fun onCancel(args: Any?) {
                    receiver?.let { unregisterReceiver(it) }
                    receiver = null
                }
            }
        )

        // Notify MethodChannel — Dart calls this to post alert notifications
        MethodChannel(messenger, "scamshield/notify").setMethodCallHandler { call, result ->
            if (call.method == "alert") {
                val title = call.argument<String>("title") ?: "Scam detected"
                val body = call.argument<String>("body") ?: ""
                postAlertNotification(this, title, body)
                result.success(null)
            } else {
                result.notImplemented()
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int =
        START_STICKY

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        receiver?.let { unregisterReceiver(it) }
        super.onDestroy()
    }
}

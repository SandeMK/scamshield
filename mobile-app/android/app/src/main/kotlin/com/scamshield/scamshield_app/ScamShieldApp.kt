package com.scamshield.scamshield_app

import android.annotation.SuppressLint
import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.provider.Settings
import android.provider.Telephony
import java.security.MessageDigest
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.FlutterEngineCache
import io.flutter.embedding.engine.dart.DartExecutor
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class ScamShieldApp : Application() {
    companion object {
        const val ENGINE_ID = "scamshield_engine"
        const val SHARE_CHANNEL = "scamshield/share"
        const val SMS_CHANNEL = "scamshield/sms"
        const val DEVICE_CHANNEL = "scamshield/device"
        const val ALERT_TAP_CHANNEL = "scamshield/alert_tap"
        var pendingShareText: String? = null

        /** Scan id from a tapped alert notification, pulled once by Dart.
         *  "" means an alert was tapped but carried no scan id. */
        var pendingOpenScanId: String? = null
    }

    /**
     * Stable anonymous device id: SHA-256 of ANDROID_ID, first 32 hex chars
     * (same shape as the old random id). On Android 8+ ANDROID_ID is scoped
     * to this app's signing key, the user and the device, so it survives an
     * uninstall/reinstall (a profile reappears by itself) but changes after
     * a factory reset or with a different signing key. Hashing keeps the
     * raw identifier on the phone. Not used for ads or tracking.
     */
    @SuppressLint("HardwareIds")
    private fun stableDeviceId(): String? {
        val androidId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
        if (androidId.isNullOrBlank()) return null
        val digest = MessageDigest.getInstance("SHA-256")
            .digest("scamshield-device:$androidId".toByteArray())
        return digest.joinToString("") { "%02x".format(it) }.take(32)
    }

    override fun onCreate() {
        super.onCreate()
        val engine = FlutterEngine(this)

        // Registered before executeDartEntrypoint so the handler exists
        // no matter how early Dart's initState() calls getInitialText —
        // the pre-warmed isolate can otherwise race ahead of MainActivity.
        MethodChannel(engine.dartExecutor.binaryMessenger, SHARE_CHANNEL)
            .setMethodCallHandler { call, result ->
                if (call.method == "getInitialText") {
                    result.success(pendingShareText)
                    pendingShareText = null
                } else {
                    result.notImplemented()
                }
            }

        // Device id + alert-tap channels: registered before the Dart
        // entrypoint for the same reason as the share channel — DeviceId and
        // RootScaffold may call them before any Activity exists.
        MethodChannel(engine.dartExecutor.binaryMessenger, DEVICE_CHANNEL)
            .setMethodCallHandler { call, result ->
                if (call.method == "getStableId") result.success(stableDeviceId())
                else result.notImplemented()
            }
        MethodChannel(engine.dartExecutor.binaryMessenger, ALERT_TAP_CHANNEL)
            .setMethodCallHandler { call, result ->
                if (call.method == "getPendingScanId") {
                    result.success(pendingOpenScanId)
                    pendingOpenScanId = null
                } else {
                    result.notImplemented()
                }
            }

        // SMS EventChannel — registered here for the same race: RootScaffold's
        // initState() listens immediately, and when the handler only appeared
        // once SmsProtectionService started, that listen failed silently and
        // no SMS was ever scanned on a cold start. The receiver lives on the
        // Application context; the foreground service keeps the process (and
        // so the receiver) alive after the activity is swiped away.
        EventChannel(engine.dartExecutor.binaryMessenger, SMS_CHANNEL).setStreamHandler(
            object : EventChannel.StreamHandler {
                private var receiver: BroadcastReceiver? = null

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

        engine.dartExecutor.executeDartEntrypoint(
            DartExecutor.DartEntrypoint.createDefault()
        )
        FlutterEngineCache.getInstance().put(ENGINE_ID, engine)
    }
}

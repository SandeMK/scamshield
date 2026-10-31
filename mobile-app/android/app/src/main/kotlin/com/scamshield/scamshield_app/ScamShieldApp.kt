package com.scamshield.scamshield_app

import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.provider.Telephony
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
        var pendingShareText: String? = null
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

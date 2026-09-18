package com.scamshield.scamshield_app

import android.app.Application
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.FlutterEngineCache
import io.flutter.embedding.engine.dart.DartExecutor
import io.flutter.plugin.common.MethodChannel

class ScamShieldApp : Application() {
    companion object {
        const val ENGINE_ID = "scamshield_engine"
        const val SHARE_CHANNEL = "scamshield/share"
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

        engine.dartExecutor.executeDartEntrypoint(
            DartExecutor.DartEntrypoint.createDefault()
        )
        FlutterEngineCache.getInstance().put(ENGINE_ID, engine)
    }
}

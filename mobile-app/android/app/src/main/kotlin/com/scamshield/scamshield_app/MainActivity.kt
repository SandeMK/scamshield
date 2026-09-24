package com.scamshield.scamshield_app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngineCache
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    companion object {
        private const val SEND_SMS_REQUEST_CODE = 101
    }

    private var pendingSendSmsResult: MethodChannel.Result? = null

    override fun getCachedEngineId(): String = ScamShieldApp.ENGINE_ID

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleShareIntent(intent)
        setupGuardianChannel()
    }

    // FR-09: SEND_SMS is requested only when the user opts in to Guardian
    // Alert from Settings, never at first launch alongside RECEIVE_SMS.
    private fun setupGuardianChannel() {
        val engine = FlutterEngineCache.getInstance().get(ScamShieldApp.ENGINE_ID) ?: return
        MethodChannel(engine.dartExecutor.binaryMessenger, "scamshield/guardian")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "hasSendSmsPermission" -> result.success(hasSendSmsPermission())
                    "requestSendSmsPermission" -> {
                        if (hasSendSmsPermission()) {
                            result.success(true)
                        } else {
                            pendingSendSmsResult = result
                            ActivityCompat.requestPermissions(
                                this, arrayOf(Manifest.permission.SEND_SMS), SEND_SMS_REQUEST_CODE
                            )
                        }
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun hasSendSmsPermission() =
        ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS) ==
            PackageManager.PERMISSION_GRANTED

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == SEND_SMS_REQUEST_CODE) {
            pendingSendSmsResult?.success(hasSendSmsPermission())
            pendingSendSmsResult = null
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleShareIntent(intent)
    }

    // Some senders (e.g. Messages, due to this Activity's empty taskAffinity)
    // launch a fresh Activity instance — onCreate, not onNewIntent — even
    // though the process and its Dart isolate are already warm and will
    // never call initState() again. So onCreate must push too, not just
    // stash the text for a pull that may never happen.
    private fun handleShareIntent(intent: Intent?) {
        val text = extractShareText(intent) ?: return
        ScamShieldApp.pendingShareText = text
        FlutterEngineCache.getInstance().get(ScamShieldApp.ENGINE_ID)?.let { engine ->
            MethodChannel(engine.dartExecutor.binaryMessenger, ScamShieldApp.SHARE_CHANNEL)
                .invokeMethod("onShare", null)
        }
    }

    private fun extractShareText(intent: Intent?): String? {
        if (intent == null) return null
        return when (intent.action) {
            Intent.ACTION_SEND -> {
                if (intent.type != "text/plain") return null
                val text = intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString() ?: return null
                val subject = intent.getCharSequenceExtra(Intent.EXTRA_SUBJECT)?.toString()
                if (!subject.isNullOrBlank()) "$subject\n$text" else text
            }
            Intent.ACTION_PROCESS_TEXT ->
                intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString()
            else -> null
        }
    }

    override fun onResume() {
        super.onResume()
        requestSmsPermissionIfNeeded()
        startForegroundService(Intent(this, SmsProtectionService::class.java))
        promptBatteryOptimizationOnce()
    }

    private fun requestSmsPermissionIfNeeded() {
        val perms = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS)
            != PackageManager.PERMISSION_GRANTED
        ) perms.add(Manifest.permission.RECEIVE_SMS)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) perms.add(Manifest.permission.POST_NOTIFICATIONS)

        if (perms.isNotEmpty())
            ActivityCompat.requestPermissions(this, perms.toTypedArray(), 100)
    }

    private fun promptBatteryOptimizationOnce() {
        val prefs = getSharedPreferences("scamshield_prefs", MODE_PRIVATE)
        if (prefs.getBoolean("battery_prompt_shown", false)) return
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        if (!pm.isIgnoringBatteryOptimizations(packageName)) {
            startActivity(
                Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                    data = Uri.parse("package:$packageName")
                }
            )
            prefs.edit().putBoolean("battery_prompt_shown", true).apply()
        }
    }
}

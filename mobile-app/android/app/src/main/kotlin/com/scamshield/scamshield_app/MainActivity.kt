package com.scamshield.scamshield_app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {

    override fun getCachedEngineId(): String = ScamShieldApp.ENGINE_ID

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

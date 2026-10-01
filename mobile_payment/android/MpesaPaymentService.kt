// M-Pesa Payment Service
// Handles payment callbacks and transaction monitoring

package com.mpesa.aiagent.payment

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import kotlinx.coroutines.*
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

class MpesaPaymentService : Service() {
    private val TAG = "MpesaPaymentService"
    private val scope = CoroutineScope(Dispatchers.Main + Job())
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "Payment service started")
        intent?.let {
            val checkoutRequestId = it.getStringExtra("checkout_request_id")
            val maxRetries = it.getIntExtra("max_retries", 30)
            if (checkoutRequestId != null) {
                scope.launch {
                    pollPaymentStatus(checkoutRequestId, maxRetries)
                }
            }
        }
        return START_STICKY
    }

    private suspend fun pollPaymentStatus(checkoutRequestId: String, maxRetries: Int) {
        repeat(maxRetries) { attempt ->
            try {
                val url = "https://your-api.example.com/api/payments/$checkoutRequestId"
                val request = Request.Builder()
                    .url(url)
                    .addHeader("Authorization", "Bearer ${getAuthToken()}")
                    .get()
                    .build()

                val response = httpClient.newCall(request).execute()
                val body = response.body?.string()

                Log.d(TAG, "Payment status check (attempt ${attempt + 1}): $body")

                if (response.isSuccessful && body != null) {
                    val status = parsePaymentStatus(body)
                    when (status) {
                        "paid" -> {
                            Log.d(TAG, "Payment confirmed!")
                            broadcastPaymentConfirmed(checkoutRequestId)
                            return@repeat
                        }
                        "failed" -> {
                            Log.e(TAG, "Payment failed")
                            broadcastPaymentFailed(checkoutRequestId)
                            return@repeat
                        }
                        else -> Log.d(TAG, "Payment status: $status")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error polling payment status: ${e.message}")
            }
            delay(2000) // Wait 2 seconds before next attempt
        }
    }

    private fun getAuthToken(): String {
        // Retrieve from secure storage
        return "your_auth_token"
    }

    private fun parsePaymentStatus(json: String): String {
        return if (json.contains("\"status\":\"paid\"")) "paid"
        else if (json.contains("\"status\":\"failed\"")) "failed"
        else "pending"
    }

    private fun broadcastPaymentConfirmed(checkoutRequestId: String) {
        val intent = Intent("com.mpesa.aiagent.PAYMENT_CONFIRMED")
        intent.putExtra("checkout_id", checkoutRequestId)
        sendBroadcast(intent)
    }

    private fun broadcastPaymentFailed(checkoutRequestId: String) {
        val intent = Intent("com.mpesa.aiagent.PAYMENT_FAILED")
        intent.putExtra("checkout_id", checkoutRequestId)
        sendBroadcast(intent)
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

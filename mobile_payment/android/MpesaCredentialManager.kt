// M-Pesa Android Integration
// Handles mobile payment authorization and callbacks

package com.mpesa.aiagent.payment;

import android.content.Context;
import android.content.SharedPreferences;
import androidx.security.crypto.EncryptedSharedPreferences;
import androidx.security.crypto.MasterKey;
import java.io.IOException;
import java.security.GeneralSecurityException;

public class MpesaCredentialManager {
    private static final String PREFERENCES_NAME = "mpesa_credentials";
    private static final String KEY_CONSUMER_KEY = "consumer_key";
    private static final String KEY_CONSUMER_SECRET = "consumer_secret";
    private static final String KEY_SHORTCODE = "shortcode";
    private static final String KEY_PASSKEY = "passkey";
    private static final String KEY_PHONE_NUMBER = "phone_number";

    private final EncryptedSharedPreferences encryptedPreferences;

    public MpesaCredentialManager(Context context) throws GeneralSecurityException, IOException {
        MasterKey masterKey = new MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build();

        this.encryptedPreferences = EncryptedSharedPreferences.create(
                context,
                PREFERENCES_NAME,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        );
    }

    public void saveCredentials(
            String consumerKey,
            String consumerSecret,
            String shortcode,
            String passkey,
            String phoneNumber
    ) {
        encryptedPreferences.edit()
                .putString(KEY_CONSUMER_KEY, consumerKey)
                .putString(KEY_CONSUMER_SECRET, consumerSecret)
                .putString(KEY_SHORTCODE, shortcode)
                .putString(KEY_PASSKEY, passkey)
                .putString(KEY_PHONE_NUMBER, phoneNumber)
                .apply();
    }

    public String getConsumerKey() {
        return encryptedPreferences.getString(KEY_CONSUMER_KEY, "");
    }

    public String getConsumerSecret() {
        return encryptedPreferences.getString(KEY_CONSUMER_SECRET, "");
    }

    public String getShortcode() {
        return encryptedPreferences.getString(KEY_SHORTCODE, "");
    }

    public String getPasskey() {
        return encryptedPreferences.getString(KEY_PASSKEY, "");
    }

    public String getPhoneNumber() {
        return encryptedPreferences.getString(KEY_PHONE_NUMBER, "");
    }

    public boolean hasCredentials() {
        return !getConsumerKey().isEmpty() && !getConsumerSecret().isEmpty();
    }

    public void clearCredentials() {
        encryptedPreferences.edit().clear().apply();
    }
}

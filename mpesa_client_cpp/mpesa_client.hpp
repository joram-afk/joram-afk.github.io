#include <iostream>
#include <string>
#include <curl/curl.h>
#include <nlohmann/json.hpp>
#include <chrono>
#include <iomanip>
#include <sstream>

using json = nlohmann::json;

class MpesaClient {
private:
    std::string consumer_key;
    std::string consumer_secret;
    std::string shortcode;
    std::string passkey;
    std::string base_url;
    std::string access_token;

public:
    MpesaClient(const std::string& key, const std::string& secret, const std::string& code, const std::string& pk, bool sandbox = true)
        : consumer_key(key), consumer_secret(secret), shortcode(code), passkey(pk) {
        base_url = sandbox ? "https://sandbox.safaricom.co.ke" : "https://api.safaricom.co.ke";
    }

    static size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* userp) {
        userp->append((char*)contents, size * nmemb);
        return size * nmemb;
    }

    bool authenticate() {
        CURL* curl = curl_easy_init();
        if (!curl) return false;

        std::string credentials = consumer_key + ":" + consumer_secret;
        std::string response;

        curl_easy_setopt(curl, CURLOPT_URL, (base_url + "/oauth/v1/generate?grant_type=client_credentials").c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPAUTH, CURLAUTH_BASIC);
        curl_easy_setopt(curl, CURLOPT_USERPWD, credentials.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 25L);

        CURLcode res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK) {
            std::cerr << "Authentication failed: " << curl_easy_strerror(res) << std::endl;
            return false;
        }

        try {
            json j = json::parse(response);
            access_token = j["access_token"];
            return true;
        } catch (const std::exception& e) {
            std::cerr << "Failed to parse auth response: " << e.what() << std::endl;
            return false;
        }
    }

    std::string getTimestamp() const {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::gmtime(&time), "%Y%m%d%H%M%S");
        return ss.str();
    }

    json initiateC2B(const std::string& phone_number, int amount, const std::string& ref) {
        if (access_token.empty() && !authenticate()) {
            return json{{"error", "Authentication failed"}};
        }

        CURL* curl = curl_easy_init();
        if (!curl) return json{{"error", "CURL initialization failed"}};

        std::string response;
        std::string timestamp = getTimestamp();
        
        json payload = {
            {"ShortCode", shortcode},
            {"CommandID", "CustomerPayBillOnline"},
            {"Amount", amount},
            {"Msisdn", phone_number},
            {"BillRefNumber", ref}
        };

        std::string payload_str = payload.dump();
        std::string auth_header = "Authorization: Bearer " + access_token;
        struct curl_slist* headers = NULL;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        headers = curl_slist_append(headers, auth_header.c_str());

        curl_easy_setopt(curl, CURLOPT_URL, (base_url + "/mpesa/c2b/v1/simulate").c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload_str.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);

        CURLcode res = curl_easy_perform(curl);
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK) {
            return json{{"error", std::string(curl_easy_strerror(res))}};
        }

        try {
            return json::parse(response);
        } catch (const std::exception& e) {
            return json{{"error", std::string(e.what())}};
        }
    }

    json queryAccountBalance() {
        if (access_token.empty() && !authenticate()) {
            return json{{"error", "Authentication failed"}};
        }

        CURL* curl = curl_easy_init();
        if (!curl) return json{{"error", "CURL initialization failed"}};

        std::string response;
        std::string timestamp = getTimestamp();
        
        json payload = {
            {"CommandID", "GetAccount"},
            {"ShortCode", shortcode},
            {"IdentifierType", "4"},
            {"Initiator", "testapi"},
            {"SecurityCredential", "encrypted_password"},
            {"QueueTimeOutURL", "https://example.com/timeout"},
            {"ResultURL", "https://example.com/result"}
        };

        std::string payload_str = payload.dump();
        std::string auth_header = "Authorization: Bearer " + access_token;
        struct curl_slist* headers = NULL;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        headers = curl_slist_append(headers, auth_header.c_str());

        curl_easy_setopt(curl, CURLOPT_URL, (base_url + "/mpesa/accountbalance/v1/query").c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload_str.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);

        CURLcode res = curl_easy_perform(curl);
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK) {
            return json{{"error", std::string(curl_easy_strerror(res))}};
        }

        try {
            return json::parse(response);
        } catch (const std::exception& e) {
            return json{{"error", std::string(e.what())}};
        }
    }
};

int main() {
    std::cout << "M-Pesa C++ Client initialized" << std::endl;
    return 0;
}

package com.olascooter.companion;

import android.app.Activity;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.util.UUID;

public class MainActivity extends Activity {

    private static final String TAG = "OlaCompanion";
    private WebView webView;
    private BluetoothGatt bluetoothGatt;

    private static final int PERMISSION_REQUEST_CODE = 1001;
    private static final String DEFAULT_URL = "http://192.168.0.12:5000/dashboard";
    private static final String DEFAULT_MAC = "87:1A:44:60:00:28";

    // Custom Nordic UART / Ola Scooter UUIDs
    private static final UUID OLA_SERVICE_UUID = UUID.fromString("6e400001-b5a3-f393-e0a9-871a44600028");
    private static final UUID OLA_RX_CHAR_UUID = UUID.fromString("6e400002-b5a3-f393-e0a9-e50e24dcca9e");
    private static final UUID CCCD_UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        requestBluetoothPermissions();

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);

        // Native BLE JavaScript Interface for WebView
        webView.addJavascriptInterface(new AndroidBluetoothBridge(), "AndroidScooter");

        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                request.grant(request.getResources());
            }
        });

        webView.loadUrl(DEFAULT_URL);
    }

    public class AndroidBluetoothBridge {
        @JavascriptInterface
        public void connectScooter(String address) {
            final String target = (address != null && !address.trim().isEmpty()) ? address.trim() : DEFAULT_MAC;
            runOnUiThread(() -> connectNativeGatt(target));
        }

        @JavascriptInterface
        public void disconnectScooter() {
            runOnUiThread(() -> disconnectNativeGatt());
        }

        @JavascriptInterface
        public boolean isNativeApp() {
            return true;
        }
    }

    private void connectNativeGatt(String address) {
        Log.i(TAG, "Connecting to scooter via Android Native BLE: " + address);
        try {
            BluetoothManager bm = (BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE);
            if (bm == null || bm.getAdapter() == null) {
                notifyWeb("alert('Bluetooth adapter not available on this phone');");
                return;
            }

            if (bluetoothGatt != null) {
                bluetoothGatt.close();
                bluetoothGatt = null;
            }

            BluetoothDevice device = bm.getAdapter().getRemoteDevice(address);
            bluetoothGatt = device.connectGatt(this, false, gattCallback, BluetoothDevice.TRANSPORT_LE);
        } catch (Exception e) {
            Log.e(TAG, "Native BLE Connect error", e);
            notifyWeb("alert('BLE connect failed: " + e.getMessage() + "');");
        }
    }

    private void disconnectNativeGatt() {
        if (bluetoothGatt != null) {
            try {
                bluetoothGatt.disconnect();
                bluetoothGatt.close();
            } catch (Exception ignored) {}
            bluetoothGatt = null;
        }
        notifyWeb("onNativeBleState(false, '');");
    }

    private final BluetoothGattCallback gattCallback = new BluetoothGattCallback() {
        @Override
        public void onConnectionStateChange(BluetoothGatt gatt, int status, int newState) {
            Log.i(TAG, "GATT State change: status=" + status + " newState=" + newState);
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                final String name = gatt.getDevice().getName();
                notifyWeb("onNativeBleState(true, '" + (name != null ? name : "OLAS1") + "');");
                // Delay service discovery to match nRF Connect timing (ensuring ACL connection settles)
                new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(() -> {
                    if (bluetoothGatt != null) {
                        Log.i(TAG, "Discovering services after ACL settle delay...");
                        bluetoothGatt.discoverServices();
                    }
                }, 1200);
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                notifyWeb("onNativeBleState(false, '');");
            }
        }

        @Override
        public void onServicesDiscovered(BluetoothGatt gatt, int status) {
            Log.i(TAG, "Services discovered: status=" + status);
            if (status == BluetoothGatt.GATT_SUCCESS) {
                BluetoothGattService service = gatt.getService(OLA_SERVICE_UUID);
                if (service != null) {
                    BluetoothGattCharacteristic rx = service.getCharacteristic(OLA_RX_CHAR_UUID);
                    if (rx != null) {
                        gatt.setCharacteristicNotification(rx, true);
                        BluetoothGattDescriptor cccd = rx.getDescriptor(CCCD_UUID);
                        if (cccd != null) {
                            cccd.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                            gatt.writeDescriptor(cccd);
                            Log.i(TAG, "Subscribed to RX telemetry notifications via Native BLE!");
                        }
                    }
                } else {
                    Log.w(TAG, "Service " + OLA_SERVICE_UUID + " not found!");
                }
            }
        }

        @Override
        public void onCharacteristicChanged(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic) {
            handleIncomingBytes(characteristic.getValue());
        }

        @Override
        public void onCharacteristicChanged(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic, byte[] value) {
            handleIncomingBytes(value);
        }

        private void handleIncomingBytes(byte[] value) {
            if (value != null && value.length > 0) {
                StringBuilder sb = new StringBuilder();
                for (byte b : value) {
                    sb.append(String.format("%02X", b));
                }
                final String hex = sb.toString();
                notifyWeb("feedRawPacket('" + hex + "');");
            }
        }
    };

    private void notifyWeb(final String js) {
        runOnUiThread(() -> {
            if (webView != null) {
                webView.evaluateJavascript(js, null);
            }
        });
    }

    private void requestBluetoothPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            String[] permissions = {
                "android.permission.BLUETOOTH_SCAN",
                "android.permission.BLUETOOTH_CONNECT",
                "android.permission.ACCESS_FINE_LOCATION"
            };
            boolean needRequest = false;
            for (String p : permissions) {
                if (checkSelfPermission(p) != PackageManager.PERMISSION_GRANTED) {
                    needRequest = true;
                    break;
                }
            }
            if (needRequest) {
                requestPermissions(permissions, PERMISSION_REQUEST_CODE);
            }
        } else {
            if (checkSelfPermission("android.permission.ACCESS_FINE_LOCATION") != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{"android.permission.ACCESS_FINE_LOCATION"}, PERMISSION_REQUEST_CODE);
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        disconnectNativeGatt();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}

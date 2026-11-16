package be.spyi.desk;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import androidx.webkit.WebViewAssetLoader;
import java.io.OutputStream;

/** WebView shell for the bundled, offline-capable SPYI dashboard.
 * The Home Assistant connection is configured in the dashboard, never hardcoded.
 * No credentials, data, or tokens are embedded in the APK.
 */
public final class MainActivity extends Activity {
    private static final String HOME = "https://appassets.androidplatform.net/assets/index.html";
    private static final int PICK_INPUT = 3001;
    private static final int SAVE_EXPORT = 3002;
    private WebView webView;
    private android.webkit.ValueCallback<Uri[]> uploadCallback;
    private byte[] pendingExport;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(android.graphics.Color.rgb(16,37,54));
        getWindow().setNavigationBarColor(android.graphics.Color.rgb(16,37,54));
        WebViewAssetLoader assetLoader = new WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
            .build();
        webView = new WebView(this);
        setContentView(webView);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        if (Build.VERSION.SDK_INT >= 26) settings.setSafeBrowsingEnabled(true);
        WebView.setWebContentsDebuggingEnabled(false);
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri target = req.getUrl();
                if (target.toString().startsWith("https://appassets.androidplatform.net/assets/")) return false;
                if ("https".equals(target.getScheme())) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, target)); }
                    catch (ActivityNotFoundException ignored) {}
                }
                return true;
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(
                WebView view, android.webkit.ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (uploadCallback != null) uploadCallback.onReceiveValue(null);
                uploadCallback = callback;
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.setType("*/*");
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                try { startActivityForResult(Intent.createChooser(intent, "Selecteer SPYI of MeDirect-bestand"), PICK_INPUT); }
                catch (ActivityNotFoundException e) {
                    uploadCallback = null;callback.onReceiveValue(null);return false;
                }
                return true;
            }
        });
        // Only bundled HTML is navigable inside this WebView; external links leave the app.
        webView.addJavascriptInterface(new SafeExportBridge(), "SPYIAndroid");
        webView.loadUrl(HOME);
    }

    public final class SafeExportBridge {
        @JavascriptInterface public void saveFile(String fileName, String mime, String base64) {
            if(base64 == null || base64.length() > 14_000_000) return;
            if(fileName == null || !fileName.matches("[A-Za-z0-9_\\-.]{1,100}\\.(csv|json|txt)")) return;
            final byte[] content;
            try { content=Base64.decode(base64, Base64.DEFAULT); }
            catch (IllegalArgumentException e) { return; }
            if(content.length > 10*1024*1024) return;
            runOnUiThread(() -> {
                pendingExport=content;
                Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);
                intent.setType(mime != null && (mime.startsWith("text/") || mime.equals("application/json"))
                    ? mime : "application/octet-stream");
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.putExtra(Intent.EXTRA_TITLE,fileName);
                try { startActivityForResult(intent,SAVE_EXPORT); }
                catch (ActivityNotFoundException e) {
                    pendingExport=null;
                    Toast.makeText(MainActivity.this,"Geen bestandsbeheerder gevonden",Toast.LENGTH_SHORT).show();
                }
            });
        }
    }

    @Override @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode,int resultCode,Intent data) {
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode==PICK_INPUT) {
            if(uploadCallback!=null) {
                uploadCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode,data));
                uploadCallback=null;
            }
        } else if(requestCode==SAVE_EXPORT) {
            if(resultCode==RESULT_OK && data!=null && data.getData()!=null && pendingExport!=null) {
                try(OutputStream out=getContentResolver().openOutputStream(data.getData())) {
                    if(out!=null){out.write(pendingExport);
                        Toast.makeText(this,"Bestand opgeslagen",Toast.LENGTH_SHORT).show();}
                } catch(Exception e) {
                    Toast.makeText(this,"Opslaan mislukt",Toast.LENGTH_LONG).show();
                }
            }
            pendingExport=null;
        }
    }
    @Override @SuppressWarnings("deprecation") public void onBackPressed() {
        if(webView!=null && webView.canGoBack())webView.goBack();
        else super.onBackPressed();
    }
    @Override protected void onDestroy() {
        if(webView!=null){webView.removeJavascriptInterface("SPYIAndroid");webView.destroy();}
        super.onDestroy();
    }
}

package com.willylehun.geopolitiqueenunclic;

import android.net.Uri;
import com.google.androidbrowserhelper.trusted.LauncherActivity;

public final class SecureLauncherActivity extends LauncherActivity {
    private static final String ALLOWED_SCHEME = "https";
    private static final String ALLOWED_HOST = "willylehun.github.io";
    private static final String ALLOWED_PREFIX = "/geopolitique-en-un-clic/";
    private static final Uri DEFAULT_URL = Uri.parse("https://willylehun.github.io/geopolitique-en-un-clic/");

    @Override
    protected Uri getLaunchingUrl() {
        Uri candidate = super.getLaunchingUrl();
        if (candidate == null) return DEFAULT_URL;

        String scheme = candidate.getScheme();
        String host = candidate.getHost();
        String path = candidate.getPath();

        boolean validScheme = ALLOWED_SCHEME.equalsIgnoreCase(scheme);
        boolean validHost = ALLOWED_HOST.equalsIgnoreCase(host);
        boolean validPath = path != null
                && (path.equals("/geopolitique-en-un-clic") || path.startsWith(ALLOWED_PREFIX));

        return validScheme && validHost && validPath ? candidate : DEFAULT_URL;
    }
}

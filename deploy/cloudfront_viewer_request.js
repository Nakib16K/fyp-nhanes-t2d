var crypto = require('crypto');

// Render privately with a high-entropy demo credential hash and a UTC cutoff.
// Unrendered or expired configurations deny every path, including cached assets.
var expectedAuthHash = '__VIEWER_AUTH_SHA256__';
var expiresAtEpochMs = Number('__DEMO_EXPIRES_EPOCH_MS__');

function denied(status, message) {
    var headers = {
        'cache-control': { value: 'private, no-store' },
        'x-content-type-options': { value: 'nosniff' },
        'referrer-policy': { value: 'no-referrer' }
    };
    if (status === 401) {
        headers['www-authenticate'] = { value: 'Basic realm="Educational demo", charset="UTF-8"' };
    }
    return { statusCode: status, headers: headers, body: message };
}

function handler(event) {
    if (!/^[a-f0-9]{64}$/.test(expectedAuthHash) || !isFinite(expiresAtEpochMs) || expiresAtEpochMs <= 0 || Date.now() >= expiresAtEpochMs) {
        return denied(503, 'Demo unavailable.');
    }
    var request = event.request;
    var auth = request.headers.authorization;
    if (!auth || (auth.multiValue && auth.multiValue.length !== 1) ||
        !/^Basic [A-Za-z0-9+/]+=*$/.test(auth.value)) {
        return denied(401, 'Authentication required.');
    }
    var supplied = crypto.createHash('sha256').update(auth.value).digest('hex');
    var difference = 0;
    for (var i = 0; i < expectedAuthHash.length; i++) {
        difference |= supplied.charCodeAt(i) ^ expectedAuthHash.charCodeAt(i);
    }
    if (difference !== 0) {
        return denied(401, 'Authentication required.');
    }
    // The origin access control supplies its own AWS authorization signature.
    delete request.headers.authorization;
    return request;
}

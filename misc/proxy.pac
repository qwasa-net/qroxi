function FindProxyForURL(url, host) {

    var proxy_string = "PROXY 127.0.0.1:18010";

    // YT → proxy
    if (
        shExpMatch(host, "*.youtube.com")
        || shExpMatch(host, "youtube.com")
        || shExpMatch(host, "*.youtu.be")
        || shExpMatch(host, "youtu.be")
        || shExpMatch(host, "*.googlevideo.com")
        || shExpMatch(host, "*.ytimg.com")
    ) {
        return proxy_string;
    }

    // others → direct
    return "DIRECT";

}
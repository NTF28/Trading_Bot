import ssl

import certifi

CIPHER_SUITE_FIREFOX = (
    "TLS_AES_128_GCM_SHA256:"
    "TLS_CHACHA20_POLY1305_SHA256:"
    "TLS_AES_256_GCM_SHA384:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:"
    "ECDHE-RSA-AES128-GCM-SHA256:"
    "ECDHE-ECDSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-CHACHA20-POLY1305:"
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-AES256-SHA:"
    "ECDHE-ECDSA-AES128-SHA:"
    "ECDHE-RSA-AES128-SHA:"
    "ECDHE-RSA-AES256-SHA:"
    "DHE-RSA-AES128-SHA:"
    "DHE-RSA-AES256-SHA:"
    "AES128-SHA:"
    "AES256-SHA:"
    "DES-CBC3-SHA"
)

CIPHER_SUITE_CHROME = (
    "TLS_AES_128_GCM_SHA256:"
    "TLS_AES_256_GCM_SHA384:"
    "TLS_CHACHA20_POLY1305_SHA256:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:"
    "ECDHE-RSA-AES128-GCM-SHA256:"
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-AES128-SHA:"
    "ECDHE-RSA-AES256-SHA:"
    "AES128-GCM-SHA256:"
    "AES256-GCM-SHA384:"
    "AES128-SHA:"
    "AES256-SHA"
)


def create_ssl_context(cipher_suite: str = None, ecdh_curve: str = None) -> ssl.SSLContext:
    """
    Creates and configures a secure SSL context tailored for Chrome-like behavior.

    This function generates an SSL context suited for client-side HTTPS communication
    by utilizing settings and cipher configurations that align with Chrome's standards.
    It ensures proper verification of server certificates and supports modern TLS
    versions for secure communication.

    Returns:
        ssl.SSLContext: An SSL context object ready for establishing secure connections.

    """
    if not cipher_suite:
        cipher_suite = CIPHER_SUITE_FIREFOX
    if not ecdh_curve:
        ecdh_curve = "prime256v1"

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(certifi.where())
    ctx.set_ciphers(cipher_suite)
    ctx.options |= (
            ssl.OP_NO_TLSv1
            | ssl.OP_NO_TLSv1_1
            | ssl.OP_NO_COMPRESSION
            | ssl.OP_CIPHER_SERVER_PREFERENCE
    )
    ctx.set_ecdh_curve(ecdh_curve or "prime256v1")
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED

    return ctx

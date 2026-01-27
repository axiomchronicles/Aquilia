"""
Test Response cookies - multiple cookies, signing, deletion.
"""

import pytest
from datetime import datetime, timezone, timedelta
from aquilia.response import Response, CookieSigner


@pytest.mark.asyncio
async def test_set_multiple_cookies():
    """Test multiple set_cookie calls produce multiple Set-Cookie header entries."""
    response = Response(b"test")
    
    response.set_cookie("session_id", "abc123", secure=True, httponly=True)
    response.set_cookie("user_pref", "dark_mode", secure=True)
    response.set_cookie("tracking", "xyz", samesite="None", secure=True)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Extract Set-Cookie headers
    start = messages[0]
    set_cookie_headers = [
        v.decode() 
        for k, v in start["headers"] 
        if k.decode().lower() == "set-cookie"
    ]
    
    # Should have 3 Set-Cookie headers
    assert len(set_cookie_headers) == 3
    
    # Check each cookie
    assert any("session_id=abc123" in h for h in set_cookie_headers)
    assert any("user_pref=dark_mode" in h for h in set_cookie_headers)
    assert any("tracking=xyz" in h for h in set_cookie_headers)
    
    # Check attributes
    assert any("Secure" in h and "HttpOnly" in h for h in set_cookie_headers)


@pytest.mark.asyncio
async def test_cookie_attributes():
    """Test cookie attributes are properly formatted."""
    response = Response(b"test")
    
    expires = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    
    response.set_cookie(
        "test_cookie",
        "value123",
        max_age=3600,
        expires=expires,
        path="/admin",
        domain="example.com",
        secure=True,
        httponly=True,
        samesite="Strict"
    )
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Get cookie header
    start = messages[0]
    cookie_header = None
    for k, v in start["headers"]:
        if k.decode().lower() == "set-cookie":
            cookie_header = v.decode()
            break
    
    assert cookie_header is not None
    assert "test_cookie=value123" in cookie_header
    assert "Max-Age=3600" in cookie_header
    assert "Path=/admin" in cookie_header
    assert "Domain=example.com" in cookie_header
    assert "Secure" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=Strict" in cookie_header


@pytest.mark.asyncio
async def test_delete_cookie():
    """Test cookie deletion sets Max-Age=0."""
    response = Response(b"test")
    
    response.delete_cookie("session_id", path="/", domain="example.com")
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Get cookie header
    start = messages[0]
    cookie_header = None
    for k, v in start["headers"]:
        if k.decode().lower() == "set-cookie":
            cookie_header = v.decode()
            break
    
    assert cookie_header is not None
    assert "session_id=" in cookie_header
    assert "Max-Age=0" in cookie_header


@pytest.mark.asyncio
async def test_cookie_signing_and_verify():
    """Test signed cookies sign/verify roundtrip; invalid signature -> failure."""
    signer = CookieSigner("my-secret-key")
    
    # Sign a value
    original_value = "user123"
    signed_value = signer.sign(original_value)
    
    # Verify signature format
    assert "." in signed_value
    sig, val = signed_value.split(".", 1)
    assert len(sig) > 0
    assert len(val) > 0
    
    # Unsign - should get original value
    unsigned_value = signer.unsign(signed_value)
    assert unsigned_value == original_value
    
    # Tamper with signature
    tampered = signed_value[:-5] + "xxxxx"
    result = signer.unsign(tampered)
    assert result is None  # Invalid signature
    
    # Tamper with value
    parts = signed_value.split(".")
    tampered2 = parts[0] + ".xxxxxx"
    result2 = signer.unsign(tampered2)
    assert result2 is None


@pytest.mark.asyncio
async def test_signed_cookie_in_response():
    """Test setting signed cookie in response."""
    response = Response(b"test")
    signer = CookieSigner("secret-key-12345")
    
    response.set_cookie(
        "secure_session",
        "user_data",
        signed=True,
        signer=signer,
        secure=True,
        httponly=True
    )
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Get cookie
    start = messages[0]
    cookie_header = None
    for k, v in start["headers"]:
        if k.decode().lower() == "set-cookie":
            cookie_header = v.decode()
            break
    
    assert cookie_header is not None
    assert "secure_session=" in cookie_header
    
    # Extract signed value
    cookie_value = cookie_header.split("secure_session=")[1].split(";")[0]
    
    # Should be able to verify
    unsigned = signer.unsign(cookie_value)
    assert unsigned == "user_data"


def test_cookie_signer_algorithms():
    """Test different hash algorithms."""
    for algo in ["sha256", "sha384", "sha512"]:
        signer = CookieSigner("secret", algorithm=algo)
        
        signed = signer.sign("test_value")
        unsigned = signer.unsign(signed)
        
        assert unsigned == "test_value"


def test_cookie_signer_with_bytes_key():
    """Test signer with bytes secret key."""
    signer = CookieSigner(b"secret-bytes-key")
    
    signed = signer.sign("test")
    unsigned = signer.unsign(signed)
    
    assert unsigned == "test"

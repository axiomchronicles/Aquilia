
from aquilia.config_builders import Workspace, Integration, AuthConfig, Module

def test_config_builder_auth():
    ws = (
        Workspace("test_app")
        .integrate(Integration.auth(
            enabled=True,
            secret_key="my-secret-key",
            store_type="redis"
        ))
    )
    
    config = ws.to_dict()
    print("Config keys:", config.keys())
    print("Integrations keys:", config["integrations"].keys())
    
    auth_config = config["integrations"].get("auth")
    if not auth_config:
        print("FAIL: Auth config not found in integrations")
        exit(1)
        
    print("Auth Config:", auth_config)
    
    assert auth_config["enabled"] is True
    assert auth_config["tokens"]["secret_key"] == "my-secret-key"
    assert auth_config["store"]["type"] == "redis"
    
    print("SUCCESS: Auth config verified")

def test_config_builder_auth_object():
    auth_conf = AuthConfig(
        enabled=True,
        secret_key="obj-secret",
        store_type="memory"
    )
    
    ws = (
        Workspace("test_app_obj")
        .integrate(Integration.auth(auth_conf))
    )
    
    config = ws.to_dict()
    auth_config = config["integrations"]["auth"]
    
    assert auth_config["tokens"]["secret_key"] == "obj-secret"
    print("SUCCESS: Auth config object verified")

if __name__ == "__main__":
    test_config_builder_auth()
    test_config_builder_auth_object()

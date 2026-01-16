"""
W16 Verification - Signing & Packaging.
"""
import sys
import os
import shutil
import json
import zipfile

# Add project root
sys.path.append(os.getcwd())

from assistant.plugins.signing import PluginSigner
from assistant.plugins.builder import PluginBuilder

def test_signing_flow():
    print("🧪 Testing Plugin Signing & Building...")
    
    test_dir = "test_data_w16"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 1. Generate Keys
    print("🔑 Generating Keys...")
    priv_path, pub_path = PluginSigner.generate_keys(test_dir)
    print(f"  Private: {priv_path}")
    print(f"  Public: {pub_path}")
    
    # 2. Create Dummy Plugin Source
    src_dir = os.path.join(test_dir, "dummy_plugin")
    os.makedirs(src_dir)
    with open(os.path.join(src_dir, "plugin.json"), "w") as f:
        json.dump({"id": "dummy.plugin", "version": "1.0.0", "name": "Dummy"}, f)
    with open(os.path.join(src_dir, "main.py"), "w") as f:
        f.write("print('Hello Signed World')")
        
    # 3. Build Package
    print("\n📦 Building Package...")
    builder = PluginBuilder()
    dist_dir = os.path.join(test_dir, "dist")
    
    pkg_path = builder.build_package(src_dir, priv_path, dist_dir)
    print(f"  Package Created: {pkg_path}")
    
    # 4. Verify (Simulate Installer)
    print("\n🔍 Verifying Package...")
    with zipfile.ZipFile(pkg_path, 'r') as zf:
        zf.extractall(os.path.join(test_dir, "extracted"))
        
    extracted_content = os.path.join(test_dir, "extracted", "content.zip")
    extracted_sig = os.path.join(test_dir, "extracted", "signature.hex")
    
    with open(extracted_sig, "r") as f:
        sig_hex = f.read()
        
    valid = PluginSigner.verify_file(extracted_content, sig_hex, public_key_path=pub_path)
    
    if valid:
        print("✅ Validation PASSED.")
    else:
        print("❌ Validation FAILED.")
        sys.exit(1)
        
    # 5. Tamper Test
    print("\n😈 Testing Tamper Resistance...")
    # Modify content.zip
    with open(extracted_content, "ab") as f:
        f.write(b"TAMPERED")
        
    valid_tamper = PluginSigner.verify_file(extracted_content, sig_hex, public_key_path=pub_path)
    
    if not valid_tamper:
        print("✅ Tamper correctly detected (Validation Failed).")
    else:
        print("❌ Tamper FAILED (Validation passed on modified file!).")
        sys.exit(1)

if __name__ == "__main__":
    test_signing_flow()

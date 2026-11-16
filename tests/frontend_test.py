"""Check every inline JavaScript block with Node's parser (syntax only)."""
import re,subprocess,tempfile
from pathlib import Path
src=(Path(__file__).resolve().parents[1]/"spyi_desk"/"SPYI_Dashboard.html").read_text()
scripts=re.findall(r"<script[^>]*>(.*?)</script>",src,re.S|re.I)
assert len(scripts)>=3,f"Expected 3 scripts, got {len(scripts)}"
assert "const demoHoldings=[" not in src
assert "generateDemoHistory()" not in src
assert "11.85" not in src
assert "SPYI.DE" in src
assert "syncOfficialHoldings" in src
for i,script in enumerate(scripts):
    with tempfile.NamedTemporaryFile(suffix=".js",mode="w",encoding="utf-8") as f:
        f.write(script);f.flush()
        subprocess.run(["node","--check",f.name],check=True)
print("PASS all inline scripts parse and no seeded market quotes remain")

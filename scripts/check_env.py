import importlib.metadata as md
import platform
import sys

import torch

OK, KO = "✅", "❌"
failures = []

def check(label, cond, detail=""):
    print(f"{OK if cond else KO}{label}" + (f" : {detail}" if detail else ""))
    if not cond:
        failures.append(label)

print("== Versions ==")
print(f"{'python':<14}{platform.python_version()}")
for pkg in ["torch", "transformers", "accelerate", "peft", "trl", "bitsandbytes", "datasets", "unsloth", "tensorboard"]:
    try:
        print(f"{pkg:<14}{md.version(pkg)}")
    except md.PackageNotFoundError:
        print(f"{pkg:<14}(non installé)")

print("\n== GPU ==")
check("CUDA disponible", torch.cuda.is_available(), f"torch compilé pour CUDA {torch.version.cuda}")
if torch.cuda.is_available():
    free, total = torch.cuda.mem_get_info()
    major, minor = torch.cuda.get_device_capability(0)
    print(f"    GPU : {torch.cuda.get_device_name(0)} (compute capability {major}.{minor})")
    print(f"    VRAM : {free / 1024**3:.1f} Go libres / {total / 1024**3:.1f} Go")
    check("bf16 supporté", torch.cuda.is_bf16_supported())

    print("\n== Test QLoRA : couche 4 bits ==")
    try:
        import bitsandbytes as bnb
        layer = bnb.nn.Linear4bit(1024, 1024, compute_dtype=torch.bfloat16, quant_type="nf4").cuda()
        x = torch.randn(4, 1024, dtype=torch.bfloat16, device="cuda")
        y = layer(x)
        check("forward 4 bits", y.shape == (4,1024) and torch.isfinite(y).all().item(), f"poids stockés en {layer.weight.dtype}")
    except Exception as e:
        check("forward 4 bits", False, repr(e))

print()
if failures:
    print(f"{KO} {len(failures)} échec(s) : {', '.join(failures)}")
    sys.exit(1)
print(f"{OK} Environnement prêt pour la phase 1")

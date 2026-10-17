"""Check the private runtime and local model files without downloading anything."""
import argparse
import json
from runtime_paths import APP, RUNTIME
from offline_network import enforce_local_network

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-creative',action='store_true')
    args=parser.parse_args()
    enforce_local_network()
    import torch
    import soundfile
    import chatterbox.mtl_tts
    import chatterbox.vc
    if not torch.cuda.is_available():
        raise SystemExit('NVIDIA CUDA is unavailable. Install a compatible NVIDIA driver.')
    result=torch.ones(32,device='cuda').sum().item()
    if result!=32:raise SystemExit('GPU arithmetic check failed.')
    print('GPU check passed:',torch.cuda.get_device_name(0))
    manifest=json.loads((APP/'model-manifest.json').read_text(encoding='utf-8'))
    if args.require_creative:
        manifest+=json.loads((APP/'creative-model-manifest.json').read_text(encoding='utf-8'))
    for item in manifest:
        file=RUNTIME/'models'/item['folder']/item['file']
        if not file.is_file() or file.stat().st_size!=item['size']:
            raise SystemExit('Model missing or incomplete: '+item['folder']+'/'+item['file']+'. Run setup again.')
    creative=(RUNTIME/'qwen-venv'/'Scripts'/'python.exe').is_file() and (RUNTIME/'models'/'qwen-design-sharded'/'model.safetensors.index.json').is_file()
    if args.require_creative and not creative:raise SystemExit('Creative runtime is incomplete. Run Setup-Creative.cmd again.')
    print('Pinned local model file sizes checked. Setup verifies SHA-256 when downloading.')
    print('Creative mode:', 'installed' if creative else 'optional; run Setup-Creative.cmd to install')
    print('Health check passed. No models or packages were downloaded.')

if __name__=='__main__':main()

"""Capture runtime versions and device information for reproduction receipts."""
import argparse,importlib.metadata,json,platform,subprocess,sys
from pathlib import Path

EXPECTED={'ftfy':'6.3.1','wcwidth':'0.2.13','numpy':'1.26.4','torch':'2.5.1','torchvision':'0.20.1','scipy':'1.14.1','bchlib':'2.1.3','diffusers':'0.35.2','transformers':'4.51.0','accelerate':'1.2.1','huggingface-hub':'0.34.4','peft':'0.17.1','timm':'1.0.15','opencv-python-headless':'4.10.0.84','Pillow':'11.0.0','imageio-ffmpeg':'0.6.0'}

def version_errors(actual,expected=EXPECTED):
    return {name:{'expected':version,'actual':actual.get(name)} for name,version in expected.items() if str(actual.get(name)).split('+')[0]!=version}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--strict',action='store_true');a=p.parse_args()
    packages={}
    for name in ['last-watermark','ftfy','wcwidth','numpy','torch','torchvision','scipy','bchlib','diffusers','transformers','accelerate','huggingface-hub','peft','timm','opencv-python-headless','Pillow','imageio-ffmpeg']:
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    report=dict(python=sys.version,platform=platform.platform(),packages=packages)
    report['version_mismatches']=version_errors(packages)
    report['loaded_modules']={}
    for name,package in [('PIL','Pillow'),('imageio_ffmpeg','imageio-ffmpeg')]:
        try:
            module=__import__(name);version=module.__version__
            report['loaded_modules'][name]={'version':version,'path':module.__file__}
            if version!=EXPECTED[package]:report['version_mismatches'][package]={'expected':EXPECTED[package],'actual_loaded':version}
        except ImportError:report['version_mismatches'][package]={'error':'Module cannot be imported'}
    import torch
    report.update(cuda_available=torch.cuda.is_available(),torch_cuda=torch.version.cuda)
    if torch.cuda.is_available():report['gpus']=[dict(name=torch.cuda.get_device_name(i),memory_bytes=torch.cuda.get_device_properties(i).total_memory) for i in range(torch.cuda.device_count())]
    try:report['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except (FileNotFoundError,subprocess.CalledProcessError):report['git_commit']=None
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2));print(json.dumps(report))
    if a.strict and report['version_mismatches']:raise SystemExit(2)
if __name__=='__main__':main()


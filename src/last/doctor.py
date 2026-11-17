"""Capture runtime versions and device information for reproduction receipts."""
import argparse,importlib.metadata,json,platform,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    packages={}
    for name in ['last-watermark','numpy','torch','torchvision','scipy','bchlib','diffusers','transformers','accelerate','huggingface-hub','peft','timm','opencv-python-headless','Pillow','imageio-ffmpeg']:
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    report=dict(python=sys.version,platform=platform.platform(),packages=packages)
    import torch
    report.update(cuda_available=torch.cuda.is_available(),torch_cuda=torch.version.cuda)
    if torch.cuda.is_available():report['gpus']=[dict(name=torch.cuda.get_device_name(i),memory_bytes=torch.cuda.get_device_properties(i).total_memory) for i in range(torch.cuda.device_count())]
    try:report['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except (FileNotFoundError,subprocess.CalledProcessError):report['git_commit']=None
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()

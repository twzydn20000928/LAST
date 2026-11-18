"""Capture runtime versions and device information for reproduction receipts."""
import argparse,importlib.metadata,json,os,platform,subprocess,sys
from pathlib import Path

EXPECTED={'ftfy':'6.3.1','wcwidth':'0.2.13','numpy':'1.26.4','torch':'2.5.1','torchvision':'0.20.1','scipy':'1.14.1','bchlib':'2.1.3','diffusers':'0.35.2','transformers':'4.51.0','accelerate':'1.2.1','huggingface-hub':'0.34.4','peft':'0.17.1','timm':'1.0.15','opencv-python-headless':'4.10.0.84','Pillow':'11.0.0','imageio-ffmpeg':'0.6.0'}

def version_errors(actual,expected=EXPECTED):
    return {name:{'expected':version,'actual':actual.get(name)} for name,version in expected.items() if str(actual.get(name)).split('+')[0]!=version}

EXPECTED.update({'sentencepiece':'0.2.0','imageio':'2.37.0'})

def gpu_environment_errors(python_version, cuda_available, torch_cuda):
    errors = []
    if tuple(python_version[:2]) != (3, 10):
        errors.append('The measured environment uses Python 3.10')
    if not cuda_available:
        errors.append('PyTorch cannot access a CUDA device')
    if torch_cuda != '12.4':
        errors.append('The measured PyTorch build uses CUDA 12.4')
    return errors

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--strict',action='store_true')
    p.add_argument('--require-paper-runtime', action='store_true', help='Require Python 3.10, CUDA 12.4 PyTorch and a visible GPU')
    a=p.parse_args()
    packages={}
    for name in ['last-watermark', *EXPECTED]:
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
    report['numerical_backend']={
        'cudnn_version':torch.backends.cudnn.version(),
        'cudnn_benchmark':torch.backends.cudnn.benchmark,
        'cudnn_deterministic':torch.backends.cudnn.deterministic,
        'cudnn_allow_tf32':torch.backends.cudnn.allow_tf32,
        'matmul_allow_tf32':torch.backends.cuda.matmul.allow_tf32,
        'deterministic_algorithms':torch.are_deterministic_algorithms_enabled(),
        'flash_sdp':torch.backends.cuda.flash_sdp_enabled(),
        'mem_efficient_sdp':torch.backends.cuda.mem_efficient_sdp_enabled(),
        'math_sdp':torch.backends.cuda.math_sdp_enabled(),
        'environment':{name:os.environ.get(name) for name in ('CUBLAS_WORKSPACE_CONFIG','NVIDIA_TF32_OVERRIDE','CUDA_MODULE_LOADING','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')},
        'scope':'Observed in this doctor process; flags are not changed and do not prove bitwise determinism of another run'}
    report.update(cuda_available=torch.cuda.is_available(),torch_cuda=torch.version.cuda)
    report['paper_runtime_errors']=gpu_environment_errors(sys.version_info, report['cuda_available'], report['torch_cuda'])
    if torch.cuda.is_available():report['gpus']=[dict(name=torch.cuda.get_device_name(i),memory_bytes=torch.cuda.get_device_properties(i).total_memory) for i in range(torch.cuda.device_count())]
    try:report['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except (FileNotFoundError,subprocess.CalledProcessError):report['git_commit']=None
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2));print(json.dumps(report))
    if a.strict and report['version_mismatches']:raise SystemExit(2)
    if a.require_paper_runtime and report['paper_runtime_errors']:raise SystemExit(2)
if __name__=='__main__':main()

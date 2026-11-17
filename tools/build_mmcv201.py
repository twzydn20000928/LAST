"""Build the pinned MMCV source with an explicit C++17 compatibility patch.

This does not install a wheel or certify the VBench environment. Run with the
Python interpreter of the intended quality environment (with PyTorch installed).
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import traceback
import urllib.request

URL = 'https://files.pythonhosted.org/packages/ab/03/6c4fb70f2c547ab96cbf66a235aa4465631f77d045e57d84d941b3e66311/mmcv-2.0.1.tar.gz'
SHA256 = '2b9b2c23795b3f43cf2ebcaca46552d9b4ef7e903eacdcf7c08ee15195044071'


def prepare(data, output):
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('MMCV source checksum mismatch')
    archive = output / 'mmcv-2.0.1.tar.gz'
    archive.write_bytes(data)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or path.parts[0] != 'mmcv-2.0.1'
                    or not (member.isfile() or member.isdir())):
                raise ValueError('Unsafe source archive member')
        tar.extractall(output)
    source = output / 'mmcv-2.0.1'
    setup = source / 'setup.py'
    before = setup.read_bytes()
    after = before.replace(b'-std=c++14', b'-std=c++17').replace(b'/std:c++14', b'/std:c++17')
    if before == after:
        raise ValueError('Expected C++14 flags absent')
    setup.write_bytes(after)
    (output / 'cpp17.patch').write_text(''.join(difflib.unified_diff(
        before.decode().splitlines(True), after.decode().splitlines(True),
        fromfile='setup.py.original', tofile='setup.py')))
    return source, {name: hashlib.sha256(value).hexdigest() for name, value in
                    [('original_setup_sha256', before), ('patched_setup_sha256', after)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-archive', type=Path, help='Optional cached, checksum-verified source')
    parser.add_argument('--cuda-home', type=Path, required=True)
    parser.add_argument('--cuda-arch', default='8.9', help='8.9 is L40; select the actual target architecture')
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    record = dict(status='preparing', started=time.time(), source_url=URL,
                  source_sha256=SHA256, python=sys.executable,
                  scope='Build only; no installation or quality-score validation')
    def save():
        (output / 'receipt.json').write_text(json.dumps(record, indent=2))
    try:
        save()
        if args.source_archive:
            data = args.source_archive.read_bytes()
        else:
            with urllib.request.urlopen(URL, timeout=120) as response:
                data = response.read()
        source, hashes = prepare(data, output)
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        env.pop('PYTHONHOME', None)
        settings = dict(PYTHONNOUSERSITE='1', CUDA_HOME=str(args.cuda_home.resolve()),
                        MMCV_WITH_OPS='1', FORCE_CUDA='1', CUDA_VISIBLE_DEVICES='',
                        MAX_JOBS=str(args.jobs), TORCH_CUDA_ARCH_LIST=args.cuda_arch,
                        OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
        env.update(settings)
        env['PATH'] = str(args.cuda_home.resolve() / 'bin') + os.pathsep + env.get('PATH', '')
        command = [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                   '--wheel-dir', str(output / 'wheels'), str(source)]
        record.update(hashes, status='building', build_env=settings, command=command)
        save()
        with (output / 'build.log').open('w') as log:
            subprocess.run(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        wheels = list((output / 'wheels').glob('mmcv-2.0.1-*.whl'))
        if len(wheels) != 1:
            raise RuntimeError('Missing or ambiguous output wheel')
        record.update(status='built_pending_validation', wheel_name=wheels[0].name,
                      wheel_sha256=hashlib.sha256(wheels[0].read_bytes()).hexdigest())
    except BaseException:
        record.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        record['finished'] = time.time()
        save()


if __name__ == '__main__':
    main()

# 用一条视频试用 LAST

如果只想看论文设置下的效果，可以直接打开[三个样本的七条件比较](../results/quickstart-three-videos.md)。如果想亲自验证，仓库附带一条 65 帧、512 × 512 的水印视频。下面从这条视频开始，全程在仓库根目录运行 Linux Bash 命令。

### 在 CPU 上核对已有结果

仓库里有 Hunyuan 和 Wan-2.2 的逐样本记录。以下命令只需 Python 3.10，可直接在仓库根目录运行。每张表都取冻结清单的前三个样本，列出 LAST 和 LFG 在原片及六项攻击下分别读对多少位。每格分母为 3 × 512 = 1536 位，括号内给出完整恢复的消息数。

```bash
for family in hunyuan wan22; do
  for mode in i2v t2v; do
    report="results/${family}_${mode}_paired_primary_first_three.json"
    if [[ "$family/$mode" == "hunyuan/i2v" ]]; then
      report=results/hunyuan_i2v_primary24.json
    fi
    echo "$family/$mode"
    PYTHONPATH=src python tools/matched_primary_methods.py --family "$family" --mode "$mode" \
      --methods last lfg --first 3 --reports "$report"
  done
done
```

例如，Wan-2.2 图生视频随机删帧后，LAST 读对 978/1536 位，LFG 读对 1077/1536 位；在同模型的文生视频中，两者分别读对 1149/1536 和 1050/1536 位。这四格均为 0/3 条消息完整恢复。读者可以更换视频生成方式查看差异；三个样本仅作演示。

[五种方法的同样本对照](../results/five-method-paper291.md)使用同一个 Hunyuan 图生样本 `paper-291`。每种方法各自生成水印视频，每格分母为 512 位。原片、噪声、压缩、模糊和随机删帧都有五种方法的结果。表中的横线表示该条件仍缺少五方齐备的评分。用以下命令可从逐样本记录重建此表。

```bash
PYTHONPATH=src python tools/matched_primary_methods.py --family hunyuan --mode i2v \
  --methods last lfg sigmark videomark videoshield --reports results/hunyuan_i2v_primary_slice291.json \
  results/hunyuan_i2v_sigmark_videomark_paper291.json results/hunyuan_i2v_videoshield_slice291.json
```

在这个样本中，随机删 30 帧与连续删 30 帧都留下 35 帧。按原视频从 0 开始编号，随机删帧后 LAST 选中的两个四帧窗口分别来自画面 `27,28,29,31` 和 `34,35,36,38`，两者都跨越原始组边界，各自有 0 帧属于预测组。纠错前后均读对 250/512 位。连续删帧后选中的六组都完整且编号正确，纠错前后均读对 466/512 位。这个例子展示了两个可以分别核查的问题：分组是否对齐，以及对齐后保留下来的信号能否恢复整条消息。

## 1. 读出公开视频里的文字

准备 Python 3.10 环境。只做提取和攻击时，安装读端依赖即可。

```bash
git clone https://github.com/twzydn20000928/LAST.git
cd LAST
python3.10 -m venv .venv
source .venv/bin/activate
unset PYTHONPATH
export PYTHONNOUSERSITE=1
python -m pip install -r environments/reader-linux-py310-cu124.txt
python -m pip install --no-deps -e .
python -m pip check
```

选择一个新的工作目录。第一条 Python 命令准备公开示例的密钥和已知消息。第二条下载并核验视频编码器（VAE），约 986 MB。收到视频的人只需视频、对应密钥和编码器即可提取。

```bash
work="$HOME/last-sailboat-demo"
vae="$HOME/last-checkpoints/hunyuan_t2v"
video=examples/public_demo/sailboat.mp4
python examples/public_demo/prepare.py --output "$work"
python -m last.models --name hunyuan_t2v --directory "$vae" --vae-only --download --verify-manifest configs/checkpoint_files.json
python -m last.extract --family hunyuan --model-dir "$vae" --video "$video" --key "$work/secret.key" --output "$work/prediction.json"
python -m last.cli unpack-message --text --prediction "$work/prediction.json" --output "$work/recovered.txt"
cat "$work/recovered.txt"
```

原片预期文字为 `LAST public reader demonstration v1`。提取默认使用 CUDA。若使用 CPU，在 `last.extract` 或下文的 `last.check_video` 命令中加上 `--device cpu --progress`。在四线程 CPU 上，65 帧原片通过 62 个候选窗口恢复了全部 512 位，解出的 35 字节文本与原文一致，耗时约 38 分钟。35 帧删帧视频用时约 19 分钟。两项用时均来自共享服务器。[原片 CPU 实测](../results/public_sailboat_cpu_clean.json)

## 2. 在同一视频上比较两种删帧方式

以下命令分别随机删除 30 帧、连续删除 30 帧。两条输出都剩 35 帧。程序将受攻击的视频写入 MP4 后重新读取；已知消息只在提取结束后用于评分。

```bash
python -m last.check_video --video "$video" --video-id sailboat-demo-v1 --demo-codec-threads \
  --family hunyuan --model-dir "$vae" --key "$work/secret.key" --message "$work/message.bin" \
  --condition drop --condition clip --output "$work/two-deletions"
cat "$work/two-deletions/summary.md"
```

| 公开示例的 GPU 实测 | 正确位数 | 比特准确率 | 整条消息恢复 |
|---|---:|---:|---|
| 随机删除 | 471/512 | 91.99% | 否 |
| 连续删除 | 512/512 | 100% | 是 |

这是同一条视频的一次对照。移除两个 `--condition` 参数并指定新的输出目录，可运行原片和全部六项主表攻击。附录的组合攻击可用 `--condition drop30_crf28` 单独测试。[原始评分](../results/public_sailboat_attacks.json) · [附录八项攻击设置](STRESS.md)

如果评测被打断，再次运行上面的命令时，保留相同的视频、密钥和模型参数，把两个 `--condition` 参数替换为 `--retry-from "$work/two-deletions/summary.json"`，并将输出目录改为新的 `"$work/two-deletions-retry"`。程序会根据原记录只补跑失败或尚未完成的条件。原目录保存已有结果，新目录保存补跑结果。

## 3. 在生成过程中写入自己的消息

沿用已激活的环境，安装生成依赖并下载完整的 Hunyuan 文生视频模型。此步需要可用的 NVIDIA GPU。若已有固定版本的完整模型，可将 `model` 指向该目录，并省略 `--download`。

```bash
python -m pip install -r environments/video-linux-py310-cu124.txt
python -m pip check
model="$HOME/last-checkpoints/hunyuan_t2v"
mine="$HOME/last-my-video"
python -m last.models --name hunyuan_t2v --directory "$model" --download --verify-manifest configs/checkpoint_files.json
python -m last.cli prepare-video --output "$mine" --prompt "A yellow kayak moves across a quiet lake" --seed 42 --text "我的第一段视频"
python -m last.smoke --family hunyuan --mode t2v --model-dir "$model" --case "$mine/case.json" \
  --key "$mine/secret.key" --message "$mine/message.bin" --output "$mine/run" --memory-gib 8 --offload sequential --marked-only
python -m last.extract --family hunyuan --model-dir "$model" --video "$mine/run/marked.mp4" \
  --key "$mine/secret.key" --output "$mine/prediction.json"
python -m last.score_message --message "$mine/message.bin" --prediction "$mine/prediction.json"
```

生成的成片位于 `$mine/run/marked.mp4`，新密钥位于 `$mine/secret.key`。文字最多占 64 个 UTF-8 字节。需要写入任意 512 位数据时，可将 `--text` 换为 `--message-file` 并提供恰好 64 字节的文件。[图生视频与 Wan-2.2 用法](../README.md#generate-and-evaluate-your-own-video)

例如，要检验自己生成的皮划艇视频在压缩、随机删帧后还能读回哪些位，接收方可以直接运行以下命令。两项攻击分别作用于同一原片，输出目录需为新目录。

```bash
python -m last.check_video --video "$mine/run/marked.mp4" --video-id kayak-42 \
  --family hunyuan --model-dir "$model" --key "$mine/secret.key" \
  --condition compression --condition drop --output "$mine/attacks"
cat "$mine/attacks/summary.md"
```

接收方此时只有预测结果。发送方拿到评测目录后，可以在 CPU 上与原消息核对。以下命令复用已保存的预测，输出每项攻击的正确位数、错误位置和整串恢复结果。

```bash
python -m last.score_message --summary "$mine/attacks/summary.json" \
  --message "$mine/message.bin" --show-errors
```

### 在同一段生成内容上更换消息

首次运行 `last.smoke` 时加上 `--save-endpoint`，并保留其私有输出目录。这样会额外保存扩散采样结束时的潜变量。之后可以沿用相同画面内容、模型和密钥，替换 64 字节消息，再次解码并导出新的水印 MP4，省去重新运行 50 步扩散采样的时间。只有最终 MP4 时，请使用前面的提取流程。

```bash
python -m last.writer_replay --run "$mine/run" --model-dir "$model" \
  --message-file /path/to/another-64-byte-message.bin --output "$mine/second-message"
```

这里的 `$mine/run` 必须是首次就带 `--save-endpoint` 的生成目录。回写只需解码器；`$model` 可指向包含相同 `vae/` 文件的目录。新保存的终点会记录这些文件的摘要。旧终点若要换目录，需让原模型目录可读，以便逐文件核对。新的成片路径是 `$mine/second-message/marked.mp4`，可使用原密钥盲提取。该操作仍需视频解码器重新渲染画面；输出文件的像素和旧成片可能不同。

在 Hunyuan 图生样本 `paper-003` 上，我们复用同一个生成终点和密钥，把消息换成“我的第一段视频”。回写后的 65 帧 MP4 经独立盲提取，改变的 250 位全部读对，保留的 262 位也全部读对，解出的 21 个 UTF-8 字节与原文一致。共享服务器上 CPU 回写约 19 分钟，原片提取约 37 分钟。[单样本实测记录](../results/custom_text_endpoint_cpu.json)

对同一成片运行 `--condition drop --video-id paper-003 --map-seed 0`，随机删除 30 帧后只读对 270/512 位。正文读对 87/168 位，补零区域读对 183/344 位，输出无法解码为有效的 UTF-8 文本。这个例子有 344 位补零，即使始终输出零也能碰对 429/512 位。评估文字应用时应同时检查解出的文字，比较方法时使用论文冻结的消息。[删帧实测记录](../results/custom_text_endpoint_cpu_drop.json)

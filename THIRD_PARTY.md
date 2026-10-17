# Third-party software and models

The application wrapper is MIT licensed. Dependencies and downloaded models keep their own licenses and notices.

| Component | Source | License / notice |
|---|---|---|
| Chatterbox and its Indic adaptation | [Pinned source](https://github.com/reenigne314/chatterbox-indic-lora/tree/0cee7be98258a3085b22251e31a3379a101c1f73) | MIT; upstream notice in `licenses/Chatterbox-MIT.txt` |
| Chatterbox base weights | [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox) | MIT according to the model source |
| Tamil LoRA, tokenizer and speaker conditionings | [reenigne314/chatterbox-indic-lora](https://huggingface.co/reenigne314/chatterbox-indic-lora) | MIT according to the model source |
| Optional English VoiceDesign | [Qwen3-TTS model](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign), [code](https://github.com/QwenLM/Qwen3-TTS) | Apache-2.0 according to their sources |
| Audio watermarking | [Resemble AI Perth](https://github.com/resemble-ai/Perth) | Installed from a pinned upstream commit; retain its installed license and watermark |
| MCP Python SDK | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | MIT; installed separately using `requirements-agent.lock` |
| PyTorch, Transformers, NumPy, SciPy, SoundFile and other libraries | See the three requirements lock files | Their respective upstream licenses |

Model revisions, file sizes and SHA-256 checksums are pinned in the model manifests. Setup downloads weights from their official model repositories; weights are not redistributed in this Git repository.

No ElevenLabs, TTSVibes, Natasha or Trickster/Grinch voice recordings or proprietary models are bundled. Names mentioned in an individual local user's saved reference are not built-in voices of this distribution. Add a recording that you are authorized to use on your own installation. This app is independent software and is not affiliated with those services.

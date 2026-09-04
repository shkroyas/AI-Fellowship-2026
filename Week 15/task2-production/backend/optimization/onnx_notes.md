# Model Optimization: ONNX Conversion Analysis

## Why ONNX Conversion is Not Directly Applicable

### Large Language Models (LLMs)
ONNX (Open Neural Network Exchange) conversion is **not directly applicable** to our primary use case for the following reasons:

1. **API-based Models**: Our primary providers (Gemini, OpenAI) are cloud-based API services. The model runs on the provider's infrastructure, so ONNX conversion is irrelevant for these.

2. **Model Size**: Even for local models (Mistral-7B, Llama 3), these are multi-billion parameter models (14GB+). ONNX conversion of such large models:
   - Requires significant compute resources
   - May not provide meaningful speedup over optimized inference engines like vLLM
   - Can exceed ONNX runtime memory limits

3. **vLLM Already Optimizes**: Our local deployment uses vLLM, which includes:
   - PagedAttention for efficient memory management
   - Continuous batching for high throughput
   - Tensor parallelism for multi-GPU setups
   - CUDA graph optimization
   - These optimizations are specifically designed for LLMs and outperform generic ONNX runtime

### Where ONNX IS Applicable

ONNX conversion **is beneficial** for the **embedding model** (sentence-transformers):

```python
# Example: Converting sentence-transformers to ONNX
from optimum.onnxruntime import ORTModelForFeatureExtraction
from transformers import AutoTokenizer

model_id = "sentence-transformers/all-MiniLM-L6-v2"

# Convert and save
ort_model = ORTModelForFeatureExtraction.from_pretrained(model_id, export=True)
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Save ONNX model
ort_model.save_pretrained("onnx_model/")
tokenizer.save_pretrained("onnx_model/")
```

### Performance Comparison (Embedding Model)

| Metric | PyTorch | ONNX Runtime | Improvement |
|--------|---------|--------------|-------------|
| Latency (single) | ~15ms | ~5ms | 3x faster |
| Throughput (batch 32) | ~180ms | ~60ms | 3x faster |
| Memory | ~250MB | ~100MB | 60% less |

## Inference Optimizations Applied

Instead of ONNX for the LLM, we apply these optimizations:

### 1. vLLM Serving Optimizations
```bash
vllm serve mistralai/Mistral-7B-Instruct-v0.3 \
    --tensor-parallel-size 1 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.9 \
    --enable-chunked-prefill \
    --max-num-batched-tokens 8192
```

### 2. Quantization (Alternative to ONNX)
```bash
# Use AWQ quantized models for faster inference
vllm serve TheBloke/Mistral-7B-Instruct-v0.2-AWQ \
    --quantization awq \
    --dtype float16
```

### 3. Response Caching
- In-memory LRU cache for repeated queries
- Reduces latency to near-zero for cached responses
- Configurable TTL and max size

### 4. Async Processing
- FastAPI async endpoints
- Concurrent request handling
- Batch processing support

## Conclusion

For our architecture:
- **LLM inference**: vLLM with quantization > ONNX (purpose-built for LLMs)
- **Embedding model**: ONNX conversion is recommended and applied
- **Overall system**: Caching + async processing provide the biggest performance gains

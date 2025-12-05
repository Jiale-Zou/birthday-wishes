import torch
from transformers import (AutoConfig,
                          AutoTokenizer,
                          AutoModelForCausalLM,
                          TextIteratorStreamer,
                          GenerationConfig,
                            BitsAndBytesConfig,
                          )
from peft import PeftModel
import os

MODEL_DIR = r"..\Qwen\Qwen2.5-0.5B-Instruct"  # 原始模型路径
FINETUNE_DIR = r"..\Qwen\Finetune-Qwen2.5-0.5B-Instruct"      # 微调模型保存路径
SAVE_DIR = r'..\Qwen\LoRA-Merge-Qwen2.5-0.5B-Instruct' # 合并模型保存路径
# ----------------------
# 配置参数（与训练时一致）
# ----------------------
# 1）载入预训练模型
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    use_fast=True,
    trust_remote_code=True,
    model_max_length=1647,
    padding_side="right", # 即token补齐长度时0的填充位置，默认为right
)
print("Tokenizer Load Success!")

config = AutoConfig.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    config=config, # 用pre_trained模型的参数加载（包含一些模型信息如结构，tokenizer）
    trust_remote_code=True,
    torch_dtype=torch.bfloat16, # 训练时指定了反量化后推理的精度，因此应该使用该全精度
    # 不要加量化参数quantization_config，因为推理时才用，合并时就是简单相加
)
print('origin config =', model.config)

# 2）模型合并
merged_model = PeftModel.from_pretrained(model, os.path.join(FINETUNE_DIR, "checkpoint-73000"))
# 合并并卸载适配器
## 1. 合并权重W_merged = W + A * B * alpha
## 2. 卸载适配器：删除A、B矩阵
## 3. 恢复原始模型架构：移除LoRA层
merged_model = merged_model.merge_and_unload()
print('merge config =', merged_model.config)


# 3）保存模型
print(f"Saving the target model to {SAVE_DIR}")
merged_model.save_pretrained(SAVE_DIR)
tokenizer.save_pretrained(SAVE_DIR)
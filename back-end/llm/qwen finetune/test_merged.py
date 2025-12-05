import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import BitsAndBytesConfig
import random
import numpy as np
import sys

# ----------------------
# 设置随机种子以确保可复现性
# ----------------------
def set_seed(seed):
    random.seed(seed)  # 设置 Python 随机种子
    np.random.seed(seed)  # 设置 NumPy 随机种子
    torch.manual_seed(seed)  # 设置 PyTorch CPU 随机种子
    torch.cuda.manual_seed_all(seed)  # 设置 PyTorch GPU 随机种子
    # 确保 CuDNN 使用确定性算法
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
# 设置固定的随机种子
SEED = 42
set_seed(SEED)

# ----------------------
# 配置参数（与训练时一致）
# ----------------------
MODEL_NAME = r"D:\PPrograms\Python\Model Finetune\Qwen2.5-0.5B\ShiPu\Qwen\LoRA-Merge-Qwen2.5-0.5B-Instruct"
SAVE_DIR = r"D:\PPrograms\Python\Model Finetune\Qwen2.5-0.5B\ShiPu\Qwen\LoRA-Merge-Qwen2.5-0.5B-Instruct"

# 量化配置（与训练时一致）
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True, # 启用4位量化
    bnb_4bit_quant_type="nf4", # 使用的4位量化算法位nf4
    bnb_4bit_compute_dtype=torch.bfloat16, # 量化到高精度时的精度
)

# ----------------------
# 加载分词器
# ----------------------
tokenizer = AutoTokenizer.from_pretrained(
    SAVE_DIR,  # 从保存路径加载分词器
    trust_remote_code=True,
    model_max_length=1647,
    padding_side="right"
)

# ----------------------
# 加载基础模型
# ----------------------
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,  # 加载原始 Qwen2.5-0.5B-Instruct 模型
    device_map="auto",
    quantization_config=bnb_config,
    # trust_remote_code=True
)


# 确保模型处于评估模式
model.eval()

# ----------------------
# 推理函数（与原始代码一致）
# ----------------------
def generate_response(query):
    prompt = (
        f"<|im_start|>system\n你是一个专业的厨师，你会做很多菜。用户报上自己所需的菜名后，你可以把做菜所需要的原料，以及做菜的方法告诉用户<|im_end|>\n"
        f"<|im_start|>user\n{query}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    outputs = model.generate(
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],  # 显式传递 attention_mask
        max_new_tokens=1000,
        temperature=0.5,
        top_p=0.8,
        do_sample=True,
        # repetition_penalty=1.2,
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True).split("assistant\n")[-1]

# ----------------------
# 测试推理
# ----------------------
if __name__ == '__main__':
    query = sys.argv[1]
    response = generate_response(query)
    print(response)
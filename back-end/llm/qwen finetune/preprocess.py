import os
from datasets import load_dataset
import re

DATASET_PATH = r"..\data"  # 数据集路径
MODEL_NAME = r"..\Qwen\Qwen2.5-0.5B-Instruct"      # 模型名称（会自动从ModelScope下载）
SAVE_PATH = r"..\Qwen\Finetune-Qwen2.5-0.5B-Instruct"  # 微调后模型保存路径

# 对每一条数据的处理方法
def format_instruction(example):
    # 处理 question 字段（列表）
    question = example['question']
    if isinstance(question, list) and len(question) > 0:
        question = question[0] # 提取第一个问题
    question = re.sub(r'\n+', '', question).strip()

    # 处理 answer 字段（列表）
    answer = example['answer']
    if isinstance(answer, list) and len(answer) > 0:
        answer = answer[0]  # 提取第一个答案
    answer = re.sub(r'\n+', '\n', answer).strip()  # 清理多余换行符

    ''' Qwen2.5的标准问答模板，建议采用，因为预训练就是这个模板 '''
    return {
        "text": f"<|im_start|>system\n你是一个专业的厨师，你会做很多菜。用户报上自己所需的菜名后，你可以把做菜所需要的原料，以及做菜的方法告诉用户<|im_end|>\n"
                f"<|im_start|>user\n{question}<|im_end|>\n"
                f"<|im_start|>assistant\n{answer}<|im_end|>"
    }

# 使用json读取方式
dataset = load_dataset(
    "json",
    data_files={
        "train": os.path.join(DATASET_PATH, "QA.json"),
    }
)
dataset = dataset.map(format_instruction, remove_columns=dataset["train"].column_names)
print("Train dataset samples:")
for i, text in enumerate(dataset["train"].select(range(5))["text"]):
    print(f"样本 {i}: {text}\n{'-'*50}")

dataset.save_to_disk(DATASET_PATH)  # 保存预处理后的数据集(保存为Arrow格式（高效二进制格式）)

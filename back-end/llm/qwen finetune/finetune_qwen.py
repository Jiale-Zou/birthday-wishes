import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig,
)
from peft import LoraConfig, TaskType, get_peft_model
from trl import SFTTrainer


DATASET_PATH = r"..\data"  # 数据集路径
MODEL_PATH = r"..\Qwen\Qwen2.5-0.5B-Instruct"      # 模型名称（会自动从ModelScope下载）
SAVE_PATH = r"..\Qwen\Finetune-Qwen2.5-0.5B-Instruct"  # 微调后模型保存路径
# 加载pretrained_model时指定的参数
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True, # 启用4位量化
    bnb_4bit_quant_type="nf4", # 使用的4位量化算法位nf4
    bnb_4bit_compute_dtype=torch.bfloat16, # 反量化到高精度时的精度
)

## 加载数据
dataset = load_dataset(
    path=DATASET_PATH,
    data_files={
        'train': [os.path.join(DATASET_PATH, 'train', f'data-0000{i}-of-00004.arrow') for i in range(4)],
    },
    streaming=True,  # 启用流式模式(避免内存爆炸)
)


## 加载 tokenizer
'''
从 MODEL_PATH读取 tokenizer_config.json
加载 vocab.json、merges.txt等文件
返回配置好的分词器对象
使用：tokenizer.encode(ls_s)返回token_ids，tokenizer.decode(ls_ids)返回解码的输入文本
'''
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    use_fast=False, # 使用快速实现(True（Rust加速）)
    trust_remote_code=True, # 信任自定义代码(True（用于新模型）)
    model_max_length=1647, # 输出序列token的最大长度，不然就截断
)
print(f"原始 pad_token: {tokenizer.pad_token}, pad_token_id: {tokenizer.pad_token_id}")
# lengths = [len(tokenizer.encode(sample["text"])) for sample in dataset["train"]]
# print(f"Train dataset stats: Min length={min(lengths)}, Max length={max(lengths)}, Mean length={sum(lengths)/len(lengths)}")


## 加载半精度模型
'''
torch.float32(FP32) 4字节
torch.float16(FP16) 2字节
torch.int8  1字节
'''
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    quantization_config=bnb_config,
)

## 设置LoRA参数
'''
不同任务类型的LoRA再模型的应用部分不同
TaskType.CAUSAL_LM          # 因果语言模型（如 GPT、Qwen）
TaskType.SEQ_2_SEQ_LM       # 序列到序列模型（如 T5、BART）  
TaskType.TOKEN_CLS          # 令牌分类（如 NER、词性标注）
TaskType.SEQ_CLS            # 序列分类（如情感分析）
TaskType.QUESTION_ANS       # 问答任务
TaskType.FEATURE_EXTRACTION # 特征提取
'''
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], # 分别对应MHA和MLP中参数
    inference_mode=False, # 训练模式
    r=2, # Lora 秩
    lora_alpha=6, # 实际为lora_alpha/r，即实际为3
    lora_dropout=0.1, # Dropout 比例
    # bias = False, # 不添加偏置项
)
model = get_peft_model(model, lora_config)

## 设置模型训练参数
args = TrainingArguments(
    output_dir=SAVE_PATH,
    per_device_train_batch_size=4, # 单个GPU处理的样本数
    gradient_accumulation_steps=2, # 累积多个小批次的梯度再更新
    # per_device_eval_batch_size=8,    # 评估批大小
    # eval_steps=200,                  # 评估频率
    warmup_steps = 5000,                # 预热步数
    # weight_decay=0.01               # 权重衰减
    logging_steps=2000, # 每多少步记录一次日志
    max_steps=73000, # 使用流式加载，就得告诉模型要运行多少步
    save_steps=20000, # 多少步保存一次模型
    learning_rate=1e-4, # 参数学习率
    # save_on_each_node=True, # 再每个分布式节点上都保存模型
    gradient_checkpointing=True # 梯度检查点：前向时保存结果，后向梯度时直接用，速度快；而True则前向时不保存结果，后向时再算，节约内存
)


## 定义SFT训练器
'''
DataCollatorForLanguageModeling: 将多个不同长度的样本组合成一个批次，并自动处理填充和标签生成
①假设有两个不同长度的样本，tokenize后为：sample1 = {"input_ids": [1, 2, 3, 4]}；sample2 = {"input_ids": [5, 6, 7, 8, 9, 10]}
②填充和mask后：batch = {
    "input_ids": [
        [1, 2, 3, 4, 0, 0],      # 样本1 + 填充
        [5, 6, 7, 8, 9, 10]      # 样本2
    ],
    "attention_mask": [
        [1, 1, 1, 1, 0, 0],      # 1=真实token，0=填充
        [1, 1, 1, 1, 1, 1]
    ]
}
③生成语言模型标签（要预测的标签）--> 根据前一个词预测后一个词，适合：GPT、Qwen等自回归模型
1）未启用掩码语言模型时mlm=False
batch["labels"] = [
    [2, 3, 4, 0, -100, -100],    # 样本1的标签
    [6, 7, 8, 9, 10, -100]       # 样本2的标签
]
2）启用掩码语言模型时mlm=True --> 根据上下文预测被掩盖的词，适合：BERT等双向模型
# 输入: [1, 2, [MASK], 4, 5]  # 随机掩盖某些token
# 标签: [-100, -100, 3, -100, -100]  # 只预测被掩盖的位置（-100表示不计算损失）
'''
# 可以自定义函数传入参数formatting_func，指定生成的标签
trainer = SFTTrainer(
    model=model,
    args=args,
    train_dataset=dataset["train"],
    data_collator=DataCollatorForLanguageModeling(
        tokenizer=tokenizer, # 必需：用于填充和截断
        mlm=False, # 是否进行掩码语言模型训练
        pad_to_multiple_of=8 # 现代GPU对8的倍数的张量有内存对齐优化，能加快数据处理速度
    )
)
trainer.train()

tokenizer.save_pretrained(SAVE_PATH)
model.save_pretrained(SAVE_PATH)
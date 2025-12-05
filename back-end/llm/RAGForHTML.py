from langchain_chroma import Chroma
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import re
import subprocess
import sys

# 1.自定义本地embedding模型
embedding_model = HuggingFaceEmbeddings(model_name='D:\\Application\\LLM\\Embedding\\Qwen3-Embedding-0.6B')
# 2.实例化一个向量数据库
vector_store = Chroma('receipe', embedding_model) # collection可以理解为表名，其管理单位就是collection
# 3.查询：可返回分数，且chromadb里分数越低相似度越高
# print(vector_store.similarity_search_with_score('hello', k=1))
# 3.将chroma变为Runnable对象，因为只有Runnable对象才能放在chain中
retriver = RunnableLambda(vector_store.similarity_search).bind(k=1) # 表示只返回topk个
# print(retriver.batch(['hello', 'ok']))

model_filter = ChatOllama(base_url="http://localhost:11434", model="qwen3:4b") # 用来预加工问题的模型

class Prompt_Func:
    ''' 管理prompt和runnable函数的类 '''

    python_path = "D:\\PPrograms\\Python\\Model Finetune\\Qwen2.5-0.5B\\.venv\\Scripts\\python.exe"
    shipu_script = "D:\\PPrograms\\Python\\Model Finetune\\Qwen2.5-0.5B\\ShiPu\\qwen_finetune\\test_merged.py"

    message1 = """
    请将下面这个问题进行预处理，要求：
    1.判断是否询问了某道食物怎么做或者是否让你推荐了吃什么，返回是或否，在返回格式中的占位符为<TF>；
    2.若询问了某道食物怎么做，或者让你推荐吃什么请你推荐相应食物，返回该食物名，在返回格式中的占位符为<NAME>；
    3.若还有其他问题，则对问题进行回答，注意，3中只用回答有关2中的食物的做法之外的问题。在返回格式中的占位符为<ANS>。
    问题为：
    {question}。
    历史的对话记录为（可能没有历史对话记录，若有，则每个[]内的内容为一条问答，[]内的usr为用户，ass为小助手
    ，<>内的内容为对应角色说的话）：
    {history}。
    返回的格式为：
    <flag><TF></flag>
    <food><NAME></food>
    <answer><ANS></answer>
    """

    message2 = """
    参考提供的上下文仅回答这个问题，若无上下文则凭你的也有知识回答，暂时回答不了则直接表明你不能回答即可。
    {question}
    上下文：
    {context}
    """

    # 创建处理输入的函数
    @classmethod
    def prepare_input(cls, data):
        """准备输入数据，将query和history分开"""
        if isinstance(data, dict):
            # 如果已经是字典格式，直接返回
            return data
        elif isinstance(data, tuple) and len(data) == 2:
            # 如果是(query, history)元组
            return {'question': data[0], 'history': data[1]}
        else:
            # 默认情况，只有query没有history
            return {'question': data, 'history': ''}

    # 交给第一个模型，对用户的问题进行修正并回答与食物不相关的问题
    @classmethod
    def extract_answer(cls, model_output):
        content = model_output.content if hasattr(model_output, 'content') else str(model_output)

        flag_match = re.search('<flag>(.*?)</flag>', content)
        food_match = re.search('<food>(.*?)</food>', content)
        answer_match = re.search('<answer>(.*?)</answer>', content)

        flag = flag_match.group(1) if flag_match else ""
        food = food_match.group(1) if food_match else ""
        answer_text = answer_match.group(1) if answer_match else ""

        return {
            'flag': flag,
            'food': food,
            'ans': answer_text
        }

    @classmethod
    def food_answer(cls, model_output_dict):
        if model_output_dict['flag'] == "是":
            context = '' # 可用retrive检索返回相关资料文本
            prompt = cls.message2.format(question=(model_output_dict['food']+'怎么做'), context=context)

            result = subprocess.run([cls.python_path, cls.shipu_script, prompt],
                           capture_output=True,
                           text=True,
                           encoding="utf-8",
                           ) # 调用未部署的本地微调shipu模型回答食物问题

            def clean_ansi_codes(text): # 清理ANSI转义序列
                ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
                return ansi_escape.sub('', text)

            if result.returncode == 0:
                ans = ''.join([model_output_dict['food'], '的做法为：', clean_ansi_codes(result.stdout), model_output_dict['ans']]).strip()
            else:
                ans = ''.join(['抱歉，我暂时不知道', model_output_dict['food'], '怎么做。\n', model_output_dict['ans']]).strip()
            return ans
        else:
            return model_output_dict['ans']

runnable_prepare_input = RunnableLambda(Prompt_Func.prepare_input)
runnable_extract_answer = RunnableLambda(Prompt_Func.extract_answer)
runnable_food_answer = RunnableLambda(Prompt_Func.food_answer)

prompt_temp = ChatPromptTemplate.from_messages([('human', Prompt_Func.message1)])

# RunnablePassthrough允许我们将用户的问题之后传递给prompt和Model
# chain = {'question': RunnablePassthrough(), 'context': retriver} | prompt_temp | model
chain = runnable_prepare_input | prompt_temp | model_filter | runnable_extract_answer | runnable_food_answer

if __name__=='__main__':
    query = sys.argv[1]
    history = sys.argv[2] if len(sys.argv) > 2 else ""
    resp = chain.invoke((query, history))

    print(resp)
# main.py: 哈耶克研究委员会主应用入口
from query_handler import handle_query  # 导入查询处理函数

def main():
    print("欢迎使用哈耶克研究委员会！")
    print("请输入中文问题（例如：'哈耶克如何看待中央计划经济？'），输入 'quit' 退出。")
    
    while True:
        question = input("\n您的提问：").strip()
        if question.lower() == 'quit':
            print("感谢使用！再见。")
            break
        
        if not question:
            print("请输入有效问题。")
            continue
        
        try:
            print("委员会正在分析中...（这可能需要几秒钟）")
            report = handle_query(question)
            print("\n" + "="*50)
            print(report)
            print("="*50)
        except Exception as e:
            print(f"处理出错：{e}。请检查 Ollama 是否运行、API key 是否有效，或索引是否构建。")

if __name__ == "__main__":
    main()
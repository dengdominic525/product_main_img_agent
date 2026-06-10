"""
电商主图视觉文案  Deep Agent
输入: 产品信息+产品主图，自动执行: 分析→文案→生图→保存
"""
import sys
import os
import re
import time

try:
    from dotenv import load_dotenv
    from langchain.tools import tool
    from langchain_openai import ChatOpenAI
    from openai import OpenAI
    from deepagents import create_deep_agent
    import requests
    import base64
except ImportError as e:
    print(f"错误: 缺少依赖模块 - {e}")
    print("")
    print("请使用以下命令安装依赖：")
    # 所使用的本地的python路径
    print('"C:\\Users\\120778\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" -m pip install langchain langchain_openai deepagents python-dotenv requests')
    print("")
    print("或者直接运行 run_agent.bat 脚本")
    sys.exit(1)

load_dotenv()
# 生图模型和llm模型
api_key = os.getenv("DOUBAO_API_KEY")
llm_api_url = os.getenv("LLM_API_URL")
llm_model = os.getenv("LLM_MODEL")
# 生图模型用的seedance，修改模型名称请移步工具：generate_images
seedance_api_url = os.getenv("SEEDANCE_API_URL")
# 图床用的公开免费的
image_hosting_api_url = os.getenv("IMAGE_HOSTING_API_URL")
image_hosting_api_key = os.getenv("IMAGE_HOSTING_API_KEY")
# 创建一个llm实体
image_client = OpenAI(
    api_key=api_key,
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)

llm = ChatOpenAI(
    api_key=api_key,
    base_url=llm_api_url,
    model_name=llm_model,
    temperature=0.7
)

# ============================================================
# 自定义工具
# ============================================================
@tool
def read_product_info(file_path: str) -> str:
    """读取指定路径的产品信息文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"产品信息读取成功：\n{content}"
    except Exception as e:
        return f"读取文件失败: {str(e)}"

@tool
def upload_to_image_hosting(local_path: str) -> str:
    """将本地图片上传到图床获取公开URL"""
    try:
        path = os.path.abspath(local_path)
        if not os.path.exists(path):
            return f"错误: 文件不存在 {local_path}"
        
        with open(path, "rb") as f:
            data = f.read()
        
        suffix = os.path.splitext(path)[1].lower()
        content_type = "image/jpeg" if suffix in [".jpg", ".jpeg"] else "image/png"
        
        resp = requests.post(
            image_hosting_api_url,
            files={"source": (os.path.basename(path), data, content_type)},
            data={"key": image_hosting_api_key, "format": "json"},
            timeout=30,
        )
        result = resp.json()
        
        if result.get("status_code") == 200:
            url = result["image"]["url"]
            return url
        return f"上传失败: {result.get('status_txt', '未知错误')}"
    except Exception as e:
        return f"上传图片失败: {str(e)}"

@tool
def analyze_selling_points(product_info: str) -> str:
    """分析产品信息并提取核心卖点"""
    prompt = f"""请分析以下产品信息，提取至少5个核心卖点或者必卖理由：
    参考思路：
    -目标人群 → 痛点 → 解决方案 → 利益翻译 → 信任证据 → 优先级 → 适用模块
    规则：
    - 每条必须基于可验证事实
    - 优先级: ★★★★★ 核心差异 | ★★★★ 重要辅助 | ★★★ 补充
    - 必须合规：无绝对化用语（禁用"最""第一""唯一"等）
    - 输出后暂停，必须等用户回复"确认"或"ok"才能继续！
    - 如果用户提出修改，调整后再次等待确认

    产品信息：
    {product_info}
    
    请按照以下格式输出：
    1. 卖点1
    2. 卖点2
    3. 卖点3
    4. 卖点4
    5. 卖点5
    """
    response = llm.invoke([{'role': 'user', 'content': prompt}])
    return response.content

@tool
def generate_image_plans(selling_points: str) -> str:
    """根据产品卖点生成5张电商主图的策划方案"""
    prompt = f"""根据以下产品卖点，生成5张电商主图的方案：
    策划方向参考：
    图1 首图: 产品居中 + 核心卖点标题 + 价格
    图2 痛点: 左右对比（问题 vs 解决）
    图3 差异化: 产品优势对比展示
    图4 场景: 三宫格使用场景
    图5 CTA: 产品全家福 + 价格 + 行动号召
    
    产品卖点：
    {selling_points}
    
    请为每个主图提供详细的策划，包括：
    - 图片主题
    - 构图方式
    - 展示内容
    - 营销文案
    
    输出格式：
    【主图1】主题：xxx
    构图：xxx
    展示内容：xxx
    文案建议：xxx
    
    【主图2】主题：xxx
    ...
    """
    response = llm.invoke([{'role': 'user', 'content': prompt}])
    return response.content



@tool
def generate_image_prompts(plans: str, ratio: str, image_url: str = None, product_info: str = "") -> str:
    """根据主图策划方案和图片比例生成AI绘画提示词"""
    platform_ratios = {
        '淘宝': '1:1',
        '京东': '1:1',
        '拼多多': '1:1',
        '抖音': '9:16',
        '小红书': '3:4'
    }
    
    actual_ratio = platform_ratios.get(ratio, ratio)
    
    reference_note = ""
    if image_url:
        reference_note = f"""
参考图片URL（白底产品图，用于主体保持一致）：{image_url}
重要：生成的图片必须参考此图片中的产品主体形状和外观，保持产品主体不变，只改变背景、场景、构图、角度、风格、光线等。"""
    
    # Extract price info from product_info
    price_note = ""
    if product_info.strip():
        price_lines = [l.strip() for l in product_info.split("\n") if any(k in l for k in ["价格", "售价", "价", "\u00a5", "\uffe5", "元", "price", "Price"])]
        if price_lines:
            price_info = "\uff1b".join(price_lines)
            price_note = f"\n注意：产品价格信息为\u300c{price_info}\u300d，生成的主图提示词中需要在画面中体现价格标签、促销价签或文案，突出价格优势。"
        else:
            price_note = f"\n完整产品信息：\n{product_info}\n注意：生成的主图提示词中需要在画面中清晰展示产品价格信息。"

    
    prompt_text = f"""根据以下主图策划方案和图片比例，生成5个详细的AI绘画提示词：
    
策划方案：
{plans}

图片比例：{actual_ratio}
{reference_note}

请生成5个不同的提示词，每个提示词描述一张完整的电商主图。
5个提示词必须展现不同的主题内容，包括不同的场景、背景、角度或构图方式，不能雷同。
{'如果有参考图片，必须保持参考图中的产品主体不变，只改变背景/场景/构图/光线/风格。' if image_url else ''}

请严格按照以下格式输出，每个提示词单独一行，不要带序号，不要带分号：
第一个提示词的内容...
第二个提示词的内容...
第三个提示词的内容...
第四个提示词的内容...
第五个提示词的内容...

要求：
- 符合电商主图风格，突出产品卖点\n- 提示词中需包含价格标签/促销文案/价格信息展示的明确描述
- 每个提示词需包含：产品描述、场景背景、光线效果、构图方式、风格氛围
- 每个提示词只输出内容本身，不要加序号前缀
{' - 参考图片中有产品的白底展示，提示词中应说明保持该产品主体的形状和外观不变' if image_url else ''}
"""
    response = llm.invoke([{'role': 'user', 'content': prompt_text}])
    
    # Parse response into individual prompts
    lines = response.content.strip().split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Remove common prefixes: "1.", "1、", "1)", "提示词1:", "第一个提示词：", etc.
        line = re.sub(r'^[\d]+[.、\)）\s]*', '', line)
        line = re.sub(r'^提示词[\d]*[：:]\s*', '', line)
        line = re.sub(r'^第[一二三四五六七八九十\d]个提示词[：:]\s*', '', line)
        line = line.strip()
        # Only keep lines that look like actual prompts (reasonable length)
        if len(line) > 10:
            cleaned.append(line)
    
    # Ensure exactly 5 prompts
    if len(cleaned) < 5:
        # Try splitting by other separators if line-based parsing didn't work
        if ';' in response.content:
            cleaned = [p.strip() for p in response.content.split(';') if p.strip() and len(p.strip()) > 10]
        elif '。' in response.content and len(cleaned) < 5:
            # Some models output in paragraph form - take first 5 sentences
            sentences = re.split(r'[。！？\n]', response.content)
            for s in sentences:
                s = s.strip()
                if s and len(s) > 10:
                    cleaned.append(s)
    
    # Pad to exactly 5 if still not enough
    fallbacks = [
        "产品主体居中展示，质感清晰，背景为渐变纯色，光线柔和均匀，突出产品主体",
        "产品在自然生活场景中展示，温暖的日光氛围，背景虚化，突出产品质感",
        "产品主体在室内场景中展示，环境简洁有格调，侧光照明突出产品轮廓和细节",
        "产品在工作室场景中展示，纯色背景，多角度布光凸显产品立体感和质感",
        "产品在创意场景中展示，独特的构图视角，色彩搭配和谐有吸引力"
    ]
    while len(cleaned) < 5:
        cleaned.append(fallbacks[len(cleaned)])
    
    return ';'.join(cleaned[:5])


@tool
def generate_images(prompts: str, reference_image_url: str = None) -> str:
    """根据提示词列表调用图片生成服务生成图片，每个提示词分开独立调用API"""
    prompt_list = [p.strip() for p in prompts.split(';') if p.strip()]
    if not prompt_list:
        return "错误: 没有有效的提示词"
    
    image_urls = []
    print(f"\n========== 开始生图：共 {len(prompt_list[:5])} 张图片 ==========")
    
    for i, prompt in enumerate(prompt_list[:5], 1):
        print(f"\n--- [第 {i}/5 张] 正在生成...")
        print(f"    提示词: {prompt[:80]}..." if len(prompt) > 80 else f"    提示词: {prompt}")
        
        try:
            extra_body = {
                "sequential_image_generation": "disabled",
                "watermark": True,
            }
            if reference_image_url:
                extra_body["image"] = reference_image_url
            
            response = image_client.images.generate(
                model="doubao-seedream-4-0-250828",
                prompt=prompt,
                size="2K",
                response_format="url",
                extra_body=extra_body,
            )
            
            if response.data:
                img_url = response.data[0].url
                image_urls.append(img_url)
                print(f"    ✓ 第 {i} 张生成成功")
            else:
                print(f"    ✗ 第 {i} 张生成失败: 无返回数据")
                image_urls.append(f"生成失败: 无返回数据")
        except Exception as e:
            print(f"    ✗ 第 {i} 张生成失败: {str(e)}")
            image_urls.append(f"生成失败: {str(e)}")
        
        # Add delay between calls to avoid rate limiting
        if i < len(prompt_list[:5]):
            print(f"    等待 2 秒后继续下一张...")
            time.sleep(2)
    
    success_count = len([u for u in image_urls if u.startswith('http')])
    print(f"\n========== 生图完成: {success_count}/{len(prompt_list[:5])} 张成功 ==========")
    return ';'.join(image_urls)


@tool
def save_images(image_urls: str, output_dir: str = "./output_images") -> str:
    """下载生成的图片并保存到本地目录"""
    os.makedirs(output_dir, exist_ok=True)
    url_list = [url.strip() for url in image_urls.split(';') if url.strip()]
    saved_files = []
    
    for i, url in enumerate(url_list, 1):
        if url.startswith('http'):
            try:
                response = requests.get(url)
                response.raise_for_status()
                
                filename = f"main_image_{i}.png"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                saved_files.append(filepath)
            except Exception as e:
                saved_files.append(f"图片{i}保存失败: {str(e)}")
        else:
            saved_files.append(f"图片{i}: {url}")
    
    return "\n".join(saved_files)

# 挂载工具列表
tools = [
    read_product_info,
    upload_to_image_hosting,
    analyze_selling_points,
    generate_image_plans,
    generate_image_prompts,
    generate_images,
    save_images
]
# 系统提示词
system_prompt = """你是一个专业的产品主图生成智能体，负责协助用户生成高质量的电商产品主图。

核心能力：使用用户提供的白底产品图作为参考，再生成的每一张主图中保持产品主体不变（主体保持一致），只改变背景、场景、构图和风格。

工作流程：
1. 首先读取用户提供的产品信息文件
2. 读取白底图并上传到图床获取公开URL
3. 分析产品卖点并总结
4. 生成5张主图策划方案供用户确认
5. 根据用户选择的图片比例生成提示词（传入白底图URL和包含价格的产品信息，告知AI需要保持产品主体不变并在图中显示价格）
6. 调用图片生成服务（传入白底图URL作为参考图，确保主体保持）
7. 保存结果并展示给用户，询问用户满意度

注意事项：
- 白底图是参考图，用于保持产品主体在所有生成图当中一致
- 每次生成都是分开独立的API调用，生成5张不同的图片
- 如果生成效果不理想，根据用户反馈调整提示词重新生成

请按照以下步骤进行：
- 先询问用户产品信息文件的路径和白底图路径
- 上传白底图到图床获取公开URL
- 分析完成后展示卖点总结，询问用户确认
- 如果用户需要修改，重新分析
- 生成5张主图策划方案
- 确认后询问图片比例或平台（如淘宝、京东、拼多多、抖音、小红书等）
- 生成提示词（传入白底图URL用于主体保持，同时传入产品信息product_info确保价格信息不丢失）并调用生图服务（传入白底图URL作为参考图）
- 保存图片后询问用户是否满意
- 如果不满意，根据用户反馈修改提示词重新生成
- 重要：必须确保生成了5张不同的图片，如果生成结果中有失败信息，告知用户哪些成功哪些失败
- 每次生图API调用都是分开独立的，所以5张图会依次生成，请耐心等待进度提示

请使用提供的工具来完成任务。"""

agent = create_deep_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt
)

def _messages_to_dicts(msgs):
    """Convert message objects to dict list, keeping only human/ai messages."""
    result = []
    for m in msgs:
        if isinstance(m, dict):
            role = m.get("role", "")
            if role in ("user", "assistant"):
                result.append({"role": role, "content": m.get("content", "")})
        else:
            try:
                if m.type in ("human", "ai"):
                    result.append({"role": "assistant" if m.type == "ai" else "user", "content": m.content})
            except AttributeError:
                pass
    return result


def main():
    print("欢迎使用产品主图生成智能体！")
    print("请按照提示提供产品信息文件和白底图路径。")
    print("输入 'exit' 退出。")
    print("-" * 50)
    
    messages = []  # Accumulate conversation history
    
    while True:
        try:
            user_input = input("你: ")
            if user_input.lower() == "exit":
                print("再见！")
                break
            
            if not user_input.strip():
                print("AI: 请输入有效的内容~")
                continue
            
            messages.append({"role": "user", "content": user_input})
            
            result = agent.invoke({"messages": messages})
            
            # Handle different return types from deepagents
            if isinstance(result, dict):
                ai_response = result["messages"][-1].content
                # Keep accumulated history from the result for next turn
                messages = _messages_to_dicts(result["messages"])
            elif hasattr(result, "content"):
                ai_response = result.content
                messages.append({"role": "assistant", "content": ai_response})
            else:
                ai_response = str(result)
                messages.append({"role": "assistant", "content": ai_response})
            
            print(f"AI: {ai_response}")
            print()
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"AI: 遇到了一点小问题，请重试~ ({str(e)})")
            print()

if __name__ == "__main__":
    main()



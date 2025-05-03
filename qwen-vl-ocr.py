import os
import base64
import requests
from mimetypes import guess_type
from dotenv import load_dotenv
load_dotenv()

class ImageProcessor:
    """图像处理核心类"""
    def __init__(self):
        # 从环境变量初始化配置
        self.api_url = os.getenv("API_URL") or "https://api.siliconflow.cn/v1/chat/completions"
        self.model_name = os.getenv("MODEL_NAME") or "Pro/Qwen/Qwen2.5-VL-7B-Instruct"
        self.api_key = os.getenv("API_KEY")
        self.prompt = os.getenv("PROMPT") or "提取图片中的文字信息"
        # 路径配置
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_dir = os.getenv("IMAGE_DIR") or os.path.join(script_dir, "images")
        self.output_file = os.getenv("OUTPUT_FILE") or os.path.join(script_dir, "ocr_results.txt")
        
        # 参数校验
        if not self.api_key:
            raise ValueError("未配置API_KEY，请在.env文件中填写")
        if not os.path.isdir(self.image_dir):
            raise FileNotFoundError(f"图片目录不存在，请创建目录")

    def process_all_images(self):
        """批量处理图片并保存结果"""
        image_files = self._get_supported_images()
        if not image_files:
            print(f"{self.image_dir} 中没有支持的图片文件")
            return

        # 确保输出目录存在
        output_dir = os.path.dirname(self.output_file)
        os.makedirs(output_dir, exist_ok=True)

        with open(self.output_file, "w", encoding="utf-8") as f:
            for idx, img_path in enumerate(image_files, 1):
                self._process_single_image(idx, img_path, f, len(image_files))

    def _get_supported_images(self):
        """获取支持的图片文件列表"""
        supported_formats = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        return sorted(
            [os.path.join(self.image_dir, f) 
             for f in os.listdir(self.image_dir) 
             if f.lower().endswith(supported_formats)],
            key=lambda x: os.path.basename(x).lower()
        )

    def _process_single_image(self, idx, img_path, file_handle, total):
        """处理单张图片并写入结果"""
        print(f"正在处理 ({idx}/{total}) {os.path.basename(img_path)}...")
        result = self._get_image_description(img_path)
        if result:
            file_handle.write(f"{result}\n\n\n")
            file_handle.flush()
            os.fsync(file_handle.fileno())

    def _get_image_description(self, image_path):
        """获取单张图片描述"""
        try:
            image_data = self._encode_image(image_path)
            mime_type = guess_type(image_path)[0] or "image/jpeg"
            response = self._call_api(image_data, mime_type)
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"处理 {os.path.basename(image_path)} 失败: {str(e)}")
            return None

    def _encode_image(self, image_path):
        """Base64编码图像"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"图片读取失败: {e}")

    def _call_api(self, image_data, mime_type):
        """调用API接口"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{mime_type};base64,{image_data}"
                    }}
                ]
            }],
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.8,
            "response_format": {"type": "text"}
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API请求失败: {e}")
        except ValueError:
            raise RuntimeError("API返回数据解析失败")

def main():
    """程序入口"""
    try:
        processor = ImageProcessor()
        processor.process_all_images()
        print("处理完成，输出文件位置:", processor.output_file)
    except Exception as e:
        print(f"程序初始化失败: {str(e)}")

if __name__ == "__main__":
    main()

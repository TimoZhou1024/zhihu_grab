import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import json
import argparse
from src.util import insert_new_line, get_article_date, download_image, download_video, get_valid_filename

class ZhihuDownloader:
    def __init__(self, cookies):
        self.cookies = cookies
        self.session = requests.Session()
        self.user_agents = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.headers = {
            'User-Agent': self.user_agents,
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
            'Cookie': self.cookies
        }
        self.session.headers.update(self.headers)
        self.soup = None

    def check_url(self, url):
        """检查URL类型并调用相应的处理函数"""
        if not url.startswith("https://"):
            url = "https://" + url
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.content, "html.parser")
            
            if "有问题，就会有答案" in self.soup.text:
                raise ValueError("无效的Cookie，请提供正确的知乎Cookie")
            
            if "没有知识存在的荒原" in self.soup.text:
                raise ValueError("页面不存在")
            
            if "zhuanlan.zhihu.com" in url:
                return self.handle_article()
            elif "/answer/" in url:
                return self.handle_answer()
            elif "/zvideo/" in url:
                return self.handle_video()
            else:
                raise ValueError("不支持的URL类型")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求错误: {str(e)}")
    
    def handle_article(self):
        """处理知乎文章"""
        title_element = self.soup.select_one("h1.Post-Title")
        content_element = self.soup.select_one("div.Post-RichTextContainer")
        date = get_article_date(self.soup, "div.ContentItem-time")
        author = self.soup.select_one('div.AuthorInfo').find('meta', {'itemprop': 'name'}).get('content')
        
        return self.save_content(title_element, content_element, author, date)
    
    def handle_answer(self):
        """处理知乎回答"""
        title_element = self.soup.select_one("h1.QuestionHeader-title")
        content_element = self.soup.select_one("div.RichContent-inner")
        date = get_article_date(self.soup, "div.ContentItem-time")
        author = self.soup.select_one('div.AuthorInfo').find('meta', {'itemprop': 'name'}).get('content')
        
        return self.save_content(title_element, content_element, author, date)
    
    def handle_video(self):
        """处理知乎视频"""
        data = json.loads(self.soup.select_one("div.ZVideo-video")['data-zop'])
        date = get_article_date(self.soup, "div.ZVideo-meta")
        
        markdown_title = f"({date}){data['authorName']}_{data['title']}"
        folder_path = os.path.join(os.getcwd(), markdown_title)
        os.makedirs(folder_path, exist_ok=True)
        
        video_url = None
        script = self.soup.find('script', id='js-initialData')
        if script:
            data = json.loads(script.text)
            videos = data['initialState']['entities']['zvideos']
            for video_id, video_info in videos.items():
                if 'playlist' in video_info['video']:
                    for quality, details in video_info['video']['playlist'].items():
                        video_url = details['playUrl']
                        break
                    break
        
        if video_url:
            video_path = os.path.join(folder_path, f"{data['title']}.mp4")
            download_video(video_url, video_path, self.session)
        
        return markdown_title

    def save_content(self, title_element, content_element, author, date):
        """保存内容为Markdown文件"""
        title = title_element.text.strip() if title_element else "Untitled"
        markdown_title = get_valid_filename(f"({date}){title}_{author}")
        
        # 创建文件夹存放图片
        folder_path = os.path.join(os.getcwd(), markdown_title)
        os.makedirs(folder_path, exist_ok=True)
        
        if content_element:
            # 将 css 样式移除
            for style_tag in content_element.find_all("style"):
                style_tag.decompose()

            for img_lazy in content_element.find_all("img", class_=lambda x: 'lazy' in x if x else True):
                img_lazy.decompose()

            # 处理内容中的标题，并处理标题中的数学公式
            for header in content_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                header_level = int(header.name[1])
                header_text = header.get_text(strip=True)
                
                # 查找标题中的数学公式并添加 $$ 包裹
                for math_span in header.select("span.ztext-math"):
                    latex_formula = math_span['data-tex']
                    if latex_formula.find("$") == -1:  # 如果公式中没有 $ 符号
                        header_text = header_text.replace(latex_formula, f"${latex_formula}$")
                
                # # 使用正则表达式查找可能的数学公式并添加 $$ 包裹
                # # 常见的数学符号模式，如 \alpha, \beta, \lambda 等
                # header_text = re.sub(r'(\\[a-zA-Z]+)(?![a-zA-Z{])', r'$$\1$$', header_text)
                # # 处理括号中的数学符号，如 (λ), (\lambda)
                # header_text = re.sub(r'\((\\?[λαβγμσπθ])\)', r'($$\1$$)', header_text)
                
                # markdown_header = f"{'#' * header_level} {header_text}"
                # insert_new_line(self.soup, header, 1)
                # header.replace_with(markdown_header)

            # 处理图片
            for img in content_element.find_all("img"):
                try:
                    if 'src' in img.attrs:
                        img_url = img.attrs['src']
                        img_name = urllib.parse.quote(os.path.basename(img_url))
                        img_path = os.path.join(folder_path, img_name)
                        
                        # 处理图片URL后缀
                        for ext in ['.jpg', '.png', '.gif']:
                            index = img_path.find(ext)
                            if index != -1:
                                img_path = img_path[:index + len(ext)]
                                break
                        
                        # 下载图片
                        try:
                            download_image(img_url, img_path, self.session)
                            img["src"] = os.path.join(markdown_title, os.path.basename(img_path))
                        except Exception as e:
                            print(f"下载图片失败: {str(e)}")
                        
                        # 添加换行
                        insert_new_line(self.soup, img, 1)
                except Exception as e:
                    print(f"处理图片失败: {str(e)}")
                    continue

            # 处理图例
            for figcaption in content_element.find_all("figcaption"):
                insert_new_line(self.soup, figcaption, 2)
            
            # 提取并存储数学公式
            math_formulas = []
            math_tags = []
            for math_span in content_element.select("span.ztext-math"):
                latex_formula = math_span['data-tex']
                # 检查是否为多行公式环境
                if any(env in latex_formula for env in ['\\begin{align}', '\\begin{gathered}', '\\begin{matrix}']):
                    math_tags.append(latex_formula)
                    insert_new_line(self.soup, math_span, 1)
                    math_span.replace_with("@@MATH_FORMULA@@")
                elif latex_formula.find("\\tag") != -1:
                    math_tags.append(latex_formula)
                    insert_new_line(self.soup, math_span, 1)
                    math_span.replace_with("@@MATH_FORMULA@@")
                else:
                    math_formulas.append(latex_formula)
                    math_span.replace_with("@@MATH@@")
            
            # 生成Markdown内容
            content = md(content_element.decode_contents().strip())
            
            # 处理数学公式替换
            for formula in math_formulas:
                # 如果公式中包含 $ 则不再添加 $ 符号
                if formula.find('$') != -1:
                    content = content.replace("@@MATH@@", f"{formula}", 1)
                else:
                    content = content.replace("@@MATH@@", f"${formula}$", 1)

            for formula in math_tags:
                # 如果公式中包含 $ 则不再添加 $ 符号
                if formula.find("$") != -1:
                    content = content.replace("@@MATH\_FORMULA@@", f"{formula}", 1)
                else:
                    content = content.replace("@@MATH\_FORMULA@@", f"$${formula}$$", 1)
            
            markdown = f"# {title}\n\n**Author:** {author}\n\n{content}"
            
            # 保存Markdown文件
            md_path = os.path.join(os.getcwd(), f"{markdown_title}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown)
        
        return markdown_title

def main():
    # parser = argparse.ArgumentParser(description='下载知乎文章并转换为Markdown格式')
    # parser.add_argument('url', help='知乎文章、回答或视频的URL')
    # parser.add_argument('cookie', help='知乎的Cookie')
    # parser.add_argument('--output', '-o', help='输出目录，默认为当前目录', default='.')
    
    # args = parser.parse_args()
    
    url = "https://zhuanlan.zhihu.com/p/707443393"
    url = "https://www.zhihu.com/question/309343971"
    cookie = "_xsrf=9cHiYHYiMJKZpK7V47RyskEhPHEWsU5h; _zap=d13a2d5f-269f-44b8-8382-630364f12c4c; d_c0=K7NTpK47ShqPTn8DYm9NsTYJYmZCvx5PEzM=|1744438300; captcha_session_v2=2|1:0|10:1744441369|18:captcha_session_v2|88:WHFlQXhqOFFCbWJNMXZZVndvaGRBRFEwTDZiMzd4cDdxWS9pQWxaZEE5azNLbjdCUC9BRnhva2JpdCsxVnFhSw==|00617052bcca810e432210b765b4550350715bc6d5e631d93fb6eecd8899685a; captcha_ticket_v2=2|1:0|10:1744441378|17:captcha_ticket_v2|728:eyJ2YWxpZGF0ZSI6IkNOMzFfS3IuUjNndlVpV09mRDZBZUJmS2FKYmRRUFpzb2wxamtobVhUbjlCbVNrdmlZOVFibk1xenk1RHp6dXJubFY0UGhzRmIxQVQ4NU5McENoU1VQYnE0TnM0WkNyWkpBS2JHbXZLMU9qUTZWVTFZendWQ1VlQVZOdjZIeXhSOTBTNlk2c3NsR2VvYV9FS0lCd0IqMWpHUkNMWHhfQm9adGZJV3c5WXlFZUNzYW5ESVdLYzhSc1JzNlFTalhNSFk2UzN1VXVyWjJLb0d5cTBXTWRjVnBOREdLQ1VQeHJ3UmNXSnVXZ3BxcURNcmhPMUFEVlJycVRES1YzSEFEWmFVZVVITGlxb1BudUVNMENyckxrR3RNamw4NmE5RWtfQjhucHJDR1NMKlVjc0FDbnM0cF9sZDNxQk1TdEJqRDQydGdudHdzY1hXb1dsWDRRYlVsNnBDWTFnMy44eUMydEMqdm5hSnRSWGRtYUNBaFpUbzlhaFRiRFJTSU5RbEc5QmhzeFJKNEdWa2VZdkFUaDNuKmd5YkR6ZEx1UypVeF9lMEwqYkRad196X190Y2s1TVZwc3Ryd1NWLjZjbWhVNENRdXVYS1AqbG8wY1Nyc0JxLmNncDFodFRVTWlreUtBcTZxUnI2aE5SQWxzX01TdlloLjFMeHEyKjFnM1ZfVHAyNnFWdGJzcG9YQ1g3N192X2lfMSJ9|515ef6a6282eacdc851014fa3c55621ef39d3894365b12f691bc8dbb90b350c5; z_c0=2|1:0|10:1744472227|4:z_c0|92:Mi4xcGRnWkRnQUFBQUFyczFPa3JqdEtHaVlBQUFCZ0FsVk5JbDduYUFCcXMzNDZlUmZMZmJNZ2dyLXduMFdiMDZ0RnVB|c760d4386710ec8d3da4505514c25a8ffb094421cd53152f78189d66f0f10613; q_c1=f8924f060bd54e1f9dfa2acf902fc1c5|1744782110000|1744782110000; __zse_ck=004_dCeBOmiA9v/QFAFi7VAQI1AdQoGCqlk=vU48j5GL0F/QMfzl6ULyj0ofcpkW3ebLQFgQCCPPpdyp2SEzoJgQp5v=AqO943sTIYApgjo7x9mkqUZaYs3MIyqAxZWBbKtr-bPowq/8wJ6hEoRA2Bpwmg56lQ0dmh0IEdFpkg/duWG7EBmrZ8Kvn4Cu3zzI2TBWM4ddB3EgjHerja4fQXR40P5uHevVtMeK4SgtRS5nbWXBsfBBG+OVixS/IJoXgG/h8xKGY4WZJM5IyVQeg6ciI56eiNtbc13iSkAguyWWZZU8=; tst=r; SESSIONID=MOiDoFO6koccJIfeaC1M1a8C2b8XyE7RMqEZ7NnfYBk; BEC=f7bc18b707cd87fca0d61511d015686f"
    output = "output"
    
    try:
        # 切换到输出目录
        if not os.path.exists(output):
            os.makedirs(output)
        os.chdir(output)
        
        # 下载并转换内容
        downloader = ZhihuDownloader(cookie)
        output_name = downloader.check_url(url)
        print(f"下载完成！文件保存在: {os.path.abspath(output_name)}")
        
    except Exception as e:
        print(f"错误: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书帖子爬取脚本
支持单个或批量爬取用户提供的帖子链接
"""

import json
import os
import sys
from typing import List, Optional
from loguru import logger
from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.common_util import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx


class PostSpider:
    """帖子爬虫类"""
    
    def __init__(self, cookies_str: str = None):
        """
        初始化爬虫
        :param cookies_str: 小红书cookies字符串，如果不提供则从环境变量读取
        """
        self.xhs_apis = XHS_Apis()
        
        if cookies_str:
            self.cookies_str = cookies_str
        else:
            self.cookies_str, self.base_path = init()
            
        if not self.cookies_str:
            logger.error("未找到有效的cookies，请设置环境变量或直接传入")
            sys.exit(1)
            
        # 如果没有base_path，创建默认路径
        if not hasattr(self, 'base_path'):
            media_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'datas/media_datas'))
            excel_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'datas/excel_datas'))
            for base_path in [media_base_path, excel_base_path]:
                if not os.path.exists(base_path):
                    os.makedirs(base_path)
                    logger.info(f'创建目录 {base_path}')
            self.base_path = {
                'media': media_base_path,
                'excel': excel_base_path,
            }
    
    def spider_single_post(self, post_url: str, proxies: dict = None) -> tuple:
        """
        爬取单个帖子信息
        :param post_url: 帖子链接
        :param proxies: 代理配置
        :return: (成功状态, 错误信息, 帖子信息)
        """
        try:
            logger.info(f"开始爬取帖子: {post_url}")
            success, msg, note_info = self.xhs_apis.get_note_info(post_url, self.cookies_str, proxies)
            
            if success and note_info and 'data' in note_info and 'items' in note_info['data']:
                if len(note_info['data']['items']) > 0:
                    note_info = note_info['data']['items'][0]
                    note_info['url'] = post_url
                    note_info = handle_note_info(note_info)
                    logger.success(f"成功爬取帖子: {note_info['title']}")
                    return True, "爬取成功", note_info
                else:
                    logger.error(f"帖子数据为空: {post_url}")
                    return False, "帖子数据为空", None
            else:
                logger.error(f"爬取失败: {post_url}, 错误: {msg}")
                return False, msg, None
                
        except Exception as e:
            logger.error(f"爬取帖子异常: {post_url}, 错误: {str(e)}")
            return False, str(e), None
    
    def spider_multiple_posts(self, post_urls: List[str], save_mode: str = 'all', 
                            output_name: str = 'posts_data', proxies: dict = None) -> dict:
        """
        批量爬取多个帖子
        :param post_urls: 帖子链接列表
        :param save_mode: 保存模式 'all'(全部), 'excel'(仅表格), 'media'(仅媒体), 'media-video'(仅视频), 'media-image'(仅图片)
        :param output_name: 输出文件名
        :param proxies: 代理配置
        :return: 爬取结果统计
        """
        logger.info(f"开始批量爬取 {len(post_urls)} 个帖子")
        
        successful_posts = []
        failed_posts = []
        
        # 逐个爬取帖子
        for i, post_url in enumerate(post_urls, 1):
            logger.info(f"正在爬取第 {i}/{len(post_urls)} 个帖子")
            success, msg, post_info = self.spider_single_post(post_url, proxies)
            
            if success and post_info:
                successful_posts.append(post_info)
            else:
                failed_posts.append({'url': post_url, 'error': msg})
        
        logger.info(f"爬取完成! 成功: {len(successful_posts)}, 失败: {len(failed_posts)}")
        
        # 保存数据
        if successful_posts:
            self._save_data(successful_posts, save_mode, output_name)
        
        # 返回统计结果
        return {
            'total': len(post_urls),
            'successful': len(successful_posts),
            'failed': len(failed_posts),
            'successful_posts': successful_posts,
            'failed_posts': failed_posts
        }
    
    def _save_data(self, posts_data: List[dict], save_mode: str, output_name: str):
        """
        保存爬取的数据
        :param posts_data: 帖子数据列表
        :param save_mode: 保存模式
        :param output_name: 输出文件名
        """
        try:
            # 保存媒体文件
            if save_mode in ['all', 'media', 'media-video', 'media-image']:
                logger.info("正在下载媒体文件...")
                for post_info in posts_data:
                    download_note(post_info, self.base_path['media'], save_mode)
            
            # 保存到Excel
            if save_mode in ['all', 'excel']:
                excel_path = os.path.join(self.base_path['excel'], f'{output_name}.xlsx')
                save_to_xlsx(posts_data, excel_path)
                logger.success(f"数据已保存到Excel: {excel_path}")
            
            # 保存到JSON（额外功能）
            json_path = os.path.join(self.base_path['excel'], f'{output_name}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(posts_data, f, ensure_ascii=False, indent=2)
            logger.success(f"数据已保存到JSON: {json_path}")
            
        except Exception as e:
            logger.error(f"保存数据时出错: {str(e)}")
    
    def interactive_spider(self):
        """
        交互式爬取模式
        """
        logger.info("🕷️  小红书帖子爬虫 - 交互模式")
        print("\n" + "="*50)
        print("小红书帖子爬取工具")
        print("="*50)
        
        while True:
            print("\n请选择操作模式:")
            print("1. 爬取单个帖子")
            print("2. 批量爬取帖子")
            print("3. 从文件读取链接批量爬取")
            print("4. 退出")
            
            choice = input("\n请输入选择 (1-4): ").strip()
            
            if choice == '1':
                self._single_post_mode()
            elif choice == '2':
                self._batch_post_mode()
            elif choice == '3':
                self._file_post_mode()
            elif choice == '4':
                print("感谢使用！")
                break
            else:
                print("无效选择，请重新输入")
    
    def _single_post_mode(self):
        """单个帖子爬取模式"""
        post_url = input("\n请输入帖子链接: ").strip()
        if not post_url:
            print("链接不能为空")
            return
        
        save_mode = self._get_save_mode()
        output_name = input("请输入保存文件名 (默认: single_post): ").strip() or "single_post"
        
        success, msg, post_info = self.spider_single_post(post_url)
        
        if success and post_info:
            self._save_data([post_info], save_mode, output_name)
            print(f"\n✅ 爬取成功!")
            print(f"标题: {post_info['title']}")
            print(f"作者: {post_info['nickname']}")
            print(f"类型: {post_info['note_type']}")
        else:
            print(f"\n❌ 爬取失败: {msg}")
    
    def _batch_post_mode(self):
        """批量帖子爬取模式"""
        print("\n请输入帖子链接，每行一个，输入空行结束:")
        urls = []
        while True:
            url = input().strip()
            if not url:
                break
            urls.append(url)
        
        if not urls:
            print("未输入任何链接")
            return
        
        save_mode = self._get_save_mode()
        output_name = input("请输入保存文件名 (默认: batch_posts): ").strip() or "batch_posts"
        
        result = self.spider_multiple_posts(urls, save_mode, output_name)
        
        print(f"\n📊 爬取完成统计:")
        print(f"总数: {result['total']}")
        print(f"成功: {result['successful']}")
        print(f"失败: {result['failed']}")
        
        if result['failed_posts']:
            print("\n❌ 失败的帖子:")
            for failed in result['failed_posts']:
                print(f"  - {failed['url']}: {failed['error']}")
    
    def _file_post_mode(self):
        """从文件读取链接模式"""
        file_path = input("\n请输入包含链接的文件路径: ").strip()
        
        if not os.path.exists(file_path):
            print("文件不存在")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            if not urls:
                print("文件中没有找到有效链接")
                return
            
            print(f"从文件中读取到 {len(urls)} 个链接")
            
            save_mode = self._get_save_mode()
            output_name = input("请输入保存文件名 (默认: file_posts): ").strip() or "file_posts"
            
            result = self.spider_multiple_posts(urls, save_mode, output_name)
            
            print(f"\n📊 爬取完成统计:")
            print(f"总数: {result['total']}")
            print(f"成功: {result['successful']}")
            print(f"失败: {result['failed']}")
            
        except Exception as e:
            print(f"读取文件出错: {str(e)}")
    
    def _get_save_mode(self) -> str:
        """获取保存模式"""
        print("\n请选择保存模式:")
        print("1. 全部保存 (数据+媒体)")
        print("2. 仅保存数据到Excel")
        print("3. 仅下载媒体文件")
        print("4. 仅下载视频")
        print("5. 仅下载图片")
        
        mode_map = {
            '1': 'all',
            '2': 'excel',
            '3': 'media',
            '4': 'media-video',
            '5': 'media-image'
        }
        
        while True:
            choice = input("请选择 (1-5): ").strip()
            if choice in mode_map:
                return mode_map[choice]
            else:
                print("无效选择，请重新输入")


def main():
    """主函数"""
    spider = PostSpider()
    
    # 如果有命令行参数，直接处理
    if len(sys.argv) > 1:
        post_urls = sys.argv[1:]
        logger.info(f"从命令行接收到 {len(post_urls)} 个链接")
        result = spider.spider_multiple_posts(post_urls, 'all', 'cmd_posts')
        print(f"爬取完成: 成功 {result['successful']}, 失败 {result['failed']}")
    else:
        # 启动交互式模式
        spider.interactive_spider()


if __name__ == "__main__":
    main() 

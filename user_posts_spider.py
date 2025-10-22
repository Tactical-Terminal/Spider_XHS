#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书用户所有帖子爬取脚本
根据用户主页链接爬取该用户的所有帖子
支持不同的保存模式和输出格式
"""

import json
import os
import sys
import urllib.parse
from typing import List, Optional, Dict
from loguru import logger
from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.common_util import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx


class UserPostsSpider:
    """用户帖子爬虫类"""
    
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
    
    def extract_user_id_from_url(self, user_url: str) -> str:
        """
        从用户URL中提取用户ID
        :param user_url: 用户主页链接
        :return: 用户ID
        """
        try:
            parsed_url = urllib.parse.urlparse(user_url)
            user_id = parsed_url.path.split("/")[-1]
            return user_id
        except Exception as e:
            logger.error(f"提取用户ID失败: {str(e)}")
            return None
    
    def get_user_info(self, user_url: str, proxies: dict = None) -> tuple:
        """
        获取用户基本信息
        :param user_url: 用户主页链接
        :param proxies: 代理配置
        :return: (成功状态, 错误信息, 用户信息)
        """
        try:
            user_id = self.extract_user_id_from_url(user_url)
            if not user_id:
                return False, "无法提取用户ID", None
            
            success, msg, user_info = self.xhs_apis.get_user_info(user_id, self.cookies_str, proxies)
            
            if success and user_info and 'data' in user_info:
                user_data = user_info['data']
                logger.info(f"获取用户信息成功: {user_data.get('basic_info', {}).get('nickname', '未知用户')}")
                return True, "获取成功", user_data
            else:
                logger.error(f"获取用户信息失败: {msg}")
                return False, msg, None
                
        except Exception as e:
            logger.error(f"获取用户信息异常: {str(e)}")
            return False, str(e), None
    
    def get_user_all_posts(self, user_url: str, proxies: dict = None) -> tuple:
        """
        获取用户所有帖子列表
        :param user_url: 用户主页链接
        :param proxies: 代理配置
        :return: (成功状态, 错误信息, 帖子列表)
        """
        try:
            logger.info(f"开始获取用户所有帖子: {user_url}")
            
            # 检查URL是否包含必要的查询参数
            parsed_url = urllib.parse.urlparse(user_url)
            if not parsed_url.query:
                # 如果URL没有查询参数，添加默认的xsec_source
                user_url += "?xsec_source=pc_user"
                logger.info(f"添加默认查询参数: {user_url}")
            
            success, msg, all_notes = self.xhs_apis.get_user_all_notes(user_url, self.cookies_str, proxies)
            
            if success and all_notes is not None:
                logger.success(f"成功获取用户帖子列表，共 {len(all_notes)} 篇")
                return True, "获取成功", all_notes
            else:
                logger.error(f"获取用户帖子列表失败: {msg}")
                return False, msg, []
                
        except Exception as e:
            logger.error(f"获取用户帖子列表异常: {str(e)}")
            return False, str(e), []
    
    def spider_single_post(self, note_url: str, proxies: dict = None) -> tuple:
        """
        爬取单个帖子详细信息
        :param note_url: 帖子链接
        :param proxies: 代理配置
        :return: (成功状态, 错误信息, 帖子信息)
        """
        try:
            success, msg, note_info = self.xhs_apis.get_note_info(note_url, self.cookies_str, proxies)
            
            if success and note_info and 'data' in note_info and 'items' in note_info['data']:
                if len(note_info['data']['items']) > 0:
                    note_data = note_info['data']['items'][0]
                    note_data['url'] = note_url
                    note_data = handle_note_info(note_data)
                    return True, "爬取成功", note_data
                else:
                    return False, "帖子数据为空", None
            else:
                return False, msg, None
                
        except Exception as e:
            logger.error(f"爬取帖子异常: {note_url}, 错误: {str(e)}")
            return False, str(e), None
    
    def spider_user_all_posts(self, user_url: str, save_mode: str = 'all', 
                             output_name: str = None, proxies: dict = None) -> dict:
        """
        爬取用户的所有帖子
        :param user_url: 用户主页链接，如：https://www.xiaohongshu.com/user/profile/674cc72b000000001d02e831
        :param save_mode: 保存模式 'all'(全部), 'excel'(仅表格), 'media'(仅媒体), 'media-video'(仅视频), 'media-image'(仅图片)
        :param output_name: 输出文件名，如果不指定则使用用户ID
        :param proxies: 代理配置
        :return: 爬取结果统计
        """
        logger.info(f"🕷️ 开始爬取用户所有帖子: {user_url}")
        
        # 获取用户基本信息
        user_success, user_msg, user_info = self.get_user_info(user_url, proxies)
        if not user_success:
            logger.error(f"获取用户信息失败: {user_msg}")
            return {'error': f"获取用户信息失败: {user_msg}"}
        
        user_nickname = user_info.get('basic_info', {}).get('nickname', '未知用户')
        user_id = self.extract_user_id_from_url(user_url)
        
        # 设置输出文件名
        if not output_name:
            output_name = f"{user_nickname}_{user_id}" if user_nickname != '未知用户' else user_id
        
        logger.info(f"👤 用户信息: {user_nickname} (ID: {user_id})")
        
        # 获取用户所有帖子列表
        posts_success, posts_msg, all_notes = self.get_user_all_posts(user_url, proxies)
        if not posts_success:
            logger.error(f"获取帖子列表失败: {posts_msg}")
            return {'error': f"获取帖子列表失败: {posts_msg}"}
        
        if not all_notes:
            logger.warning("该用户没有发布任何帖子")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'user_info': user_info,
                'successful_posts': [],
                'failed_posts': []
            }
        
        logger.info(f"📝 找到 {len(all_notes)} 篇帖子，开始详细爬取...")
        
        successful_posts = []
        failed_posts = []
        
        # 逐个爬取帖子详细信息
        for i, note_info in enumerate(all_notes, 1):
            try:
                note_id = note_info.get('note_id')
                xsec_token = note_info.get('xsec_token', '')
                
                if not note_id:
                    logger.warning(f"第 {i} 篇帖子缺少note_id，跳过")
                    failed_posts.append({'note_info': note_info, 'error': '缺少note_id'})
                    continue
                
                # 构建帖子详情链接
                note_url = f"https://www.xiaohongshu.com/explore/{note_id}"
                if xsec_token:
                    note_url += f"?xsec_token={xsec_token}&xsec_source=pc_user"
                
                logger.info(f"正在爬取第 {i}/{len(all_notes)} 篇帖子: {note_id}")
                
                success, msg, post_detail = self.spider_single_post(note_url, proxies)
                
                if success and post_detail:
                    successful_posts.append(post_detail)
                    logger.success(f"✅ 第 {i} 篇成功: {post_detail.get('title', '无标题')}")
                else:
                    failed_posts.append({'note_id': note_id, 'url': note_url, 'error': msg})
                    logger.error(f"❌ 第 {i} 篇失败: {msg}")
                    
            except Exception as e:
                logger.error(f"处理第 {i} 篇帖子时出错: {str(e)}")
                failed_posts.append({'index': i, 'error': str(e)})
        
        logger.info(f"🎉 爬取完成! 成功: {len(successful_posts)}, 失败: {len(failed_posts)}")
        
        # 保存数据
        if successful_posts:
            self._save_data(successful_posts, save_mode, output_name, user_info)
        
        # 返回统计结果
        return {
            'total': len(all_notes),
            'successful': len(successful_posts),
            'failed': len(failed_posts),
            'user_info': user_info,
            'successful_posts': successful_posts,
            'failed_posts': failed_posts
        }
    
    def _save_data(self, posts_data: List[dict], save_mode: str, output_name: str, user_info: dict = None):
        """
        保存爬取的数据
        :param posts_data: 帖子数据列表
        :param save_mode: 保存模式
        :param output_name: 输出文件名
        :param user_info: 用户信息
        """
        try:
            # 保存媒体文件
            if save_mode in ['all', 'media', 'media-video', 'media-image']:
                logger.info("📥 正在下载媒体文件...")
                for post_info in posts_data:
                    download_note(post_info, self.base_path['media'], save_mode)
            
            # 保存到Excel
            if save_mode in ['all', 'excel']:
                excel_path = os.path.join(self.base_path['excel'], f'{output_name}.xlsx')
                save_to_xlsx(posts_data, excel_path)
                logger.success(f"📊 数据已保存到Excel: {excel_path}")
            
            # 保存到JSON（包含用户信息）
            json_data = {
                'user_info': user_info,
                'posts_count': len(posts_data),
                'posts_data': posts_data,
                'crawl_time': str(os.path.getmtime(__file__))
            }
            
            json_path = os.path.join(self.base_path['excel'], f'{output_name}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            logger.success(f"💾 数据已保存到JSON: {json_path}")
            
        except Exception as e:
            logger.error(f"保存数据时出错: {str(e)}")
    
    def interactive_spider(self):
        """
        交互式爬取模式
        """
        logger.info("🕷️ 小红书用户帖子爬虫 - 交互模式")
        print("\n" + "="*60)
        print("🌟 小红书用户所有帖子爬取工具")
        print("="*60)
        print("支持爬取指定用户的所有已发布帖子")
        print("示例链接: https://www.xiaohongshu.com/user/profile/674cc72b000000001d02e831")
        
        while True:
            print("\n请选择操作:")
            print("1. 爬取用户所有帖子")
            print("2. 查看用户基本信息")
            print("3. 退出")
            
            choice = input("\n请输入选择 (1-3): ").strip()
            
            if choice == '1':
                self._spider_user_mode()
            elif choice == '2':
                self._user_info_mode()
            elif choice == '3':
                print("👋 感谢使用！")
                break
            else:
                print("❌ 无效选择，请重新输入")
    
    def _spider_user_mode(self):
        """用户帖子爬取模式"""
        user_url = input("\n请输入用户主页链接: ").strip()
        if not user_url:
            print("❌ 链接不能为空")
            return
        
        if "xiaohongshu.com/user/profile/" not in user_url:
            print("❌ 请输入正确的小红书用户主页链接")
            return
        
        save_mode = self._get_save_mode()
        output_name = input("请输入保存文件名 (回车使用默认名称): ").strip()
        
        result = self.spider_user_all_posts(user_url, save_mode, output_name or None)
        
        if 'error' in result:
            print(f"\n❌ 爬取失败: {result['error']}")
            return
        
        print(f"\n📊 爬取完成统计:")
        print(f"👤 用户: {result['user_info'].get('basic_info', {}).get('nickname', '未知')}")
        print(f"📝 总帖子数: {result['total']}")
        print(f"✅ 成功: {result['successful']}")
        print(f"❌ 失败: {result['failed']}")
        
        if result['failed_posts']:
            print(f"\n❌ 失败的帖子 ({len(result['failed_posts'])}):")
            for i, failed in enumerate(result['failed_posts'][:5], 1):  # 只显示前5个
                print(f"  {i}. {failed.get('note_id', 'Unknown')}: {failed['error']}")
            if len(result['failed_posts']) > 5:
                print(f"  ... 还有 {len(result['failed_posts']) - 5} 个失败")
    
    def _user_info_mode(self):
        """查看用户信息模式"""
        user_url = input("\n请输入用户主页链接: ").strip()
        if not user_url:
            print("❌ 链接不能为空")
            return
        
        success, msg, user_info = self.get_user_info(user_url)
        
        if success and user_info:
            basic_info = user_info.get('basic_info', {})
            interact_info = user_info.get('interact_info', {})
            
            print(f"\n👤 用户信息:")
            print(f"📛 昵称: {basic_info.get('nickname', '未知')}")
            print(f"🆔 用户ID: {basic_info.get('red_id', '未知')}")
            print(f"📝 简介: {basic_info.get('desc', '无')}")
            print(f"👥 粉丝数: {interact_info.get('followed_count', 0)}")
            print(f"💖 获赞与收藏: {interact_info.get('liked_count', 0)}")
            print(f"📚 笔记数: {interact_info.get('note_count', 0)}")
        else:
            print(f"\n❌ 获取用户信息失败: {msg}")
    
    def _get_save_mode(self) -> str:
        """获取保存模式"""
        print("\n请选择保存模式:")
        print("1. 🎯 全部保存 (数据+媒体)")
        print("2. 📊 仅保存数据到Excel")
        print("3. 📥 仅下载媒体文件")
        print("4. 🎬 仅下载视频")
        print("5. 🖼️ 仅下载图片")
        
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
                print("❌ 无效选择，请重新输入")


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 命令行模式
        user_url = sys.argv[1]
        save_mode = sys.argv[2] if len(sys.argv) > 2 else 'all'
        output_name = sys.argv[3] if len(sys.argv) > 3 else None
        
        spider = UserPostsSpider()
        logger.info(f"命令行模式: 爬取用户 {user_url}")
        result = spider.spider_user_all_posts(user_url, save_mode, output_name)
        
        if 'error' in result:
            print(f"爬取失败: {result['error']}")
            sys.exit(1)
        else:
            print(f"爬取完成: 成功 {result['successful']}/{result['total']}")
    else:
        # 交互式模式
        spider = UserPostsSpider()
        spider.interactive_spider()


if __name__ == "__main__":
    main()
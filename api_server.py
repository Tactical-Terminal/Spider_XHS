#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书API服务器
提供RESTful API接口用于获取小红书帖子信息
"""

import os
import sys
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
from loguru import logger
import uvicorn

from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.data_util import handle_note_info

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="小红书数据API",
    description="获取小红书帖子的详细信息，包括图片、视频、文本等",
    version="1.0.0"
)

# 初始化API客户端
xhs_apis = XHS_Apis()

# 从环境变量获取配置
COOKIES_STR = os.getenv('XHS_COOKIES', '')
PROXY_HOST = os.getenv('PROXY_HOST', '')
PROXY_PORT = os.getenv('PROXY_PORT', '')

# 配置代理
proxies = None
if PROXY_HOST and PROXY_PORT:
    proxies = {
        'http': f'http://{PROXY_HOST}:{PROXY_PORT}',
        'https': f'http://{PROXY_HOST}:{PROXY_PORT}'
    }
    logger.info(f"已配置代理: {proxies}")


class PostRequest(BaseModel):
    """帖子请求模型"""
    url: str
    cookies: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.xiaohongshu.com/explore/67d7c713000000000900e391?xsec_token=AB1ACxbo5cevHxV_bWibTmK8R1DDz0NnAW1PbFZLABXtE=&xsec_source=pc_user",
                "cookies": "可选的cookies字符串"
            }
        }


class PostResponse(BaseModel):
    """帖子响应模型"""
    success: bool
    message: str
    data: Optional[Dict[Any, Any]] = None


@app.get("/", response_model=Dict[str, str])
async def root():
    """API根路径"""
    return {
        "message": "小红书数据API服务",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "xhs-api"
    }


@app.post("/api/post", response_model=PostResponse)
async def get_post_info(request: PostRequest):
    """
    获取小红书帖子信息

    Args:
        request: 包含帖子URL的请求体

    Returns:
        包含帖子详细信息的响应

    响应数据包括:
        - note_id: 帖子ID
        - title: 标题
        - desc: 描述文本
        - note_type: 类型(normal/video)
        - images: 图片列表(无水印)
        - video: 视频信息(无水印)
        - user: 用户信息
        - liked_count: 点赞数
        - collected_count: 收藏数
        - comment_count: 评论数
        - share_count: 分享数
    """
    try:
        # 使用请求中的cookies或环境变量中的cookies
        cookies = request.cookies if request.cookies else COOKIES_STR

        if not cookies:
            raise HTTPException(
                status_code=400,
                detail="未提供cookies,请在请求中提供或在环境变量中配置XHS_COOKIES"
            )

        # 调用API获取帖子信息
        logger.info(f"正在获取帖子信息: {request.url}")
        success, msg, note_info = xhs_apis.get_note_info(request.url, cookies, proxies)

        if not success:
            logger.error(f"获取帖子失败: {msg}")
            raise HTTPException(status_code=500, detail=f"获取帖子失败: {msg}")

        # 检查返回数据
        if not note_info or 'data' not in note_info or 'items' not in note_info['data']:
            logger.error("帖子数据格式错误")
            raise HTTPException(status_code=500, detail="帖子数据格式错误")

        items = note_info['data']['items']
        if len(items) == 0:
            logger.error("帖子数据为空")
            raise HTTPException(status_code=404, detail="未找到帖子数据")

        # 处理帖子信息
        post_data = items[0]
        post_data['url'] = request.url
        processed_data = handle_note_info(post_data)

        # 重新组织数据结构，使其更清晰
        formatted_data = {
            "note_id": processed_data.get("note_id"),
            "note_url": processed_data.get("note_url"),
            "title": processed_data.get("title"),
            "desc": processed_data.get("desc"),
            "note_type": processed_data.get("note_type"),
            "images": processed_data.get("image_list", []),  # 图片列表（无水印）
            "video": {
                "cover": processed_data.get("video_cover"),
                "url": processed_data.get("video_addr")
            } if processed_data.get("video_addr") else None,  # 视频信息（无水印）
            "user": {
                "user_id": processed_data.get("user_id"),
                "nickname": processed_data.get("nickname"),
                "avatar": processed_data.get("avatar"),
                "home_url": processed_data.get("home_url")
            },
            "stats": {
                "liked_count": processed_data.get("liked_count"),
                "collected_count": processed_data.get("collected_count"),
                "comment_count": processed_data.get("comment_count"),
                "share_count": processed_data.get("share_count")
            },
            "tags": processed_data.get("tags", []),
            "upload_time": processed_data.get("upload_time"),
            "ip_location": processed_data.get("ip_location")
        }

        logger.success(f"成功获取帖子: {formatted_data['title']}")

        return PostResponse(
            success=True,
            message="成功获取帖子信息",
            data=formatted_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.get("/api/post", response_model=PostResponse)
async def get_post_info_by_url(
    url: str = Query(..., description="小红书帖子URL"),
    cookies: Optional[str] = Query(None, description="可选的cookies字符串")
):
    """
    通过URL参数获取小红书帖子信息 (GET方法)

    Args:
        url: 小红书帖子URL
        cookies: 可选的cookies字符串

    Returns:
        包含帖子详细信息的响应
    """
    request = PostRequest(url=url, cookies=cookies)
    return await get_post_info(request)


@app.post("/api/batch", response_model=Dict[str, Any])
async def get_batch_posts(urls: list[str], cookies: Optional[str] = None):
    """
    批量获取多个帖子信息

    Args:
        urls: 帖子URL列表
        cookies: 可选的cookies字符串

    Returns:
        包含所有帖子信息的响应
    """
    results = {
        "success": [],
        "failed": [],
        "total": len(urls)
    }

    cookies_to_use = cookies if cookies else COOKIES_STR

    if not cookies_to_use:
        raise HTTPException(
            status_code=400,
            detail="未提供cookies,请在请求中提供或在环境变量中配置XHS_COOKIES"
        )

    for url in urls:
        try:
            success, msg, note_info = xhs_apis.get_note_info(url, cookies_to_use, proxies)

            if success and note_info and 'data' in note_info and 'items' in note_info['data']:
                if len(note_info['data']['items']) > 0:
                    post_data = note_info['data']['items'][0]
                    post_data['url'] = url
                    processed_data = handle_note_info(post_data)

                    # 格式化数据
                    formatted_data = {
                        "note_id": processed_data.get("note_id"),
                        "note_url": processed_data.get("note_url"),
                        "title": processed_data.get("title"),
                        "desc": processed_data.get("desc"),
                        "note_type": processed_data.get("note_type"),
                        "images": processed_data.get("image_list", []),
                        "video": {
                            "cover": processed_data.get("video_cover"),
                            "url": processed_data.get("video_addr")
                        } if processed_data.get("video_addr") else None,
                        "user": {
                            "user_id": processed_data.get("user_id"),
                            "nickname": processed_data.get("nickname"),
                            "avatar": processed_data.get("avatar"),
                            "home_url": processed_data.get("home_url")
                        },
                        "stats": {
                            "liked_count": processed_data.get("liked_count"),
                            "collected_count": processed_data.get("collected_count"),
                            "comment_count": processed_data.get("comment_count"),
                            "share_count": processed_data.get("share_count")
                        },
                        "tags": processed_data.get("tags", []),
                        "upload_time": processed_data.get("upload_time"),
                        "ip_location": processed_data.get("ip_location")
                    }

                    results["success"].append({
                        "url": url,
                        "data": formatted_data
                    })
                else:
                    results["failed"].append({
                        "url": url,
                        "error": "帖子数据为空"
                    })
            else:
                results["failed"].append({
                    "url": url,
                    "error": msg
                })
        except Exception as e:
            results["failed"].append({
                "url": url,
                "error": str(e)
            })

    return {
        "message": f"批量处理完成: 成功 {len(results['success'])}, 失败 {len(results['failed'])}",
        "results": results
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"服务器错误: {str(exc)}",
            "data": None
        }
    )


def main():
    """启动服务器"""
    # 检查环境变量
    if not COOKIES_STR:
        logger.warning("警告: 未设置XHS_COOKIES环境变量,请在.env文件中配置或在API请求中提供cookies")

    # 获取服务器配置
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8000'))

    logger.info(f"正在启动API服务器...")
    logger.info(f"服务地址: http://{host}:{port}")
    logger.info(f"API文档: http://{host}:{port}/docs")

    # 启动服务器
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()

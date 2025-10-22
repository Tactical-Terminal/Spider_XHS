# 小红书API使用说明

## 📋 功能介绍

这是一个基于FastAPI构建的小红书数据采集API服务，可以通过HTTP接口获取小红书帖子的详细信息。

### 支持的功能

- ✅ 获取单个帖子的详细信息
- ✅ 批量获取多个帖子
- ✅ 返回无水印图片和视频链接
- ✅ 获取帖子标题、描述、用户信息
- ✅ 获取点赞、收藏、评论、分享数据

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`:

```bash
cp .env.example .env
```

编辑 `.env` 文件,填入你的小红书Cookies:

```env
XHS_COOKIES=your_cookies_here
API_HOST=0.0.0.0
API_PORT=8000
```

**获取Cookies的方法:**

1. 打开浏览器,访问 [小红书网页版](https://www.xiaohongshu.com)
2. 登录你的账号
3. 按F12打开开发者工具
4. 切换到Network(网络)标签
5. 刷新页面,找到任意请求
6. 在请求头中复制Cookie的值

### 3. 启动服务器

**Linux/Mac:**

```bash
chmod +x start_api.sh
./start_api.sh
```

**或直接使用Python:**

```bash
python api_server.py
```

服务启动后访问:
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 📖 API接口文档

### 1. 获取单个帖子 (POST)

**接口:** `POST /api/post`

**请求体:**

```json
{
  "url": "https://www.xiaohongshu.com/explore/67d7c713000000000900e391?xsec_token=AB1ACxbo5cevHxV_bWibTmK8R1DDz0NnAW1PbFZLABXtE=&xsec_source=pc_user",
  "cookies": "可选的cookies字符串"
}
```

**响应:**

```json
{
  "success": true,
  "message": "成功获取帖子信息",
  "data": {
    "note_id": "67d7c713000000000900e391",
    "title": "帖子标题",
    "desc": "帖子描述文本...",
    "note_type": "normal",
    "images": [
      "https://sns-img-qc.xhscdn.com/xxx.jpg",
      "https://sns-img-qc.xhscdn.com/yyy.jpg"
    ],
    "video": null,
    "user": {
      "user_id": "xxx",
      "nickname": "用户昵称",
      "avatar": "头像URL"
    },
    "liked_count": 1234,
    "collected_count": 567,
    "comment_count": 89,
    "share_count": 12,
    "time": "2025-01-15 10:30:00",
    "ip_location": "北京",
    "tags": ["标签1", "标签2"]
  }
}
```

### 2. 获取单个帖子 (GET)

**接口:** `GET /api/post?url={帖子URL}`

**示例:**

```bash
curl "http://localhost:8000/api/post?url=https://www.xiaohongshu.com/explore/67d7c713000000000900e391?xsec_token=xxx&xsec_source=pc_user"
```

### 3. 批量获取帖子

**接口:** `POST /api/batch`

**请求体:**

```json
{
  "urls": [
    "https://www.xiaohongshu.com/explore/xxx",
    "https://www.xiaohongshu.com/explore/yyy"
  ],
  "cookies": "可选的cookies字符串"
}
```

**响应:**

```json
{
  "message": "批量处理完成: 成功 2, 失败 0",
  "results": {
    "success": [
      {
        "url": "https://www.xiaohongshu.com/explore/xxx",
        "data": { /* 帖子数据 */ }
      }
    ],
    "failed": [],
    "total": 2
  }
}
```

### 4. 健康检查

**接口:** `GET /health`

**响应:**

```json
{
  "status": "healthy",
  "service": "xhs-api"
}
```

## 🔧 使用示例

### Python示例

```python
import requests

# API地址
api_url = "http://localhost:8000/api/post"

# 帖子URL
post_url = "https://www.xiaohongshu.com/explore/67d7c713000000000900e391?xsec_token=xxx&xsec_source=pc_user"

# 发送请求
response = requests.post(api_url, json={"url": post_url})
data = response.json()

if data["success"]:
    post_info = data["data"]
    print(f"标题: {post_info['title']}")
    print(f"描述: {post_info['desc']}")
    print(f"图片数量: {len(post_info['images'])}")
    print(f"点赞数: {post_info['liked_count']}")
else:
    print(f"获取失败: {data['message']}")
```

### cURL示例

```bash
# POST请求
curl -X POST "http://localhost:8000/api/post" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.xiaohongshu.com/explore/67d7c713000000000900e391?xsec_token=xxx&xsec_source=pc_user"
  }'

# GET请求
curl "http://localhost:8000/api/post?url=https://www.xiaohongshu.com/explore/67d7c713000000000900e391?xsec_token=xxx&xsec_source=pc_user"
```

### JavaScript示例

```javascript
// 使用fetch
async function getPostInfo(postUrl) {
  const response = await fetch('http://localhost:8000/api/post', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      url: postUrl
    })
  });

  const data = await response.json();

  if (data.success) {
    console.log('标题:', data.data.title);
    console.log('图片:', data.data.images);
  } else {
    console.error('获取失败:', data.message);
  }
}

// 调用
getPostInfo('https://www.xiaohongshu.com/explore/xxx');
```

## 🐳 Docker部署

创建 `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "api_server.py"]
```

构建和运行:

```bash
# 构建镜像
docker build -t xhs-api .

# 运行容器
docker run -d \
  --name xhs-api \
  -p 8000:8000 \
  -e XHS_COOKIES="your_cookies_here" \
  xhs-api
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| XHS_COOKIES | 小红书Cookies | - | 是* |
| API_HOST | API服务器监听地址 | 0.0.0.0 | 否 |
| API_PORT | API服务器端口 | 8000 | 否 |
| PROXY_HOST | 代理服务器地址 | - | 否 |
| PROXY_PORT | 代理服务器端口 | - | 否 |

\* 可以在.env中配置或在每个API请求中提供

### 代理配置

如果你在国外服务器上运行,可能需要配置代理:

```env
PROXY_HOST=127.0.0.1
PROXY_PORT=7890
```

## 📝 注意事项

1. **Cookies安全**: Cookies包含登录凭证,请勿泄露给他人
2. **请求频率**: 建议控制请求频率,避免被小红书限流
3. **Cookies过期**: Cookies会定期过期,需要重新获取
4. **仅供学习**: 本项目仅供学习交流使用,请勿用于商业用途

## 🔍 故障排查

### 1. 返回401/403错误

- Cookies已过期,需要重新获取
- Cookies格式不正确

### 2. 返回404错误

- 帖子链接不正确
- 帖子已被删除或设为私密

### 3. 服务启动失败

- 检查端口8000是否被占用
- 检查Python版本是否为3.7+
- 检查依赖是否正确安装

### 4. 无法访问小红书

- 检查网络连接
- 如在国外,尝试配置代理

## 📞 技术支持

如有问题,请查看项目README或提交Issue。

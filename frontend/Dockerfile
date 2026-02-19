# AI Society 前端 Dockerfile
# ===========================
# 构建方式: docker build -t aisociety-frontend .
# 运行方式: docker run -p 3000:3000 aisociety-frontend

FROM node:20-alpine

# 设置工作目录
WORKDIR /app

# 复制 package 文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 3000

# 开发模式启动
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

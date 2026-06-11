# Nginx、Cloudflare 与 HTTPS 说明

## 1. 域名访问发生了什么

一条典型链路是：

```text
用户输入域名
-> DNS 把域名解析到 VPS IP
-> 请求到达 VPS 的 80/443 端口
-> Nginx 接收请求
-> Nginx 转发给 FastAPI 容器
-> FastAPI 返回页面或 API 响应
```

## 2. Cloudflare 做什么

Cloudflare 在本项目里主要负责：

- 管理 DNS 解析。
- 给域名提供 HTTPS 入口。
- 做基础 CDN 和访问保护。

Cloudflare 不是传统意义上的 Linux VPS。它不替代你的服务器，而是站在用户和服务器之间。

## 3. DNS 配置

在 Cloudflare DNS 中添加：

```text
Type: A
Name: @ 或 interview
Content: 你的 VPS 公网 IP
Proxy status: Proxied 或 DNS only
```

说明：

- `@` 表示根域名，例如 `example.com`。
- `interview` 表示子域名，例如 `interview.example.com`。
- `Proxied` 会让流量经过 Cloudflare。
- `DNS only` 只做域名解析，请求直接到服务器。

## 4. HTTPS 两种路线

### 路线 A：Cloudflare 代理模式

适合个人项目快速展示。

流程：

```text
浏览器 HTTPS -> Cloudflare -> VPS Nginx
```

建议 Cloudflare SSL 模式使用：

```text
Full
```

后续如果服务器也配置了真实证书，可以用：

```text
Full strict
```

### 路线 B：Let's Encrypt / Certbot

适合希望服务器自己管理证书的情况。

大致流程：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

注意：

- 需要域名已经解析到 VPS。
- 需要开放 80/443 端口。
- 如果 Cloudflare 开启代理，遇到验证问题时可以临时切到 DNS only。

## 5. Nginx 为什么叫反向代理

普通代理是“客户端找代理去访问别人”。

反向代理是“服务器入口替后端服务接收请求”。

本项目中：

```text
用户不知道 FastAPI 容器在哪
用户只访问 Nginx
Nginx 再把请求转发到 app:8000
```

所以 Nginx 是反向代理。
